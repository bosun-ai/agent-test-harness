# WorkspaceProvider is a class that provides access to workspaces through the workspace-provider utility
#  
# The utility is an executable with the following usage:
#   Usage: derrick --provisioning-mode <PROVISIONING_MODE> --workspace-config-path <WORKSPACE_CONFIG_PATH> --server-mode <SERVER_MODE> 

import subprocess
import threading
import time
import requests
import json

from .events import events

WORKSPACE_PROVIDER_COMMAND = "derrick --provisioning-mode docker --workspace-config-path workspace_config.json --server-mode http"

class WorkspaceProvider:
    process: subprocess.Popen
    workspace_config: dict
    base_url: str = "http://localhost:50080"
    running: bool

    def __init__(self, name: str, repository: str, setup_script: str):
        repo_name = repository.split("/")[-1]
        self.workspace_config = {
            "name": name,
            "repositories": [{"url": repository, "path": "/" + repo_name}],
            "setup_script": setup_script
        }
        self.process = None
        self.running = False

    def run(self):
        # TODO: Write the workspace config to a file and pass the path to the workspace-provider command
        with open("workspace_config.json", "w") as f:
            json.dump(self.workspace_config, f)
        
        self.process = subprocess.Popen(WORKSPACE_PROVIDER_COMMAND, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.running = True
        events.add_main_exit_event_listener(self.stop)

        # wait for the workspace provider to start by requesting the health endpoint
        print("Waiting for workspace provider to start...")
        while True:
            time.sleep(0.2)
            print("Checking if workspace provider is running...")
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
                print(f"Error: {e}")
                pass

        print("Workspace provider started")

        threading.Thread(target=self.monitor_process, daemon=True).start()

    def monitor_process(self):
        while self.running:
            time.sleep(0.2)
            process = self.process
            process.poll()
            if process.returncode is not None and self.running:
                self.running = False
                print("workspace provider process exited early")
                process.stdout.close()
                output = process.stdout.read()
                print(output)
                process.stderr.close()
                error = process.stderr.read()
                print(error)
                break

    def stop(self):
        print("Stopping workspace provider...")
        self.running = False
        self.process.terminate()

    def _request(self, method: str, path: str, **kwargs):
        return requests.request(method, f"{self.base_url}/{path}", **kwargs)

    def create_workspace(self):
        response = self._request("POST", "workspaces")
        return response.json()

    def delete_workspace(self, workspace_id: str):
        self._request("DELETE", f"workspaces/{workspace_id}")

    def list_workspaces(self):
        response = self._request("GET", "workspaces")
        return response.json()
    
    def run_command(self, workspace_id: str, command: str):
        response = self._request("POST", f"workspaces/{workspace_id}/cmd", json={"command": command})
        return response.json()
    
    def run_command_with_output(self, workspace_id: str, command: str):
        response = self._request("POST", f"workspaces/{workspace_id}/cmd_with_output", json={"command": command})
        return response.json()
    
    def write_file(self, workspace_id: str, path: str, content: str):
        response = self._request("POST", f"workspaces/{workspace_id}/write_file", json={"path": path, "content": content})
        return response.json()
    
    def read_file(self, workspace_id: str, path: str):
        response = self._request("POST", f"workspaces/{workspace_id}/read_file", json={"path": path})
        return response.json()
  