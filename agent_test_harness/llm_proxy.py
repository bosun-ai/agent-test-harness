import requests
import subprocess
import secrets
import os
import threading
import time

from .events import events

LLM_PROXY_COMMAND = "amsterdam"

# LLMProxy is a class that proxies requests to the LLM proxy service
class LLMProxy:
    admin_token: str
    config: dict
    process: subprocess.Popen
    base_url: str
    running: bool

    def __init__(self, config: dict):
        self.admin_token = secrets.token_hex(16)
        self.config = config
        self.process = None
        self.base_url = "http://localhost:50081"
        self.running = False

    def run(self):
        env = os.environ.copy()
        env["ADMIN_TOKEN"] = self.admin_token
        env["PORT"] = "50081"

        self.process = subprocess.Popen(LLM_PROXY_COMMAND, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.running = True
        events.add_main_exit_event_listener(self.stop)

        # wait for the LLM proxy to start by requesting the health endpoint
        while True:
            time.sleep(0.2)
            try:
                response = self._request("GET", "health")
                match response.status_code:
                    case 200:
                        break
                    case _:
                        raise Exception(f"LLM proxy returned unexpected status code: {response.status_code}")
            except requests.exceptions.ConnectionError:
                pass
            except Exception as e:
                print(f"Error: {e}")
                pass

        print("LLM proxy started")

        threading.Thread(target=self.monitor_process, daemon=True).start()

    def monitor_process(self):
        while self.running:
            time.sleep(0.2)
            process = self.process
            process.poll()
            if process.returncode is not None and self.running:
                self.running = False
                print("LLM proxy process exited early")
                process.stdout.close()
                output = process.stdout.read()
                print(output)
                process.stderr.close()
                error = process.stderr.read()
                print(error)
                break

    def stop(self):
        print("Stopping LLM proxy...")
        self.running = False
        self.process.terminate()

    def _request(self, method: str, path: str, **kwargs):
        return requests.request(method, f"{self.base_url}/{path}", **kwargs)

    def create_project(self, project_name: str):
      response = self._request("POST", "admin/v1/projects", headers={"Authorization": f"Bearer {self.admin_token}"}, json={"name": project_name})
      return response.json()
    
    def get_metrics(self, project_token: str):
      response = self._request("GET", "v1/metrics", headers={"Authorization": f"Bearer {project_token}"})
      return response.json()
