import logging
import time

from .llm_proxy import LLMProxy
from .workspace_provider import WorkspaceProvider

class AgentTestBenchmark:
    run_name: str
    llm_proxy: LLMProxy
    agent: dict
    repository: dict
    workspace_provider: WorkspaceProvider
    project: dict
    workspace: dict
    results: dict
    initial_git_ref: str
    name: str
    repository_name: str

    def __init__(self, name: str, llm_proxy: LLMProxy, workspace_provider: WorkspaceProvider, agent: dict, repository: dict):
        self.llm_proxy = llm_proxy
        self.workspace_provider = workspace_provider
        self.agent = agent
        self.repository = repository
        self.project = None
        self.workspace = None
        self.initial_git_ref = None
        self.results = {}
        self.repository_name = self.repository["name"]
        self.repository_path = "/" + self.repository_name
        self.name = name
        self.files = self.repository["files"]

    def environment_variables(self):
        return {
            "OPENAI_API_BASE": self.llm_proxy.endpoint,
            "OPENAI_API_KEY": self.project['token'],
            "REPOSITORY_URL": self.repository["url"],
            "PROJECT_ROOT": self.repository_path,
            "TEST_COMMAND": self.repository["test_command"],
            "COVERAGE_REPORT_PATH": self.repository["coverage_report_path"],
        }

    # Steps
    # 1. Provide the LLM proxy
    # 2. Provision a workspace with a copy of the git repository
    # 3. Run the coverage tool inside the workspace to establish a baseline
    # 4. Run the agent inside the workspace
    # 5. Run the coverage tool again to determine improvements
    # 6. Run a git diff between the original git repo and the version in the workspace to measure impact
    def run(self):
        logging.info("Provisioning LLM proxy...")
        self.provision_llm_proxy()
        logging.info("Provisioning workspace...")
        self.provision_workspace()
        logging.info("Establishing initial git ref...")
        self.establish_initial_git_ref()
        logging.info("Running coverage tool...")
        self.results["initial_coverage_tool_output"] = self.run_test_command()
        logging.info("Running agent...")
        start_time = time.time()
        self.results["agent_output"] = self.run_agent()
        end_time = time.time()
        self.results["agent_execution_time"] = end_time - start_time
        logging.info("Running coverage tool again...")
        self.results["final_coverage_tool_output"] = self.run_test_command()
        logging.info("Running git diff...")
        self.results["git_diff"] = self.run_git_diff()
        logging.info("Getting LLM metrics...")
        self.results["llm_metrics"] = self.get_llm_metrics()

        return self.results

    def run_command_in_workdir(self, command: str, env=None):
        if env is None:
            env = self.environment_variables()
        else:
            # merge the environment variables
            env = {**self.environment_variables(), **env}
        return self.workspace_provider.run_command_with_output(self.workspace["id"], f"cd {self.repository_path} && {command}", env)

    def provision_llm_proxy(self):
        self.project = self.llm_proxy.create_project(self.name)

    def get_llm_metrics(self):
        return self.llm_proxy.get_metrics(self.project["token"])

    def provision_workspace(self):
        self.workspace = self.workspace_provider.create_workspace(env=self.environment_variables())

    def establish_initial_git_ref(self):
        commit_context = "git config user.name 'agent-test-harness'; git config user.email 'agent-test-harness@example.com';"
        self.initial_git_ref = self.run_command_in_workdir(f"{commit_context} git commit -a -m \"benchmark-head\" 1>/dev/null; git rev-parse HEAD")

    def run_test_command(self):
        return self.run_command_in_workdir(self.repository["test_command"])

    def run_agent(self):
        env = self.environment_variables()
        log = ""
        for file, test_file in self.files:
            log += f"Running agent on file {file}\n"
            this_env = {**env, "FILE_PATH": file, "TEST_FILE_PATH": test_file}
            log += self.run_command_in_workdir(self.agent["command"], this_env)
        return log

    def run_git_diff(self):
        return self.run_command_in_workdir(f"git diff {self.initial_git_ref}")
