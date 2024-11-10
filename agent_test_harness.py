import json
import traceback
import yaml
import argparse
import os

from agent_test_harness.agent_test_harness import AgentTestHarness
from agent_test_harness.events import events

def main():
    print("Running agent test harness...")
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Path to the config file", default="config.yaml")
    args = parser.parse_args()
    config = read_config(args.config)

    try:
        agent_test_harness = AgentTestHarness(config)
        results = agent_test_harness.benchmark_agents()
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {e}\n{traceback.format_exc()}")
        exit(1)
    finally:
        events.trigger_main_exit_event()

def read_config(config_path):
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        exit(1)

    with open(config_path, "r") as file:
        return yaml.safe_load(file)

if __name__ == "__main__":
    main()
