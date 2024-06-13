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

# Server and client specific commands
SERVER_SPECIFIC_COMMANDS = {
    "switch_server": {
        "pre_validation": [
            "echo Kernel version below:",
            "uname -r",
            "echo Checking mailbox status below:",
            "echo -e 'exit' | mbcmd",
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
            "echo -e 'exit' | mbcmd",
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
        self.create_trigger_file_dir()

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
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # File handler for detailed logging
        file_handler = logging.FileHandler(self.log_filename)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(file_handler)

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

    def create_trigger_file_dir(self):
        """Create the trigger file directory if it doesn't exist."""
        os.makedirs(TRIGGER_FILE_DIR, exist_ok=True)

    def create_trigger_file(self, filename):
        """Create a zero-byte trigger file."""
        trigger_file_path = os.path.join(TRIGGER_FILE_DIR, filename)
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
            self.create_trigger_file(f"failed_{self.action}.trig")
            self._console_print(f"{self.action.capitalize()} failed")
            sys.exit(EXIT_UNKNOWN_CLIENT_OR_SERVER)

        # Check mailbox status for switch_server and L7_server
        if self.server_type in ["switch_server", "L7_server"]:
            mailbox_status = self._check_mailbox_status()
            if mailbox_status == "Mail box system not active":
                logging.error("IST Mail box is not active")
                self._console_print("IST Mail box is not active")
                self.create_trigger_file(f"failed_{self.action}.trig")
                sys.exit(EXIT_MAILBOX_NOT_ACTIVE)

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
        """Execute a single command asynchronously."""
        logging.info(f"Executing command: {command}")
        try:
            subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            logging.error(f"Command execution failed with error: {e}")
            self._log_to_failed_log(f"Command execution failed for: {command}")
            self.create_trigger_file(f"failed_{self.action}.trig")
            self._console_print(f"{self.action.capitalize()} failed")
            sys.exit(EXIT_COMMAND_EXECUTION_FAILURE)

    def _execute_command_synchronously(self, command):
        """Execute a single command synchronously and return output."""
        logging.info(f"Executing command synchronously: {command}")
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logging.info(f"Command output:\n{result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logging.error(f"Command execution failed with error: {e}")
            self._log_to_failed_log(f"Command execution failed for: {command}")
            self.create_trigger_file(f"failed_{self.action}.trig")
            self._console_print(f"{self.action.capitalize()} failed")
            sys.exit(EXIT_COMMAND_EXECUTION_FAILURE)

    def _handle_ipcs_output(self, output):
        """Handle IPCS output to log used resources."""
        logging.info("Handling IPCS output...")
        # Implement your handling logic based on the IPCS output
        pass

    def _check_mailbox_status(self):
        """Check mailbox status for switch_server and L7_server."""
        logging.info("Checking mailbox status...")
        command = "echo -e '\n exit' | mbcmd"
        output = self._execute_command_synchronously(command)
        if "Mail box system not active" in output:
            return "Mail box system not active"
        elif "IST Mail Box up since" in output:
            return "Mail Box is up and running"
        else:
            logging.error("Unexpected output from mailbox check.")
            self._log_to_failed_log("Unexpected output from mailbox check.")
            self.create_trigger_file(f"failed_{self.action}.trig")
            self._console_print(f"{self.action.capitalize()} failed")
            sys.exit(EXIT_COMMAND_EXECUTION_FAILURE)

    def _log_to_failed_log(self, message):
        """Log a message to the failed log file."""
        logging.error(message)
        self.failed_log_handler.error(message)

    def _console_print(self, message):
        """Print a message to the console if not logging to console."""
        if self.action in ["prevalidation", "shutdown"]:
            print(message)

    def run(self):
        """Run the server management process."""
        logging.info(f"Starting {self.action} process for {self.hostname} ({self.client}, {self.server_type})")
        self.execute_commands(self.action)
        logging.info(f"{self.action.capitalize()} completed successfully for {self.hostname}")
        self.create_trigger_file(f"{self.action}_successful.trig")
        self._console_print(f"{self.action.capitalize()} is successful")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Server Management Script")
    parser.add_argument("action", choices=["prevalidation", "shutdown"], help="Action to perform")
    args = parser.parse_args()

    manager = ServerManager(args.action)
    manager.run()
