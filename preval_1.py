#!/usr/bin/env python3

import os
import socket
import subprocess
import logging
from datetime import datetime
import argparse
import psutil
import re
import sys
import time

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
        "shutdown": [
            "cleanipc.sh",        # Run cleanipc.sh first
            "ipcs",               # Then run ipcs
            "./shutdown.sh",
            "kill oentsrv"
        ],
        "processes": ["splunkd", "nxagentd", "producer"]
    },
    "wso2_server": {
        "shutdown": [
            "/data/wso2/wso2am-3.2.0/bin/wso2server.sh stop",
            "kill oentsrv"
        ],
        "processes": ["wso2"]
    },
    "gui_server": {
        "shutdown": [
            "./shutdown.sh",
            "kill oentsrv"
        ],
        "processes": ["guiproc"]
    },
    "sftp_server": {
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
    "client3": SERVER_SPECIFIC_COMMANDS
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
        """Execute the commands for the given command type (shutdown)."""
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
            elif "cleanipc.sh" in command:
                self._execute_command_synchronously(command)
                time.sleep(10)  # Wait for 10 seconds after running cleanipc.sh
            elif "ipcs" in command:
                output = self._execute_command_synchronously(command)
                self._handle_ipcs_output(output)
            else:
                self._execute_command(command)

    def _execute_command(self, command):
        """Execute a single command and log the result."""
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            error_output = result.stderr.decode().strip()
            logging.info(f"Executed command: {command}")
            logging.info(f"Output:\n{output}")
            if error_output:
                logging.error(f"Error Output:\n{error_output}")
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode().strip()
            logging.error(f"Failed to execute command: {command}")
            logging.error(f"Error:\n{error_output}")
            logging.getLogger().error(f"Failed to execute command: {command}", exc_info=True)

    def _execute_command_synchronously(self, command):
        """Execute a single command synchronously and return the output."""
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            error_output = result.stderr.decode().strip()
            logging.info(f"Executed command: {command}")
            logging.info(f"Output:\n{output}")
            if error_output:
                logging.error(f"Error Output:\n{error_output}")
            return output
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode().strip()
            logging.error(f"Failed to execute command: {command}")
            logging.error(f"Error:\n{error_output}")
            logging.getLogger().error(f"Failed to execute command: {command}", exc_info=True)
            return ""

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
            sys.exit(1)

    def shutdown(self):
        """Perform shutdown
