import json
import traceback
import yaml
import argparse
import os
import logging
from pycobertura import Cobertura, CoberturaDiff

from agent_test_harness.agent_test_harness import AgentTestHarness
from agent_test_harness.events import events

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Path to the config file", default="config.yaml")
    parser.add_argument("--organize-results", help="Organize results into a JSON file", default=False, action="store_true") 
    args = parser.parse_args()
    config = read_config(args.config)
    setup_logging(config)
    logging.info("Running agent test harness...")

    if args.organize_results:
        logging.info("Organizing results...")
        results = json.load(open("tmp/results/results.json", "r"))
        organize_results(results)
        return
    else:
        logging.info("Running agent test harness...")

    try:
        agent_test_harness = AgentTestHarness(config)
        results = agent_test_harness.benchmark_agents()

        organize_results(results)

        print(json.dumps(results, indent=2))
    except Exception as e:
        logging.error(f"Error: {e}\n{traceback.format_exc()}")
        exit(1)
    finally:
        events.trigger_main_exit_event()

def organize_results(results):
    os.makedirs("tmp/results", exist_ok=True)
    agents_stats = []
    for agent_result in results:
        agent_name = agent_result["agent_name"]
        repository_stats = []
        logging.info(f"Organizing results for agent: {agent_name}")
        for repository_result in agent_result["results"]:
            repository_url = repository_result["repository_url"]
            repository_results = repository_result["results"]
            llm_metrics = repository_results["llm_metrics"]
            run_id = repository_results["run"] if "run" in repository_results else None
            # unique models
            models = list(set([llm_metric["model_name"] for llm_metric in llm_metrics]))
            coverage_report = generate_coverage_report(repository_results)
            coverage_after = coverage_report["coverage_after"]
            coverage_before = coverage_report["coverage_before"]
            coverage_diff = coverage_report["coverage_diff"]
            repository_stats.append({
                "repository_url": repository_url,
                "run_id": run_id,
                "successful": coverage_after is not None,
                "coverage_before": {
                    "line_rate": coverage_before.line_rate(),
                    "branch_rate": coverage_before.branch_rate(),
                    "total_statements": coverage_before.total_statements(),
                    "total_misses": coverage_before.total_misses(),
                } if coverage_before else None,
                "coverage_after": {
                    "line_rate": coverage_after.line_rate(),
                    "branch_rate": coverage_after.branch_rate(),
                    "total_statements": coverage_after.total_statements(),
                    "total_misses": coverage_after.total_misses(),
                } if coverage_after else None,
                "coverage_diff": {
                    "line_rate": coverage_diff.diff_line_rate(),
                    "total_statements": coverage_diff.diff_total_statements(),
                    "total_misses": coverage_diff.diff_total_misses(),
                } if coverage_diff else None,
                "agent_execution_time": repository_results["agent_execution_time"],
                "total_completion_tokens": sum([llm_metric["completion_token_count"] for llm_metric in llm_metrics]),
                "completions_count": len(llm_metrics),
                "total_prompt_tokens": sum([llm_metric["prompt_token_count"] for llm_metric in llm_metrics]),
                "total_token_count": sum([llm_metric["total_token_count"] for llm_metric in llm_metrics]),
                "models": [
                    {
                        "name": model,
                        "completions_count": len([llm_metric for llm_metric in llm_metrics if llm_metric["model_name"] == model]),
                        "total_completion_tokens": sum([llm_metric["completion_token_count"] for llm_metric in llm_metrics if llm_metric["model_name"] == model]),
                        "total_prompt_tokens": sum([llm_metric["prompt_token_count"] for llm_metric in llm_metrics if llm_metric["model_name"] == model]),
                        "total_token_count": sum([llm_metric["total_token_count"] for llm_metric in llm_metrics if llm_metric["model_name"] == model]),
                    } for model in models
                ]
            })
        successful_repositories = [repository_stat for repository_stat in repository_stats if repository_stat["successful"]]
        agent_stats = {
            "name": agent_name,
            "runs": repository_stats,
            "total_completion_tokens": sum([repository_stat["total_completion_tokens"] for repository_stat in repository_stats]),
            "total_prompt_tokens": sum([repository_stat["total_prompt_tokens"] for repository_stat in repository_stats]),
            "total_token_count": sum([repository_stat["total_token_count"] for repository_stat in repository_stats]),
            "runs_count": len(repository_stats),
            "successful_runs_count": len(successful_repositories),
            "average_coverage_diff": sum([repository_stat["coverage_diff"]["line_rate"] for repository_stat in successful_repositories]) / len(successful_repositories) if successful_repositories else None,
            "average_agent_execution_time": sum([repository_stat["agent_execution_time"] for repository_stat in repository_stats]) / len(repository_stats) if repository_stats else None,
            "models": [
                {
                    "name": model,
                    "total_completion_tokens": sum([repository_stat["models"][i]["total_completion_tokens"] for i, repository_stat in enumerate(repository_stats) if repository_stat["models"][i]["name"] == model]),
                    "total_prompt_tokens": sum([repository_stat["models"][i]["total_prompt_tokens"] for i, repository_stat in enumerate(repository_stats) if repository_stat["models"][i]["name"] == model]),
                    "total_token_count": sum([repository_stat["models"][i]["total_token_count"] for i, repository_stat in enumerate(repository_stats) if repository_stat["models"][i]["name"] == model]),
                } for model in models
            ]
        }
        agents_stats.append(agent_stats)

    with open("tmp/results/agent_stats.json", "w") as f:
        json.dump(agents_stats, f, indent=2)

def generate_coverage_report(repository_result):
    try:
        coverage_before = Cobertura(repository_result["initial_coverage_tool_output"])
    except Exception as e:
        logging.error(f"Error generating coverage report before: {e}\n{traceback.format_exc()}")
        coverage_before = None

    try:
        coverage_after = Cobertura(repository_result["final_coverage_tool_output"])
    except Exception as e:
        coverage_after = None

    if coverage_before and coverage_after:
        coverage_diff = CoberturaDiff(coverage_before, coverage_after)
    else:
        coverage_diff = None

    return {
        "coverage_before": coverage_before,
        "coverage_after": coverage_after,
        "coverage_diff": coverage_diff
    }


def setup_logging(_config):
    logging.basicConfig(level=logging.INFO)

def read_config(config_path):
    if not os.path.exists(config_path):
        logging.error(f"Config file not found: {config_path}")
        exit(1)

    with open(config_path, "r") as file:
        return yaml.safe_load(file)

if __name__ == "__main__":
    main()
