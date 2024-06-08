#!/usr/bin/env python3

import os
import socket
import subprocess
import logging
from datetime import datetime
import argparse
import psutil

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

# Server and client specific commands
SERVER_SPECIFIC_COMMANDS = {
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
        self.failed_log_handler = logging.FileHandler(self.failed_log_filename)
        self.failed_log_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.failed_log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.failed_log_handler)

    @staticmethod
    def _remove_old_log_files(*log_files):
        """Remove old log files if they exist."""
        for log_file in log_files:
            if os.path.exists(log_file):
                os.remove(log_file)

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
        if "api" in self.hostname:
            return "api_server"
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
            else:
                self._execute_command(command)

    def _execute_command(self, command):
        """Execute a single command and log the result."""
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            logging.info(f"Executed command: {command}")
            
            if command == "echo -e 'exit' | mbcmd":
                filtered_output = self._filter_mbcmd_output(output)
                logging.info(f"Output:\n{filtered_output}")
            else:
                logging.info(f"Output:\n{output}")
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode().strip()
            logging.error(f"Failed to execute command: {command}")
            logging.error(f"Error:\n{error_output}")
            logging.getLogger().error(f"Failed to execute command: {command}", exc_info=True)

    def _filter_mbcmd_output(self, output):
        """Filter the mbcmd output to extract the specific required line."""
        for line in output.splitlines():
            if "IST Mail Box up since" in line:
                return line
        return "Desired line not found in mbcmd output."

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
        self.execute_commands("shutdown")

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
                logging.error(f"Unknown action: {self.action}")
        except Exception as e:
            logging.error(f"Script execution stopped due to an error: {e}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Server management script.")
    parser.add_argument("action", choices=["prevalidation", "shutdown"], help="Action to perform")
    args = parser.parse_args()

    manager = ServerManager(args.action)
    manager.run()

if __name__ == "__main__":
    main()
