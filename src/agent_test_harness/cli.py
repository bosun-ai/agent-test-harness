import json
import traceback
import argparse
import os
import logging
import yaml
import subprocess
import shutil
from typing import Dict, Any, Optional

from .agent_test_harness import AgentTestHarness
from .events import events
from .report_results import report_results
from .benchmark_config import BenchmarkConfig

class Cli:
    def __init__(self):
        self.args: Optional[argparse.Namespace] = None
        self.config: Optional[Dict[str, Any]] = None

    def parse_args(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("-c", "--config", help="Path to the config file", default="config.yaml")
        parser.add_argument("--report-results", help="Report results into a JSON file", default=False, action="store_true")
        parser.add_argument("--print-config", help="Print the final configuration and exit", default=False, action="store_true")
        parser.add_argument("--agent", help="Run a specific agent (overrides config)")
        parser.add_argument("--repository", help="Run against a specific repository (overrides config)")
        self.args = parser.parse_args()

    def read_config(self, path: str) -> dict:
        if not os.path.exists(self.args.config):
            logging.error(f"Config file not found: {self.args.config}")
            exit(1)
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def initialize(self) -> None:
        """Load and validate configuration"""
        self.check_required_executables()
        # If both agent and repository are specified, we don't need a config file
        if self.args.agent and self.args.repository:
            # Create a config with just the specified agent and repository
            config = {
                "agents": [{
                    "name": self.args.agent
                }],
                "repositories": [{
                    "name": self.args.repository
                }],
                "runs": 1,
                "results_path": "results"
            }
        else:
            # Handle partial override
            if self.args.agent or self.args.repository:
                logging.error("Both --agent and --repository must be specified together")
                exit(1)

            # Otherwise load from config file
            config = self.read_config(self.args.config)


        # Initialize benchmark config with loaded config
        self.config = BenchmarkConfig(config).config
        self.setup_logging()

    def execute(self) -> None:
        """Execute the CLI command based on arguments"""
        if self.args.print_config:
            print(json.dumps(self.config, indent=2))
            return

        if self.args.report_results:
            self.report_results()
            return

        self.run_benchmark()

    def run_benchmark(self) -> None:
        """Run the benchmark suite"""
        logging.info("Running agent test harness...")
        try:
            agent_test_harness = AgentTestHarness(self.config)
            results = agent_test_harness.benchmark_agents()
            print(json.dumps(results, indent=2))
            self.export_results(results)
        except Exception as e:
            logging.error(f"Error: {e}\n{traceback.format_exc()}")
            exit(1)
        finally:
            events.trigger_main_exit_event()

    def report_results(self) -> None:
        """Generate and export results report"""
        logging.info("Reporting results...")
        results = json.load(open("tmp/results/results.json", "r"))
        self.export_results(results)

    def export_results(self, results: Dict[str, Any]) -> None:
        """Export results to JSON files"""
        os.makedirs("tmp/results", exist_ok=True)
        agents_stats = report_results(results)
        with open("tmp/results/agent_stats.json", "w") as f:
            json.dump(agents_stats, f, indent=2)

    def setup_logging(self) -> None:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def check_required_executables(self) -> None:
        """Check if required executables are present and install them if not."""
        required_executables = {
            'amsterdam': 'amsterdam',
            'derrick': 'derrick'
        }
        
        for executable, package in required_executables.items():
            if shutil.which(executable) is None:
                logging.info(f"{executable} not found, attempting to install...")
                try:
                    subprocess.run(['cargo', 'install', package], check=True)
                    logging.info(f"Successfully installed {executable}")
                except subprocess.CalledProcessError as e:
                    logging.error(f"Failed to install {executable}: {e}")
                    exit(1)
