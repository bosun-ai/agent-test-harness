import json
import requests
import subprocess
import secrets
import os
import threading
import time
import logging
import sys

from .events import events

LLM_PROXY_COMMAND = "amsterdam"

# LLMProxy is a class that proxies requests to the LLM proxy service
class LLMProxy:
    admin_token: str
    config: dict
    process: subprocess.Popen
    base_url: str
    running: bool
    endpoint: str

    def __init__(self, config: dict):
        self.admin_token = secrets.token_hex(16)
        self.config = config
        self.process = None
        self.base_url = "http://localhost:50081"
        self.endpoint = "http://host.docker.internal:50081/v1/openai/v1"
        self.running = False

    def run(self):
        env = os.environ.copy()
        env["RUST_LOG"] = "debug"
        env["ADMIN_TOKEN"] = self.admin_token
        env["PORT"] = "50081"
        env["DATABASE_URL"] = "sqlite://tmp/llm_proxy.db"

        logging.info("Starting LLM proxy...")
        self.process = subprocess.Popen(LLM_PROXY_COMMAND,
                                        shell=True,
                                        # stdout and stderr are piped to the parent process's stderr
                                        stdout=sys.stderr,
                                        stderr=sys.stderr,
                                        env=env)
        self.running = True
        events.add_main_exit_event_listener(self.stop)

        # wait for the LLM proxy to start by requesting the health endpoint
        while True:
            time.sleep(0.2)
            logging.info("Checking if LLM proxy is running...")
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
                logging.error(f"Error: {e}")
                pass

        logging.info("LLM proxy started")

        threading.Thread(target=self.monitor_process, daemon=True).start()

    def monitor_process(self):
        while self.running:
            time.sleep(0.2)
            process = self.process
            process.poll()
            if process.returncode is not None and self.running:
                self.running = False
                logging.error("LLM proxy process exited early")
                process.stdout.close()
                output = process.stdout.read()
                logging.error(output)
                process.stderr.close()
                error = process.stderr.read()
                logging.error(error)
                break

    def stop(self):
        logging.info("Stopping LLM proxy...")
        self.running = False
        self.process.terminate()

    def _request(self, method: str, path: str, **kwargs):
        response = requests.request(method, f"{self.base_url}/{path}", **kwargs)

        if response.status_code >= 400:
            raise Exception(f"LLM proxy returned status code {response.status_code}: {response.text}")
        
        try:
            response.json()
        except json.JSONDecodeError:
            raise Exception(f"LLM proxy returned status code {response.status_code}: {response.text}")
        
        return response

    def create_project(self, project_name: str):
        logging.info(f"Creating project {project_name}...")
        response = self._request("POST", "admin/v1/projects", headers={"Authorization": f"Bearer {self.admin_token}"}, json={
            "name": project_name,
          "description": "Created by agent test harness"
        })
        logging.info(f"Project created: {response.json()}")
        return response.json()
    
    def get_metrics(self, project_token: str):
      response = self._request("GET", "v1/metrics", headers={"Authorization": f"Bearer {project_token}"})
      return response.json()
