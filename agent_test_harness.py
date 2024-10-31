import json
import yaml
from agent_test_harness.agent_test_harness import AgentTestHarness

def main():
    print("Running agent test harness...")
    config = read_config()
    agent_test_harness = AgentTestHarness(config)
    results = agent_test_harness.benchmark_agents()
    print(json.dumps(results, indent=2))

def read_config():
    with open("config.yaml", "r") as file:
        return yaml.safe_load(file)

if __name__ == "__main__":
    main()
