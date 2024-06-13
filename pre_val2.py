#!/usr/bin/env python3

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
TRIG_DIR = "trig_files"
LOG_EXTENSION = ".log"
FAILED_LOG_SUFFIX = "_failed"
TRIG_EXTENSION = ".trig"

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

# Server and client specific commands
SERVER_SPECIFIC_COMMANDS = {
    "switch_server": {
        "pre_validation": [
            "echo Kernel version below:",
            "uname -r",
            "echo Checking mailbox status below:",
            "echo -e '\\n exit' | mbcmd",
            "mbcmd tasks"
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
            "echo -e '\\n exit' | mbcmd",
            "mbcmd tasks"
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
        "pre_validation": [],
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
                "echo -e '\\n exit' | mbcmd",
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
        self.create_trig_directory()

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
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_filename),
                logging.FileHandler(self.failed_log_filename),
                logging.StreamHandler(sys.stdout)  # Log to console as well
            ]
        )

    @staticmethod
    def _remove_old_log_files(*log_files):
        """Remove old log files if they exist."""
        for log_file in log_files:
            if os.path.exists(log_file):
                os.remove(log_file)

    def create_trig_directory(self):
        """Create the trig file directory if it doesn't exist."""
        os.makedirs(TRIG_DIR, exist_ok=True)

    def create_trigger_file(self, filename):
        """Create a zero-byte trigger file."""
        trigger_file_path = os.path.join(TRIG_DIR, filename)
        if os.path.exists(trigger_file_path):
            os.remove(trigger_file_path)
        open(trigger_file_path, 'a').close()

    def identify_client(self):
        """Identify the client based on the hostname."""
        if "client1" in self.hostname:
            return "client1"
        elif "client2" in self.hostname:
            return "client2"
        elif "client3" in self.hostname:
            return "client3"
        else:
            return "unknown_client"

    def identify_server_type(self):
        """Identify the server type based on the hostname."""
        if "istap" in self.hostname:
            return "switch_server"
        elif "l7" in self.hostname:
            return "L7_server"
        elif "wso2" in self.hostname:
            return "wso2_server"
        elif "gui" in self.hostname:
            return "gui_server"
        elif "sftp" in self.hostname:
            return "sftp_server"
        else:
            return "unknown_server"

    def execute_commands(self, command_type):
        """Execute the commands for the given command type (pre-validation or shutdown)."""
        if self.client not in COMMANDS or self.server_type not in COMMANDS[self.client]:
            logging.error(f"Unknown client ({self.client}) or server type ({self.server_type})")
            self.create_trigger_file(f"{self.action}_failed{TRIG_EXTENSION}")
            print("Unknown client or server type", file=sys.stderr)
            sys.exit(EXIT_UNKNOWN_CLIENT_OR_SERVER)

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
            else:
                self._execute_command(command)

    def _execute_command(self, command):
        """Execute a single command and log the result."""
        logging.debug(f"Executing command: {command}")
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            error_output = result.stderr.decode().strip()

            logging.info(f"Executed command: {command}")
            logging.info(f"Output:\n{output}")
            if error_output:
                logging.error(f"Error output:\n{error_output}")

            if command == "echo -e '\\n exit' | mbcmd":
                filtered_output = self._filter_mbcmd_output(output)
                logging.info(f"Filtered Output:\n{filtered_output}")
                if "Mail Box up since" in filtered_output:
                    logging.info("Mailbox is active. Continuing with the rest of the script.")
                elif "Mail box system not active" in filtered_output:
                    logging.error("Mail box system not active. Stopping execution.")
                    self.create_trigger_file(f"{self.action}_failed{TRIG_EXTENSION}")
                    print("Mail box system not active. Script will not execute further.")
                    sys.exit(EXIT_GENERAL_FAILURE)

        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode().strip()
            logging.error(f"Failed to execute command: {command}")
            logging.error(f"Error:\n{error_output}")
            print(f"Error: {error_output}", file=sys.stderr)
            sys.exit(EXIT_COMMAND_EXECUTION_FAILURE)

    def _execute_command_synchronously(self, command):
        """Execute a single command synchronously and return the output."""
        logging.debug(f"Executing command: {command}")
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            logging.info(f"Executed command: {command}")
            logging.info(f"Output:\n{output}")
            return output
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode().strip()
            logging.error(f"Failed to execute command: {command}")
            logging.error(f"Error:\n{error_output}")
            print(f"Error: {error_output}", file=sys.stderr)
            sys.exit(EXIT_COMMAND_EXECUTION_FAILURE)

    @staticmethod
    def _filter_mbcmd_output(output):
        """Filter the output of mbcmd to find relevant information."""
        for line in output.splitlines():
            if "Mail Box up since" in line or "Mail box system not active" in line:
                return line
        return "Desired line not found in mbcmd output."

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
                print(f"Error: Shared memory segment found for istadm: {line}", file=sys.stderr)

        if not istadm_found:
            logging.info("No shared memory segments for istadm, shutdown is complete and clean.")
        else:
            logging.error("Shared memory segments for istadm were found during shutdown.")
            sys.exit(EXIT_SHUTDOWN_FAILURE)

    def pre_validation(self):
        """Perform pre-validation tasks."""
        logging.info("Starting pre-validation...")
        if self.server_type in ["switch_server", "L7_server"]:
            mailbox_command = "echo -e '\\n exit' | mbcmd"
            self._execute_command(mailbox_command)
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
        self._check_processes()

        if self.server_type == "switch_server" and self.client in ["client1", "client2"]:
            self._handle_producer_shutdown()
        if self.server_type == "wso2_server":
            self._shutdown_wso2_server()

        if self.server_type == "L7_server":
            self._handle_ist_api_services_shutdown()

        self.execute_commands("shutdown")

    def _handle_producer_shutdown(self):
        """Handle shutdown of producer processes for api_server."""
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
            sys.exit(EXIT_SCRIPT_NOT_FOUND)

    def _shutdown_wso2_server(self):
        """Shutdown wso2 server by executing wso2server.sh with stop argument."""
        wso2_script_path = "/data/wso2/wso2am-3.2.0/bin/wso2server.sh"
        if os.path.exists(wso2_script_path):
            logging.info(f"Executing {wso2_script_path} with stop argument")
            self._execute_command(f"{wso2_script_path} stop")
        else:
            logging.error(f"WSO2 server shutdown script {wso2_script_path} not found.")
            sys.exit(EXIT_SCRIPT_NOT_FOUND)

    def _handle_ist_api_services_shutdown(self):
        """Handle shutdown of ist-api-services for L7 server."""
        ist_api_services_running = False
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            if "ist-api-services" in process.info['cmdline']:
                ist_api_services_running = True
                logging.info("ist-api-services process is running.")
                self._shutdown_ist_api_services()
                break

        if not ist_api_services_running:
            logging.info("ist-api-services is not running, skipping shutdown.")

    def _shutdown_ist_api_services(self):
        """Shutdown the ist-api-services process."""
        ist_api_services_path = "/home/istadm/istapi/ist-api-services"
        killme_script_path = os.path.join(ist_api_services_path, "killme")

        if os.path.exists(killme_script_path):
            logging.info(f"Executing {killme_script_path} to shut down ist-api-services.")
            try:
                result = subprocess.run(f"./{killme_script_path}", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output = result.stdout.decode().strip()
                error_output = result.stderr.decode().strip()
                
                logging.info(f"Executed {killme_script_path} to shut down ist-api-services.")
                logging.info(f"Output:\n{output}")
                if error_output:
                    logging.error(f"Error output:\n{error_output}")
            except subprocess.CalledProcessError as e:
                error_output = e.stderr.decode().strip()
                logging.error(f"Failed to execute {killme_script_path}")
                logging.error(f"Error:\n{error_output}")
                logging.getLogger().error(f"Failed to execute {killme_script_path}", exc_info=True)
                sys.exit(EXIT_COMMAND_EXECUTION_FAILURE)
        else:
            logging.error(f"killme script not found at {killme_script_path}.")
            sys.exit(EXIT_SCRIPT_NOT_FOUND)

    def run(self):
        """Run the specified action (pre-validation or shutdown)."""
        logging.info(f"Hostname: {self.hostname}")
        logging.info(f"Identified client: {self.client}")
        logging.info(f"Identified server type: {self.server_type}")

        try:
            if self.action == "prevalidation":
                self.pre_validation()
                logging.info("Pre-validation completed successfully.")
                self.create_trigger_file("successful_prevalidation.trig")
                print("Pre-validation completed successfully.")
                sys.exit(EXIT_SUCCESS)
            elif self.action == "shutdown":
                self.shutdown()
                logging.info("Shutdown completed successfully.")
                self.create_trigger_file("successful_shutdown.trig")
                print("Shutdown completed successfully.")
                sys.exit(EXIT_SUCCESS)
            else:
                logging.error(f"Unknown action: {self.action}")
                self.create_trigger_file(f"{self.action}_failed.trig")
                print(f"Unknown action: {self.action}", file=sys.stderr)
                sys.exit(EXIT_UNKNOWN_ACTION)
        except Exception as e:
            logging.error(f"Script execution stopped due to an error: {e}")
            self.create_trigger_file(f"{self.action}_failed.trig")
            print(f"Script execution stopped due to an error: {e}", file=sys.stderr)
            sys.exit(EXIT_GENERAL_FAILURE)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Server management script.")
    parser.add_argument("action", choices=["prevalidation", "shutdown"], help="Action to perform")
    args = parser.parse_args()

    manager = ServerManager(args.action)
    manager.run()

if __name__ == "__main__":
    main()
