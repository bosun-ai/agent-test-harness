# WorkspaceProvider is a class that provides access to workspaces through the workspace-provider utility
#  
# The utility is an executable with the following usage:
#   Usage: derrick --provisioning-mode <PROVISIONING_MODE> --workspace-config-path <WORKSPACE_CONFIG_PATH> --server-mode <SERVER_MODE> 

import subprocess
import requests
import json

WORKSPACE_PROVIDER_COMMAND = "derrick --provisioning-mode docker --workspace-config-path workspace_config.json --server-mode http"

class WorkspaceProvider:
    process: subprocess.Popen
    workspace_config: dict
    base_url: str = "http://localhost:50080"

    def __init__(self, name: str, repository: str, setup_script: str):
        repo_name = repository.split("/")[-1]
        self.workspace_config = {
            "name": name,
            "repositories": [{"url": repository, "path": "/" + repo_name}],
            "setup_script": setup_script
        }
        self.process = None

    def run(self):
        # TODO: Write the workspace config to a file and pass the path to the workspace-provider command
        with open("workspace_config.json", "w") as f:
            json.dump(self.workspace_config, f)
        
        self.process = subprocess.Popen(WORKSPACE_PROVIDER_COMMAND, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop(self):
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
  