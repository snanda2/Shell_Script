#!/usr/bin/env python3

"""
Auto Patching Script

This script performs pre-validation and shutdown tasks for various server types based on the client configuration.

Author: [Your Name]
Date: [Date]

Usage:
    python script_name.py <action>

    action:
        prevalidation   Perform pre-validation tasks.
        shutdown        Perform shutdown tasks.

Exit Codes:
    EXIT_SUCCESS = 0
    EXIT_GENERAL_FAILURE = 1
    EXIT_PREVALIDATION_FAILURE = 2
    EXIT_SHUTDOWN_FAILURE = 3
    EXIT_COMMAND_EXECUTION_FAILURE = 4
    EXIT_PROCESS_NOT_FOUND = 5
    EXIT_SCRIPT_NOT_FOUND = 6
    EXIT_UNKNOWN_ACTION = 7
    EXIT_UNKNOWN_CLIENT_OR_SERVER = 8
    EXIT_MAILBOX_NOT_ACTIVE = 9
    EXIT_SHARED_MEMORY_SEGMENT_FOUND = 10
"""

import os
import socket
import subprocess
import logging
from datetime import datetime
import argparse
import psutil
import sys
import time
import re

def is_process_running(process_name):
    """Checks if a process is running by name or in its command line arguments.

    Args:
        process_name (str): The name of the process to check.

    Returns:
        bool: True if the process is running, False otherwise.
    """
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        if process_name in process.info['name'] or any(process_name in cmd for cmd in process.info['cmdline']):
            return True
    return False

# Constants for log directory and file extensions
LOG_DIR = "logs"
LOG_EXTENSION = ".log"
FAILED_LOG_SUFFIX = "_failed"
TRIGGER_FILE_DIR = "trigger_files"

# Exit codes
EXIT_SUCCESS = 0
EXIT_GENERAL_FAILURE = 1
EXIT_PREVALIDATION_FAILURE = 2
EXIT_SHUTDOWN_FAILURE = 3
EXIT_COMMAND_EXECUTION_FAILURE = 4
EXIT_PROCESS_NOT_FOUND = 5
EXIT_SCRIPT_NOT_FOUND = 6
EXIT_UNKNOWN_ACTION = 7
EXIT_UNKNOWN_CLIENT_OR_SERVER = 8
EXIT_MAILBOX_NOT_ACTIVE = 9
EXIT_SHARED_MEMORY_SEGMENT_FOUND = 10

# Server and client specific commands
SERVER_SPECIFIC_COMMANDS = {
    "switch_server": {
        "pre_validation": [
            "echo Kernel version below:",
            "uname -r",
            "echo Checking mailbox status below:",
            "echo -e 'exit' | mbcmd",
            "mbcmd tasks",
            "mbportcmd list",
            "shccmd list"
        ],
        "shutdown": [
            "shutdown.sh",
            "pkill oentsrv",
            "istnodeagt stop",
            "cleanipc.sh",
            "ipcs"
        ],
        "processes": ["istnodeagt", "oentsrv", "oassrv", "splunkd", "nxagentd", "producer"]
    },
    "L7_server": {
        "pre_validation": [
            "echo Kernel version below:",
            "uname -r",
            "echo Checking mailbox status below:",
            "echo -e 'exit' | mbcmd",
            "mbcmd tasks",
            "mbportcmd list",
            "shccmd list"
        ],
        "shutdown": [
            "shutdown.sh",
            "istnodeagt stop",
            "cleanipc.sh",
            "ipcs"
        ],
        "processes": ["istnodeagt", "ist-api-services"]
    },
    "wso2_server": {
        "pre_validation":[],
        "shutdown": [
            "/data/wso2/wso2am-3.2.0/bin/wso2server.sh stop",
        ],
        "processes": ["wso2"]
    },
    "gui_server": {
        "pre_validation": [
            "echo GUI pre-validation"
        ],
        "shutdown": [
            "./shutdown.sh",
        ],
        "processes": ["guiproc"]
    },
    "sftp_server": {
        "pre_validation": [
            "echo SFTP pre-validation"
        ],
        "shutdown": [
            "./shutdown.sh",
        ],
        "processes": ["sftpd"]
    }
}

