# WorkspaceProvider is a class that provides access to workspaces through the workspace-provider utility
#  
# The utility is an executable with the following usage:
#   Usage: derrick --provisioning-mode <PROVISIONING_MODE> --workspace-config-path <WORKSPACE_CONFIG_PATH> --server-mode <SERVER_MODE> 

import subprocess
import threading
import time
import requests
import json
import logging
import sys
import uuid
from .events import events

WORKSPACE_PROVIDER_COMMAND = "derrick --provisioning-mode docker --workspace-config-path <WORKSPACE_CONFIG_PATH> --server-mode http"

class WorkspaceProvider:
    process: subprocess.Popen
    workspace_config: dict
    base_url: str = "http://localhost:50080"
    running: bool

    def __init__(self, name: str, repository: dict, setup_script: str):
        logging.info(f"Initializing workspace provider for {name}...")
        self.workspace_config = {
            "name": name,
            "repositories": [{"url": repository["url"], "path": "/" + repository["name"]}],
            "setup_script": setup_script
        }
        self.process = None
        self.running = False

    def run(self):
        # Write the workspace config to a random temporary file
        config_path = f"tmp/workspace_config_{uuid.uuid4()}.json"

        with open(config_path, "w") as f:
            json.dump(self.workspace_config, f)
        
        self.process = subprocess.Popen(WORKSPACE_PROVIDER_COMMAND.replace("<WORKSPACE_CONFIG_PATH>", config_path),
                                        shell=True,
                                        # stdout and stderr are piped to the parent process's stderr
                                        stdout=sys.stderr,
                                        stderr=sys.stderr,
                                        )
        self.running = True
        events.add_main_exit_event_listener(self.stop)

        # wait for the workspace provider to start by requesting the health endpoint
        logging.info("Waiting for workspace provider to start...")
        while True:
            time.sleep(0.2)
            try:
                response = self._request("GET", "health")
                match response.status_code:
                    case 200:
                        break
                    case _:
                        raise Exception(f"Workspace provider returned unexpected status code: {response.status_code}")
            except requests.exceptions.ConnectionError:
                pass
            except Exception as e:
                logging.error(f"Error: {e}")
                pass

            if not self.running:
                # self.process.stdout.close()
                # output = self.process.stdout.read()
                # logging.error(output)
                # self.process.stderr.close()
                # error = self.process.stderr.read()
                # logging.error(error)
                raise Exception("Workspace provider failed to start")

        logging.info("Workspace provider started")

        threading.Thread(target=self.monitor_process, daemon=True).start()

    def monitor_process(self):
        while self.running:
            time.sleep(0.2)
            process = self.process
            process.poll()
            if process.returncode is not None and self.running:
                self.running = False
                logging.error("workspace provider process exited early")
                # process.stdout.close()
                # output = process.stdout.read()
                # logging.error(output)
                # process.stderr.close()
                # error = process.stderr.read()
                # logging.error(error)
                break

    def stop(self):
        logging.info("Stopping workspace provider...")
        self.running = False
        self.process.terminate()
        # wait for the process to exit
        self.process.wait()
        logging.info("Workspace provider stopped")
        # Check if the process exited cleanly
        if self.process.returncode != 0:
            logging.error(f"Workspace provider exited with code {self.process.returncode}")

    def _request(self, method: str, path: str, **kwargs):
        return requests.request(method, f"{self.base_url}/{path}", **kwargs)

    def create_workspace(self, env: dict):
        response = self._request("POST", "workspaces", json={"env": env})
        return response.json()

    def delete_workspace(self, workspace_id: str):
        self._request("DELETE", f"workspaces/{workspace_id}")

    def list_workspaces(self):
        response = self._request("GET", "workspaces")
        return response.json()

    def run_command(self, workspace_id: str, command: str, env: dict):
        response = self._request("POST", f"workspaces/{workspace_id}/cmd", json={"cmd": command, "env": env})
        return response.json()

    def run_command_with_output(self, workspace_id: str, command: str, env: dict):
        response = self._request("POST", f"workspaces/{workspace_id}/cmd_with_output", json={"cmd": command, "env": env})
        return response.json()
    
    def write_file(self, workspace_id: str, path: str, content: str):
        response = self._request("POST", f"workspaces/{workspace_id}/write_file", json={"path": path, "content": content})
        return response.json()
    
    def read_file(self, workspace_id: str, path: str):
        response = self._request("POST", f"workspaces/{workspace_id}/read_file", json={"path": path})
        return response.json()
  