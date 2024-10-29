from .llm_proxy import LLMProxy
from .workspace_provider import WorkspaceProvider

class AgentTestBenchmark:
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

    def __init__(self, llm_proxy: LLMProxy, workspace_provider: WorkspaceProvider, agent: dict, repository: dict):
        self.llm_proxy = llm_proxy
        self.workspace_provider = workspace_provider
        self.agent = agent
        self.repository = repository
        self.project = None
        self.workspace = None
        self.initial_git_ref = None
        self.results = {}
        self.repository_name = self.repository["url"].split("/")[-1]
        self.name = f"{self.agent["name"]}-{self.repository_name}"

    # Steps
    # 1. Provide the LLM proxy
    # 2. Provision a workspace with a copy of the git repository
    # 3. Run the coverage tool inside the workspace to establish a baseline
    # 4. Run the agent inside the workspace
    # 5. Run the coverage tool again to determine improvements
    # 6. Run a git diff between the original git repo and the version in the workspace to measure impact
    def run(self):
        self.provision_llm_proxy()
        self.provision_workspace()
        self.establish_initial_git_ref()
        self.results["initial_coverage_tool_output"] = self.run_coverage_tool()
        self.results["agent_output"] = self.run_agent()
        self.results["final_coverage_tool_output"] = self.run_coverage_tool()
        self.results["git_diff"] = self.run_git_diff()
        return self.results

    def provision_llm_proxy(self):
        self.project = self.llm_proxy.create_project(self.name)

    def provision_workspace(self):
        self.workspace = self.workspace_provider.create_workspace()

    def establish_initial_git_ref(self):
        self.initial_git_ref = self.workspace_provider.run_command_with_output(self.workspace["id"], "git rev-parse HEAD")

    def run_coverage_tool(self):
        return self.workspace_provider.run_command_with_output(self.workspace["id"], self.repository["coverage_tool_command"])

    def run_agent(self):
        return self.workspace_provider.run_command_with_output(self.workspace["id"], self.agent["command"])

    def run_git_diff(self):
        return self.workspace_provider.run_command_with_output(self.workspace["id"], f"git diff {self.initial_git_ref}")
