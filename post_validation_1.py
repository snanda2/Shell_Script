#!/usr/bin/env python3

import os
import socket
import subprocess
import logging
from datetime import datetime
import argparse
import psutil
import sys
import re
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Constants for log directory and file extensions
LOG_DIR = "logs"
LOG_EXTENSION = ".log"
FAILED_LOG_SUFFIX = "_failed"
PRE_VALIDATION_STATE_FILE = "prevalidation_state.json"

# Email Configuration
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "your_email@example.com"
SMTP_PASSWORD = "your_password"
SENDER_EMAIL = "your_email@example.com"
RECEIVER_EMAIL = "receiver_email@example.com"

# Exit codes
EXIT_SUCCESS = 0
EXIT_GENERAL_FAILURE = 1
EXIT_POSTVALIDATION_FAILURE = 11

EXIT_CODE_DESCRIPTIONS = {
    EXIT_SUCCESS: "Script completed successfully.",
    EXIT_GENERAL_FAILURE: "General failure.",
    EXIT_POSTVALIDATION_FAILURE: "Post-validation failure."
}

class ServerManager:
    def __init__(self, action):
        self.hostname = socket.gethostname()
        self.client = self.identify_client()
        self.server_type = self.identify_server_type()
        self.environment = self.identify_environment()
        self.region = self.identify_region()
        self.action = action
        self.setup_logging()
        self.overall_status = True  # To track overall script status
        self.prevalidation_state = self.read_prevalidation_state()
        self.postvalidation_state = {
            "processes": [],
            "mailbox_status": "",
            "ports": {
                "disconnected": [],
                "passive": [],
                "stopped": []
            },
            "bins_down": []
        }

    def setup_logging(self):
        """Set up logging for the script."""
        os.makedirs(LOG_DIR, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        base_log_filename = f"{self.hostname}_{self.client}_{date_str}_{self.action}"
        self.log_filename = os.path.join(LOG_DIR, f"{base_log_filename}{LOG_EXTENSION}")
        self.failed_log_filename = os.path.join(LOG_DIR, f"{base_log_filename}{FAILED_LOG_SUFFIX}{LOG_EXTENSION}")

        # Remove old log files if they exist
        self._remove_old_log_files(self.log_filename, self.failed_log_filename)

        logging.basicConfig(
            filename=self.log_filename,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Failed log handler
        self.failed_log_handler = logging.FileHandler(self.failed_log_filename)
        self.failed_log_handler.setLevel(logging.ERROR)
        self.failed_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.failed_log_handler)

    @staticmethod
    def _remove_old_log_files(*log_files):
        """Remove old log files if they exist."""
        for log_file in log_files:
            if os.path.exists(log_file):
                os.remove(log_file)

    def identify_client(self):
        """Identify the client based on the hostname."""
        hostname_lower = self.hostname.lower()
        if "cv" in hostname_lower:
            return "Chevron"
        else:
            return "unknown_client"

    def identify_server_type(self):
        """Identify the server type based on the hostname."""
        hostname_lower = self.hostname.lower()
        if "istsap" in hostname_lower:
            return "switch_server"
        elif "istssn" in hostname_lower:
            return "L7_server"
        elif "dwso2" in hostname_lower:
            return "wso2_server"
        elif "gui" in hostname_lower:
            return "gui_server"
        elif "sftp" in hostname_lower:
            return "sftp_server"
        else:
            return "unknown_server"

    def identify_environment(self):
        """Identify the environment based on the hostname."""
        match = re.search(r'v\w{2}\w{4}(\w{1})\w{2}', self.hostname.lower())
        if match:
            env_code = match.group(1)
            if env_code == 'p':
                return "Production"
            elif env_code == 's':
                return "Stage"
            elif env_code == 'd':
                return "Development"
            elif env_code == 't':
                return "UAT"
        return "Unknown"

    def identify_region(self):
        """Identify the region based on the hostname."""
        match = re.search(r'v\w{2}\w{3}(\w{1})\w{2}', self.hostname.lower())
        if match:
            region_code = match.group(1)
            if region_code == 'w':
                return "West"
            elif region_code == 'e':
                return "East"
        return "Unknown"

    def read_prevalidation_state(self):
        """Read the pre-validation state from a file."""
        try:
            with open(PRE_VALIDATION_STATE_FILE, 'r') as f:
                prevalidation_state = json.load(f)
            logging.info("Pre-validation state read successfully.")
            return prevalidation_state
        except Exception as e:
            logging.error(f"Failed to read pre-validation state. Error: {e}")
            self.log_and_exit(EXIT_GENERAL_FAILURE, "Failed to read pre-validation state")

    def bringup_services(self):
        """Bring up the services."""
        logging.info("Bringing up services...")
        self.execute_commands("bringup")

    def execute_commands(self, command_type):
        """Execute the commands for the given command type (bringup)."""
        if self.client not in COMMANDS or self.server_type not in COMMANDS[self.client]:
            self.log_and_exit(EXIT_GENERAL_FAILURE, "Unknown client or server type")

        commands = COMMANDS[self.client][self.server_type].get(command_type, [])
        for command in commands:
            self._execute_command(command)

    def _execute_command(self, command):
        """Execute a single command and log the result."""
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            status_code = result.returncode
            logging.info(f"Executed command: {command}")
            logging.info(f"Output:\n{output}")
            logging.info(f"Status code: {status_code}")
            if status_code != 0:
                self.overall_status = False

        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode().strip()
            status_code = e.returncode
            logging.error(f"Failed to execute command: {command}")
            logging.error(f"Error:\n{error_output}")
            logging.error(f"Status code: {status_code}")

            if status_code == 127:
                self.log_and_exit(EXIT_GENERAL_FAILURE, "Command not found")
            elif status_code == 126:
                self.log_and_exit(EXIT_GENERAL_FAILURE, "Command cannot execute")
            elif status_code == 1:
                self.log_and_exit(EXIT_GENERAL_FAILURE, "General error")
            
            self.overall_status = False

    def post_validation(self):
        """Perform post-validation tasks."""
        logging.info("Starting post-validation...")
        self.check_mailbox_status()
        self.check_processes()
        self.check_ports()
        self.check_bins()
        self.compare_states()
        self.log_post_validation_results()

    def check_mailbox_status(self):
        """Check the IST Mail Box status."""
        try:
            result = subprocess.run("echo -e '\n exit' | mbcmd", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            filtered_output = self._filter_mbcmd_output(output)
            logging.info(f"Mailbox check output:\n{filtered_output}")

            if "IST Mail Box up since" in filtered_output:
                logging.info("IST Mail Box is up and active.")
                self.postvalidation_state["mailbox_status"] = "up"
            elif "Mail box system not active" in filtered_output:
                logging.info("Mail box system not active.")
                self.postvalidation_state["mailbox_status"] = "not active"
            else:
                logging.info("Unexpected mailbox status output.")
                self.postvalidation_state["mailbox_status"] = "unexpected"
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode().strip()
            logging.error(f"Failed to check mailbox status. Error:\n{error_output}")
            self.postvalidation_state["mailbox_status"] = "error"

    @staticmethod
    def _filter_mbcmd_output(output):
        """Filter the output of mbcmd to find relevant information."""
        for line in output.splitlines():
            if "IST Mail Box" in line:
                return line
        return "Desired line not found in mbcmd output."

    def check_processes(self):
        """Check the status of required processes and log the results."""
        processes = self.prevalidation_state.get("processes", [])
        for process in processes:
            if is_process_running(process):
                logging.info(f"Process {process} is running - OK")
                self.postvalidation_state["processes"].append(process)
            else:
                logging.error(f"Process {process} is not running - NOT OK")
                self.overall_status = False

    def check_ports(self):
        """Check the status of ports."""
        if self.server_type in ["switch_server", "L7_server"]:
            result = subprocess.run("mbportcmd list", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            self._handle_portcmd_output(output)

    def _handle_portcmd_output(self, output):
        """Handle the output of mbportcmd list to check for disconnected, passive, or stopped ports."""
        disconnected_ports = []
        passive_ports = []
        stopped_ports = []

        current_port_info = ""
        for line in output.splitlines():
            if re.match(r'^\[\s*\d+\]:', line):  # Matches lines like "[ 21]:"
                current_port_info = line
            elif "disconnected" in line or "passive" in line or "stopped" in line:
                state = "disconnected" if "disconnected" in line else "passive" if "passive" in line else "stopped"
                full_info = f"{current_port_info}\n\t{line.strip()}"
                if state == "disconnected":
                    disconnected_ports.append(full_info)
                elif state == "passive":
                    passive_ports.append(full_info)
                elif state == "stopped":
                    stopped_ports.append(full_info)

        if disconnected_ports or passive_ports or stopped_ports:
            if disconnected_ports:
                logging.info("Disconnected ports found:\n" + "\n".join(disconnected_ports))
            if passive_ports:
                logging.info("Passive ports found:\n" + "\n".join(passive_ports))
            if stopped_ports:
                logging.info("Stopped ports found:\n" + "\n".join(stopped_ports))

        self.postvalidation_state["ports"]["disconnected"] = disconnected_ports
        self.postvalidation_state["ports"]["passive"] = passive_ports
        self.postvalidation_state["ports"]["stopped"] = stopped_ports

    def check_bins(self):
        """Check the status of bins."""
        if self.server_type in ["switch_server", "L7_server"]:
            result = subprocess.run("shccmd list", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            self._handle_shccmd_output(output)

    def _handle_shccmd_output(self, output):
        """Handle the output of shccmd list to check for bins that are down."""
        down_bins = []

        current_bin_info = ""
        for line in output.splitlines():
            if re.match(r'^\[\s*\d+\]:', line):  # Matches lines like "[ 1]:"
                if current_bin_info:
                    current_bin_info += f"\n{line.strip()}"
                else:
                    current_bin_info = line.strip()
            elif "Status: Down" in line:
                full_info = f"{current_bin_info}\n\t{line.strip()}"
                down_bins.append(full_info)
                current_bin_info = ""

        if down_bins:
            logging.info("Bins found in down status:\n" + "\n".join(down_bins))

        self.postvalidation_state["bins_down"] = down_bins

    def compare_states(self):
        """Compare pre-validation and post-validation states."""
        if self.prevalidation_state["mailbox_status"] == self.postvalidation_state["mailbox_status"]:
            logging.info("Mailbox status matches pre-validation - OK")
        else:
            logging.error("Mailbox status does not match pre-validation - NOT OK")
            self.overall_status = False

        if self.prevalidation_state["processes"] == self.postvalidation_state["processes"]:
            logging.info("Processes match pre-validation - OK")
        else:
            logging.error("Processes do not match pre-validation - NOT OK")
            self.overall_status = False

        if self.prevalidation_state["ports"]["disconnected"] == self.postvalidation_state["ports"]["disconnected"]:
            logging.info("Disconnected ports match pre-validation - OK")
        else:
            logging.error("Disconnected ports do not match pre-validation - NOT OK")
            self.overall_status = False

        if self.prevalidation_state["ports"]["passive"] == self.postvalidation_state["ports"]["passive"]:
            logging.info("Passive ports match pre-validation - OK")
        else:
            logging.error("Passive ports do not match pre-validation - NOT OK")
            self.overall_status = False

        if self.prevalidation_state["ports"]["stopped"] == self.postvalidation_state["ports"]["stopped"]:
            logging.info("Stopped ports match pre-validation - OK")
        else:
            logging.error("Stopped ports do not match pre-validation - NOT OK")
            self.overall_status = False

        if self.prevalidation_state["bins_down"] == self.postvalidation_state["bins_down"]:
            logging.info("Bins down match pre-validation - OK")
        else:
            logging.error("Bins down do not match pre-validation - NOT OK")
            self.overall_status = False

    def log_post_validation_results(self):
        """Log the results of the post-validation checks."""
        if self.overall_status:
            logging.info("Post-validation completed successfully - ALL OK")
        else:
            logging.error("Post-validation completed with errors - NOT OK")
        self.log_and_exit(EXIT_SUCCESS if self.overall_status else EXIT_POSTVALIDATION_FAILURE)

    def log_and_exit(self, exit_code, message=""):
        """Log the exit code and exit the script."""
        script_name = os.path.basename(__file__)
        log_file = self.failed_log_filename if exit_code != EXIT_SUCCESS else self.log_filename
        status_description = EXIT_CODE_DESCRIPTIONS.get(exit_code, "Unknown status code")

        if exit_code == EXIT_SUCCESS:
            logging.info(status_description)
            print(f"{script_name} completed successfully with exit code: {exit_code}")
        else:
            logging.error(f"{script_name} Failed: {message}")
            logging.error(f"{script_name} Failed with exit code: {exit_code}")
            print(f"{script_name} Failed: {message}")
            print(f"{script_name} Failed with exit code: {exit_code}")

        self.send_email_notification(exit_code, status_description, log_file)
        sys.exit(exit_code)

    def send_email_notification(self, exit_code, status_description, log_file):
        """Send an email notification with the log file attached."""
        script_name = os.path.basename(__file__)
        current_time = datetime.now().strftime("%d-%m-%Y %H:%M")
        subject = f"{script_name} {self.action.capitalize()} Notification - {self.client} {self.environment} {self.region} - {self.hostname} - {current_time}"
        body = f"Script Name: {script_name}\n"
        body += f"Hostname: {self.hostname}\n"
        body += f"Client: {self.client}\n"
        body += f"Environment: {self.environment}\n"
        body += f"Region: {self.region}\n"
        body += f"Server Type: {self.server_type}\n"
        body += f"Action: {self.action}\n"
        body += f"Exit Code: {exit_code}\n"
        body += f"Status: {status_description}\n"
        body += "\nNOTE: This is a system-generated email. In case of any concerns, please reach out to us at support@example.com."

        # Create email message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Attach log file
        with open(log_file, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(log_file)}')
            msg.attach(part)

        # Send email
        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
            server.close()
            logging.info("Email notification sent successfully.")
        except Exception as e:
            logging.error(f"Failed to send email notification. Error: {e}")

    def run(self):
        """Run the specified action (bringup and post-validation)."""
        logging.info(f"Hostname: {self.hostname}")
        logging.info(f"Identified client: {self.client}")
        logging.info(f"Identified environment: {self.environment}")
        logging.info(f"Identified region: {self.region}")
        logging.info(f"Identified server type: {self.server_type}")

        try:
            self.bringup_services()
            self.post_validation()
        except Exception as e:
            logging.error(f"Script execution stopped due to an error: {e}")
            self.log_and_exit(EXIT_GENERAL_FAILURE, "General failure")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Bringup and Post-validation Script.")
    parser.add_argument("action", choices=["postvalidation"], help="Action to perform")
    args = parser.parse_args()

    manager = ServerManager(args.action)
    manager.run()

if __name__ == "__main__":
    main()
