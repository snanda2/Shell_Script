import os
import socket
import subprocess
import logging
from datetime import datetime
import argparse
import psutil

# Configuration for commands based on client and server type
COMMANDS = {
    "client1": {
        "api_server": {
            "pre_validation": [
                "uname -r",  # Assuming "kernel version" means checking the kernel version
                "mbcmd",
                "mbcmd tasks"
            ],
            "shutdown": [
                "echo Client1 API Shutdown Command 1",
                "echo Client1 API Shutdown Command 2"
            ],
            "processes": ["splunkd", "nxagentd", "producer"]
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
                "uname -r",
                "mbcmd",
                "mbcmd tasks"
            ],
            "shutdown": [
                "echo Client2 API Shutdown Command 1",
                "echo Client2 API Shutdown Command 2"
            ],
            "processes": ["splunkd", "nxagentd", "producer"]
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
                "uname -r",
                "mbcmd",
                "mbcmd tasks"
            ],
            "shutdown": [
                "echo Client3 API Shutdown Command 1",
                "echo Client3 API Shutdown Command 2"
            ],
            "processes": ["splunkd", "nxagentd", "producer"]
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
        self.setup_logging()

    def setup_logging(self):
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        base_log_filename = f"{self.hostname}_{self.client}_{date_str}"
        self.log_filename = os.path.join(log_dir, f"{base_log_filename}.log")
        self.failed_log_filename = os.path.join(log_dir, f"{base_log_filename}_failed.log")
        
        # Remove old log files if they exist
        if os.path.exists(self.log_filename):
            os.remove(self.log_filename)
        if os.path.exists(self.failed_log_filename):
            os.remove(self.failed_log_filename)

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

    def check_process_running(self, process_name):
        for proc in psutil.process_iter(['pid', 'name']):
            if process_name in proc.info['name']:
                return True
        return False

    def execute_commands(self, command_type):
        if self.client not in COMMANDS or self.server_type not in COMMANDS[self.client]:
            logging.error(f"Unknown client ({self.client}) or server type ({self.server_type})")
            return

        if command_type == "pre_validation" and "processes" in COMMANDS[self.client][self.server_type]:
            processes = COMMANDS[self.client][self.server_type]["processes"]
            for process in processes:
                if not self.check_process_running(process):
                    logging.error(f"Process {process} is not running")
                    raise Exception(f"Process {process} is not running")

        commands = COMMANDS[self.client][self.server_type].get(command_type, [])
        for command in commands:
            try:
                result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output = result.stdout.decode().strip()
                logging.info(f"Executed command: {command}")
                logging.info(f"Output: {output}")
            except subprocess.CalledProcessError as e:
                error_output = e.stderr.decode().strip()
                logging.error(f"Failed to execute command: {command}")
                logging.error(f"Error: {error_output}")
                raise

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

        try:
            if action == "prevalidation":
                self.pre_validation()
            elif action == "shutdown":
                self.shutdown()
            else:
                logging.error(f"Unknown action: {action}")
        except Exception as e:
            logging.error(f"Script execution stopped due to an error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Server management script.")
    parser.add_argument("action", choices=["prevalidation", "shutdown"], help="Action to perform")
    args = parser.parse_args()

    manager = ServerManager()
    manager.run(args.action)

if __name__ == "__main__":
    main()