# Configuration for commands based on client and server type
COMMANDS = {
    "client1": SERVER_SPECIFIC_COMMANDS,
    "client2": SERVER_SPECIFIC_COMMANDS,
    "client3": {
        "api_server": {
            "pre_validation": [
                "echo Kernel version below:",
                "uname -r",
                "echo Checking mailbox status below:",
                "echo -e 'exit' | mbcmd",
                "mbcmd tasks"
            ],
            "shutdown": [
                "./shutdown.sh",
                "kill oentsrv"
            ],
            "processes": ["splunkd", "nxagentd", "producer"]
        },
        "wso2_server": {
            "pre_validation": [
                "ps -ef | grep wso2 | grep -v grep"
            ],
            "shutdown": [
                "./shutdown.sh",
                "kill oentsrv"
            ],
            "processes": ["wso2"]
        },
        "gui_server": {
            "pre_validation": [
                "echo GUI pre-validation"
            ],
            "shutdown": [
                "./shutdown.sh",
                "kill oentsrv"
            ],
            "processes": ["guiproc"]
        },
        "sftp_server": {
            "pre_validation": [
                "echo SFTP pre-validation"
            ],
            "shutdown": [
                "./shutdown.sh",
                "kill oentsrv"
            ],
            "processes": ["sftpd"]
        }
    }
}

