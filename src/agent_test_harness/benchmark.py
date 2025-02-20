import os
import json

class Benchmark:
    name: str
    agents: list[dict]
    instances: list[dict]
    results: dict[str, dict]
    output_path: str

    def __init__(self, name: str, config: dict, agents: list[dict], instances: list[dict]):
        self.name = name
        self.config = config
        self.agents = agents
        self.instances = instances
        self.results = {}

        self.output_path = os.path.join(config["results_path"], name)
        os.makedirs(self.output_path, exist_ok=True)
        
        self.runs_path = os.path.join(self.output_path, "runs")
        os.makedirs(self.runs_path, exist_ok=True)

        for file in os.listdir(self.runs_path):
            with open(os.path.join(self.runs_path, file), "r") as f:
                run_name = file.split(".json")[0]
                self.results[run_name] = json.load(f)

    def run_name(self, agent: dict, instance, iteration: int):
        return f"{agent['name']}-{agent['version']}-{instance.instance_id}-{iteration}"

    def add_result(self, run_name: str, result: dict):
        self.results[run_name] = result
        with open(os.path.join(self.runs_path, f"{run_name}.json"), "w") as f:
            json.dump(result, f, indent=2)

    def next_run(self):
        for agent in self.agents:
            for instance in self.instances:
                for iteration in range(self.config["runs"]):
                    run_name = self.run_name(agent, instance, iteration)
                    if run_name not in self.results:
                        return {
                            "agent": agent,
                            "agent_version": agent["version"],
                            "instance": instance,
                            "run_name": run_name
                        }
        return None