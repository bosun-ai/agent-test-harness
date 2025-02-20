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
import os
import signal
import base64

from dataclasses import dataclass

from .events import events

WORKSPACE_PROVIDER_COMMAND = "derrick --provisioning-mode docker --workspace-config-path <WORKSPACE_CONFIG_PATH> --server-mode http"

@dataclass
class CommandOutput:
    exit_code: int
    output: str

    def succeeded(self) -> bool:
        return self.exit_code == 0

    def failed(self) -> bool:
        return not self.succeeded()

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
        
        command = WORKSPACE_PROVIDER_COMMAND.replace("<WORKSPACE_CONFIG_PATH>", config_path)
        logging.info(f"Running workspace provider with command: {command}")
        self.process = subprocess.Popen(command,
                                        shell=True,
                                        # stdout and stderr are piped to the parent process's stderr
                                        stdout=sys.stderr,
                                        stderr=sys.stderr,
                                        preexec_fn=os.setsid
                                        )
        self.running = True
        events.add_main_exit_event_listener(self.stop)

        # wait for the workspace provider to start by requesting the health endpoint
        logging.info("Waiting for workspace provider to start...")
        while True:
            time.sleep(0.2)
            try:
                self._request("GET", "health")
                break
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
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        # wait for the process to exit
        self.process.wait()
        logging.info("Workspace provider stopped")
        # Check if the process exited cleanly
        if self.process.returncode != 0:
            logging.error(f"Workspace provider exited with code {self.process.returncode}")

    def _request(self, method: str, path: str, **kwargs):
        response = requests.request(method, f"{self.base_url}/{path}", **kwargs)
        if response.status_code >= 400:
            raise Exception(f"Workspace provider returned status code {response.status_code}: {response.text}")
        return response.json()

    def create_workspace(self, env: dict):
        logging.info("Creating workspace...")
        return self._request("POST", "workspaces", json={"env": env})

    def delete_workspace(self, workspace_id: str):
        self._request("DELETE", f"workspaces/{workspace_id}")

    def list_workspaces(self):
        return self._request("GET", "workspaces")

    def run_command(self, workspace_id: str, command: str, env: dict, timeout: int = 10*60):
        return self._request("POST", f"workspaces/{workspace_id}/cmd", json={"cmd": command, "env": env, "timeout": timeout})

    def run_command_with_output(self, workspace_id: str, command: str, env: dict = None) -> CommandOutput:
        result = self._request("POST", f"workspaces/{workspace_id}/cmd_with_output", json={
            "cmd": command,
            "env": env or {}
        })
        return CommandOutput(exit_code=result["exit_code"], output=result["output"])

    def write_file(self, workspace_id: str, path: str, content: bytes):
        content_base64 = base64.b64encode(content).decode("utf-8")
        return self._request("POST", f"workspaces/{workspace_id}/write_file", json={"path": path, "content": content_base64})
    
    def read_file(self, workspace_id: str, path: str):
        return self._request("POST", f"workspaces/{workspace_id}/read_file", json={"path": path})
  