from .agent_test_benchmark import AgentTestBenchmark
from .workspace_provider import WorkspaceProvider
from .llm_proxy import LLMProxy
from .benchmark import Benchmark
import logging
import traceback

class AgentTestHarness:
    llm_proxy: LLMProxy
    config: dict
    runs: int
    benchmark: Benchmark

    def __init__(self, config: dict):
        self.config = config
        self.llm_proxy = LLMProxy(config)
        self.llm_proxy.run()
        self.runs = config["runs"]
        self.benchmark = Benchmark(config)

    def benchmark_agents(self):
        while next_run := self.benchmark.next_run():
            try:
                results = self.benchmark_agent(next_run["agent"], next_run["repository"], next_run["iteration"])
                self.benchmark.add_result(next_run["run_name"], results)
            except Exception as e:
                logging.error(f"Error benchmarking agent {next_run['agent']['name']} on repository {next_run['repository']['name']}: {e}")
                backtrace = traceback.format_exc()
                self.benchmark.add_result(next_run["run_name"], {"error": str(e), "backtrace": backtrace})

        return self.benchmark.results

    def benchmark_agent(self, agent: dict, repositories: list[dict], runs: int = 1):
        benchmark_results = {
            "agent_name": agent["name"],
            "results": []
        }
        for repository in repositories:
            benchmark_results["results"].extend(self.benchmark_agent_on_repository(agent, repository))
        return benchmark_results

    def benchmark_agent_on_repository(self, agent: dict, repository: dict):
        repository_name = repository["name"]
        name = f"{agent['name']}-{repository_name}"

        setup_script = repository["setup_script"] + "\n# Agent setup script:\n\n" + agent["setup_script"]

        workspace_provider = WorkspaceProvider(name, repository, setup_script)
        workspace_provider.run()

        logging.info(f"Running {self.runs} runs for agent {agent['name']} on repository {repository_name}...")
        benchmark_results = []
        for iteration in range(self.runs):
            run_name = f"{name}-{iteration}"
            benchmark_result = {
                "repository_url": repository["url"],
                "results": {},
                "run": run_name
            }

            logging.info(f"Initializing agent test benchmark for run {run_name}...")
            agent_test_benchmark = AgentTestBenchmark(run_name, self.llm_proxy, workspace_provider, agent, repository)

            logging.info(f"Running agent test benchmark for run {run_name}...")
            benchmark_result["results"] = agent_test_benchmark.run()
            benchmark_results.append(benchmark_result)

        workspace_provider.stop()

        return benchmark_results