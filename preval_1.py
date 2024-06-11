    def shutdown(self):
        """Perform shutdown tasks."""
        logging.info("Starting shutdown...")

        for process_name in SERVER_SPECIFIC_COMMANDS[self.server_type]["processes"]:
            if is_process_running(process_name):
                logging.info(f"{process_name} process is running.")
            else:
                logging.info(f"{process_name} process is not running.")

        if self.server_type == "api_server" and self.client in ["client1", "client2"]:
            self._handle_producer_shutdown()

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

def main(action):
    server_manager = ServerManager(action)
    if action == "shutdown":
        server_manager.shutdown()
    else:
        logging.error(f"Unknown action: {action}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Server Manager")
    parser.add_argument("action", choices=["shutdown"], help="Action to perform")
    args = parser.parse_args()
    main(args.action)