class ServerManager:
    def __init__(self, action):
        self.hostname = socket.gethostname()
        self.client = self.identify_client()
        self.server_type = self.identify_server_type()
        self.action = action
        self.setup_logging()
        self.overall_status = True  # To track overall script status

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
        if "client1" in hostname_lower:
            return "client1"
        elif "client2" in hostname_lower:
            return "client2"
        elif "client3" in hostname_lower:
            return "client3"
        else:
            return "unknown_client"

    def identify_server_type(self):
        """Identify the server type based on the hostname."""
        hostname_lower = self.hostname.lower()
        if "istap" in hostname_lower:
            return "switch_server"
        elif "l7" in hostname_lower:
            return "L7_server"
        elif "wso2" in hostname_lower:
            return "wso2_server"
        elif "gui" in hostname_lower:
            return "gui_server"
        elif "sftp" in hostname_lower:
            return "sftp_server"
        else:
            return "unknown_server"

    def check_mailbox_status(self):
        """Check the IST Mail Box status."""
        try:
            result = subprocess.run("echo -e '\n exit' | mbcmd", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            filtered_output = self._filter_mbcmd_output(output)
            logging.info(f"Mailbox check output:\n{filtered_output}")

            if "IST Mail Box up since" in filtered_output:
                logging.info("IST Mail Box is up and active.")
                return True
            elif "Mail box system not active" in filtered_output:
                self.log_and_exit(EXIT_MAILBOX_NOT_ACTIVE, "Mailbox is not active")
            else:
                self.log_and_exit(EXIT_MAILBOX_NOT_ACTIVE, "Unexpected mailbox status output")
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode().strip()
            logging.error(f"Failed to check mailbox status. Error:\n{error_output}")
            self.log_and_exit(EXIT_MAILBOX_NOT_ACTIVE, "Failed to check mailbox status")

    @staticmethod
    def _filter_mbcmd_output(output):
        """Filter the output of mbcmd to find relevant information."""
        for line in output.splitlines():
            if "IST Mail Box" in line:
                return line
        return "Desired line not found in mbcmd output."

    def log_and_exit(self, exit_code, message=""):
        """Log the exit code and exit the script."""
        script_name = os.path.basename(__file__)
        if exit_code == EXIT_SUCCESS:
            logging.info("Script completed successfully.")
            self.create_trigger_file(f"{self.action}_successful.trig")
            print(f"{script_name} completed successfully with exit code: {exit_code}")
        else:
            logging.error(f"{script_name} Failed: {message}")
            logging.error(f"{script_name} Failed with exit code: {exit_code}")
            self.create_trigger_file(f"{self.action}_failed.trig")
            print(f"{script_name} Failed: {message}")
            print(f"{script_name} Failed with exit code: {exit_code}")
        sys.exit(exit_code)

    def execute_commands(self, command_type):
        """Execute the commands for the given command type (pre-validation or shutdown)."""
        if self.client not in COMMANDS or self.server_type not in COMMANDS[self.client]:
            self.log_and_exit(EXIT_UNKNOWN_CLIENT_OR_SERVER, "Unknown client or server type")

        if self.server_type in ["switch_server", "L7_server"]:
            if not self.check_mailbox_status():
                logging.error("Mailbox status check failed. Exiting script.")
                return

        commands = COMMANDS[self.client][self.server_type].get(command_type, [])
        for command in commands:
            if "kill" in command:
                process_name = command.split()[1]
                if is_process_running(process_name):
                    logging.info(f"Process {process_name} is running, proceeding to kill.")
                    self._execute_command(command)
                else:
                    logging.info(f"Process {process_name} is not running.")
            elif "cleanipc.sh" in command:
                self._execute_command_synchronously(command)
                time.sleep(10)
            elif "ipcs" in command:
                output = self._execute_command_synchronously(command)
                self._handle_ipcs_output(output)
            elif "mbportcmd list" in command or "shccmd list" in command:
                output = self._execute_command_synchronously(command)
                self._handle_portcmd_output(output)
            else:
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
                self.log_and_exit(EXIT_COMMAND_EXECUTION_FAILURE, "Command not found")
            elif status_code == 126:
                self.log_and_exit(EXIT_COMMAND_EXECUTION_FAILURE, "Command cannot execute")
            elif status_code == 1:
                self.log_and_exit(EXIT_COMMAND_EXECUTION_FAILURE, "General error")
            
            self.overall_status = False

    def _execute_command_synchronously(self, command):
        """Execute a single command synchronously and return the output."""
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            error_output = result.stderr.decode().strip()
            status_code = result.returncode
            logging.info(f"Executed command: {command}")
            logging.info(f"Output:\n{output}")
            logging.info(f"Status code: {status_code}")
            if error_output:
                logging.error(f"Error Output:\n{error_output}")
            if status_code != 0:
                self.overall_status = False
            return output

        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode().strip()
            status_code = e.returncode
            logging.error(f"Failed to execute command: {command}")
            logging.error(f"Error:\n{error_output}")
            logging.error(f"Status code: {status_code}")

            if status_code == 127:
                self.log_and_exit(EXIT_COMMAND_EXECUTION_FAILURE, "Command not found")
            elif status_code == 126:
                self.log_and_exit(EXIT_COMMAND_EXECUTION_FAILURE, "Command cannot execute")
            elif status_code == 1:
                self.log_and_exit(EXIT_COMMAND_EXECUTION_FAILURE, "General error")

            self.overall_status = False
            return None

    def _handle_ipcs_output(self, output):
        """Handle the output of the ipcs command to check for shared memory segments."""
        istadm_found = False

        shared_memory_section = False
        for line in output.splitlines():
            if re.match(r'------\s*Shared Memory Segments\s*------', line):
                shared_memory_section = True
            elif re.match(r'------\s*\w+\s*------', line):
                shared_memory_section = False

            if shared_memory_section and "istadm" in line:
                istadm_found = True
                logging.error(f"Shared memory segment found for istadm: {line}")
                self.log_and_exit(EXIT_SHARED_MEMORY_SEGMENT_FOUND, "Shared memory segment found for istadm")

        if not istadm_found:
            logging.info("No shared memory segments for istadm, shutdown is complete and clean.")
        else:
            logging.error("Shared memory segments for istadm were found during shutdown.")
            self.overall_status = False

    def _handle_portcmd_output(self, output):
        """Handle the output of mbportcmd list and shccmd list to check for disconnected, passive, or stopped ports."""
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

    def pre_validation(self):
        """Perform pre-validation tasks."""
        logging.info("Starting pre-validation...")
        self._check_processes()
        self.execute_commands("pre_validation")

    def _check_processes(self):
        """Check the status of required processes and log the results."""
        processes = COMMANDS[self.client][self.server_type].get("processes", [])
        for process in processes:
            if is_process_running(process):
                logging.info(f"Process {process} is running")
            else:
                logging.warning(f"Process {process} is not running")

    def shutdown(self):
        """Perform shutdown tasks."""
        logging.info("Starting shutdown...")

        if self.server_type == "switch_server" and self.client in ["Chevron", "Intuit"]:
            self._handle_producer_shutdown()
        if self.server_type == "wso2_server":
            self._shutdown_wso2_server()

        if self.server_type == "L7_server":
            self._handle_ist_api_services_shutdown()

        self.execute_commands("shutdown")

    def _handle_producer_shutdown(self):
        """Handle shutdown of producer processes for switch_server."""
        producer_running = False
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            if "prod01" in process.info['cmdline']:
                producer_running = True
                self._shutdown_producer_instance("instance_1")
            elif "prod02" in process.info['cmdline']:
                producer_running = True
                self._shutdown_producer_instance("instance_2")
            else:
                logging.info(f"Skipping non-producer process: {process.info['cmdline']}")

        if not producer_running:
            logging.info("No producer process is running, skipping producer shutdown.")

    def _shutdown_producer_instance(self, instance):
        """Shut down the producer instance by executing the appropriate script."""
        base_path = "/home/istadm/pdir/ositeroot/ist_ddp/"
        instance_path = os.path.join(base_path, instance)

        if os.path.exists(instance_path):
            stop_script_path = os.path.join(instance_path, "stop_ddp.ksh")
        else:
            stop_script_path = os.path.join(base_path, "stop_ddp.ksh")

        if os.path.exists(stop_script_path):
            logging.info(f"Executing {stop_script_path} for {instance}")
            self._execute_command(f"./{stop_script_path}")
        else:
            logging.error(f"Stop script {stop_script_path} not found.")
            # No need to exit or mark overall status as false

    def _shutdown_wso2_server(self):
        """Shutdown wso2 server by executing wso2server.sh with stop argument."""
        wso2_script_path = "/data/wso2/wso2am-3.2.0/bin/wso2server.sh"
        if os.path.exists(wso2_script_path):
            logging.info(f"Executing {wso2_script_path} with stop argument")
            self._execute_command(f"{wso2_script_path} stop")
        else:
            logging.error(f"WSO2 server shutdown script {wso2_script_path} not found.")
            self.log_and_exit(EXIT_SCRIPT_NOT_FOUND, "WSO2 server shutdown script not found")

    def _handle_ist_api_services_shutdown(self):
        """Handle shutdown of ist-api-services for L7 server."""
        ist_api_services_running = False
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            if "ist-api-services" in process.info['cmdline']:
                ist_api_services_running = True
                logging.info("ist-api-services process is running.")
                self._shutdown_ist_api_services()
                break

        if ist_api_services_running:
            logging.info("ist-api-services is running, shutdown initiated.")
        else:
            logging.info("ist-api-services is not running, skipping shutdown.")

    def _shutdown_ist_api_services(self):
        """Shutdown the ist-api-services process."""
        ist_api_services_path = "/home/istadm/istapi/ist-api-services"
        killme_script_path = os.path.join(ist_api_services_path, "killme")

        if os.path.exists(killme_script_path):
            logging.info(f"Executing {killme_script_path} to shut down ist-api-services.")
            self._execute_command(f"./{killme_script_path}")
        else:
            logging.error(f"killme script not found at {killme_script_path}.")
            self.log_and_exit(EXIT_SCRIPT_NOT_FOUND, "killme script not found")

    def create_trigger_file(self, filename):
        """Create a trigger file in the trigger directory."""
        os.makedirs(TRIGGER_FILE_DIR, exist_ok=True)
        trigger_file_path = os.path.join(TRIGGER_FILE_DIR, filename)

        # Remove old trigger files
        for file in os.listdir(TRIGGER_FILE_DIR):
            os.remove(os.path.join(TRIGGER_FILE_DIR, file))

        with open(trigger_file_path, 'w') as file:
            pass

    def run(self):
        """Run the specified action (pre-validation or shutdown)."""
        logging.info(f"Hostname: {self.hostname}")
        logging.info(f"Identified client: {self.client}")
        logging.info(f"Identified server type: {self.server_type}")

        try:
            if self.action == "prevalidation":
                self.pre_validation()
            elif self.action == "shutdown":
                self.shutdown()
            else:
                self.log_and_exit(EXIT_UNKNOWN_ACTION, "Unknown action")
        except Exception as e:
            logging.error(f"Script execution stopped due to an error: {e}")
            self.log_and_exit(EXIT_GENERAL_FAILURE, "General failure")

        # Log the overall status of the script
        if self.overall_status:
            logging.info("Script completed successfully.")
            self.create_trigger_file(f"{self.action}_successful.trig")
            self.log_and_exit(EXIT_SUCCESS)
        else:
            logging.error("Script completed with errors.")
            self.create_trigger_file(f"{self.action}_failed.trig")
            self.log_and_exit(EXIT_GENERAL_FAILURE, "Script completed with errors")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Auto Patching Script.")
    parser.add_argument("action", choices=["prevalidation", "shutdown"], help="Action to perform")
    args = parser.parse_args()

    manager = ServerManager(args.action)
    manager.run()

if __name__ == "__main__":
    main()
