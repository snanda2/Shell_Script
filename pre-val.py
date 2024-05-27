import os
import socket
import subprocess
import logging
from datetime import datetime
import argparse

# Configuration for commands based on client and server type
COMMANDS = {
    "client1": {
        "api_server": {
            "pre_validation": [
                "ps -ef | grep splunkd",
                "ps -ef | grep nxagentd",
                "uname -r",  # Assuming "kernel version" means checking the kernel version
                "ps -ef | grep producer",
                "mbcmd",
                "mbcmd tasks"
            ],
            "shutdown": [
                "echo Client1 API Shutdown Command 1",
                "echo Client1 API Shutdown Command 2"
            ]
        },
        "wso2_server": {
            "pre_validation": [
                "ps -ef | grep wso2 | grep -v grep"
            ],
            "shutdown": [
                "echo Client1 WSO2 Shutdown Command 1",
                "echo Client1 WSO2 Shutdown Command 2"
            ]
        },
        # Add other server types for client1...
    },
    "client2": {
        "api_server": {
            "pre_validation": [
                "ps -ef | grep splunkd",
                "ps -ef | grep nxagentd",
                "uname -r",
                "ps -ef | grep producer",
                "mbcmd",
                "mbcmd tasks"
            ],
            "shutdown": [
                "echo Client2 API Shutdown Command 1",
                "echo Client2 API Shutdown Command 2"
            ]
        },
        "wso2_server": {
            "pre_validation": [
                "ps -ef | grep wso2 | grep -v grep"
            ],
            "shutdown": [
                "echo Client2 WSO2 Shutdown Command 1",
                "echo Client2 WSO2 Shutdown Command 2"
            ]
        },
        # Add other server types for client2...
    },
    "client3": {
        "api_server": {
            "pre_validation": [
                "ps -ef | grep splunkd",
                "ps -ef | grep nxagentd",
                "uname -r",
                "ps -ef | grep producer",
                "mbcmd",
                "mbcmd tasks"
            ],
            "shutdown": [
                "echo Client3 API Shutdown Command 1",
                "echo Client3 API Shutdown Command 2"
            ]
        },
        "wso2_server": {
            "pre_validation": [
                "ps -ef | grep wso2 | grep -v grep"
            ],
            "shutdown": [
                "echo Client3 WSO2 Shutdown Command 1",
                "echo Client3 WSO2 Shutdown Command 2"
            ]
        },
        # Add other server types for client3...
    }
}

class ServerManager:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.client = self.identify_client()
        self.server_type = self.identify_server_type()
        self.log_filename = f"{self.hostname}_{self.client}_{datetime.now().strftime('%Y%m%d')}.log"
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            filename=self.log_filename,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def identify_client(self):
        if "client1" in self.hostname:
            return "client1"
        elif "client2" in self.hostname:
            return "client2"
        elif "client3" in self.hostname:
            return "client3"
        else:
            return "unknown_client"

    def identify_server_type(self):
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
        if self.client not in COMMANDS or self.server_type not in COMMANDS[self.client]:
            logging.error(f"Unknown client ({self.client}) or server type ({self.server_type})")
            return

        commands = COMMANDS[self.client][self.server_type].get(command_type, [])
        for command in commands:
            try:
                result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logging.info(f"Executed command: {command}")
                logging.info(f"Output: {result.stdout.decode().strip()}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to execute command: {command}")
                logging.error(f"Error: {e.stderr.decode().strip()}")

    def pre_validation(self):
        logging.info("Starting pre-validation...")
        self.execute_commands("pre_validation")

    def shutdown(self):
        logging.info("Starting shutdown...")
        self.execute_commands("shutdown")

    def run(self, action):
        logging.info(f"Hostname: {self.hostname}")
        logging.info(f"Identified client: {self.client}")
        logging.info(f"Identified server type: {self.server_type}")

        if action == "prevalidation":
            self.pre_validation()
        elif action == "shutdown":
            self.shutdown()
        else:
            logging.error(f"Unknown action: {action}")

def main():
    parser = argparse.ArgumentParser(description="Server management script.")
    parser.add_argument("action", choices=["prevalidation", "shutdown"], help="Action to perform")
    args = parser.parse_args()

    manager = ServerManager()
    manager.run(args.action)

if __name__ == "__main__":
    main()
