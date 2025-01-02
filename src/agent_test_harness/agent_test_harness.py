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
                results = self.benchmark_agent(next_run["run_name"],next_run["agent"], next_run["repository"])
                self.benchmark.add_result(next_run["run_name"], results)
            except Exception as e:
                logging.error(f"Error benchmarking agent {next_run['agent']['name']} on repository {next_run['repository']['name']}: {e}")
                backtrace = traceback.format_exc()
                agent = next_run["agent"]
                repository = next_run["repository"]
                error_result = {
                    "agent_name": agent["name"],
                    "agent_version": agent["version"],
                    "repository_url": repository["url"],
                    "result": {"error": str(e), "backtrace": backtrace},
                    "run": next_run["run_name"]
                }
                self.benchmark.add_result(next_run["run_name"], error_result)

        return list(self.benchmark.results.values())
    

    def benchmark_agent(self, run_name: str, agent: dict, repository: dict):
        setup_script = repository["setup_script"] + "\n# Agent setup script:\n\n" + agent["setup_script"]

        logging.info(f"Initializing workspace provider for run {run_name}...")

        workspace_provider = WorkspaceProvider(run_name, repository, setup_script)
        workspace_provider.run()

        # TODO also add repository revision
        benchmark_result = {
            "agent_name": agent["name"],
            "agent_version": agent["version"],
            "repository_url": repository["url"],
            "result": {},
            "run": run_name
        }

        logging.info(f"Initializing agent test benchmark for run {run_name}...")
        agent_test_benchmark = AgentTestBenchmark(run_name, self.llm_proxy, workspace_provider, agent, repository)

        logging.info(f"Running agent test benchmark for run {run_name}...")
        benchmark_result["result"] = agent_test_benchmark.run()

        workspace_provider.stop()

        return benchmark_result
