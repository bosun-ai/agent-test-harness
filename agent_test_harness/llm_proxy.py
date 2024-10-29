import requests
import subprocess
import secrets
import os
LLM_PROXY_COMMAND = "amsterdam-prompt-gateway"

# LLMProxy is a class that proxies requests to the LLM proxy service
class LLMProxy:
    admin_token: str
    config: dict
    process: subprocess.Popen
    base_url: str

    def __init__(self, config: dict):
        self.admin_token = secrets.token_hex(16)
        self.config = config
        self.process = None
        self.base_url = "http://localhost:50081"

    def run(self):
        env = os.environ.copy()
        env["ADMIN_TOKEN"] = self.admin_token
        env["PORT"] = "50081"

        self.process = subprocess.Popen(LLM_PROXY_COMMAND, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    def stop(self):
        self.process.terminate()

    def _request(self, method: str, path: str, **kwargs):
        return requests.request(method, f"{self.base_url}/{path}", **kwargs)

    def create_project(self, project_name: str):
      response = self._request("POST", "admin/v1/projects", headers={"Authorization": f"Bearer {self.admin_token}"}, json={"name": project_name})
      return response.json()
    
    def get_metrics(self, project_token: str):
      response = self._request("GET", "v1/metrics", headers={"Authorization": f"Bearer {project_token}"})
      return response.json()
