from .agent_test_benchmark import AgentTestBenchmark
from .workspace_provider import WorkspaceProvider
from .llm_proxy import LLMProxy

class AgentTestHarness:
    llm_proxy: LLMProxy
    config: dict

    def __init__(self, config: dict):
        self.config = config
        self.llm_proxy = LLMProxy(config)

    def benchmark_agents(self):
        benchmark_results = []
        for agent in self.config["agents"]:
            benchmark_results.append(self.benchmark_agent(agent, self.config["repositories"]))

        return benchmark_results

    def benchmark_agent(self, agent: dict, repositories: list[dict]):
        benchmark_results = {
            "agent_name": agent["name"],
            "results": []
        }
        for repository in repositories:
            benchmark_results["results"].append(self.benchmark_agent_on_repository(agent, repository))
        return benchmark_results

    def benchmark_agent_on_repository(self, agent: dict, repository: dict):
        repository_name = repository["url"].split("/")[-1]
        name = f"{agent["name"]}-{repository_name}"

        benchmark_result = {
            "repository_url": repository["url"],
            "results": {}
        }

        setup_script = repository["setup_script"] + "\n# Agent setup script:\n\n" + agent["setup_script"]

        workspace_provider = WorkspaceProvider(name, repository["url"], setup_script)
        workspace_provider.run()

        agent_test_benchmark = AgentTestBenchmark(self.llm_proxy, workspace_provider, agent, repository)

        benchmark_result["results"] = agent_test_benchmark.run()

        return benchmark_result