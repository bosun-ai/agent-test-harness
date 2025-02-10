from datasets import load_dataset
import os
import yaml
import subprocess
import json
import logging

from .agent_test_benchmark import AgentTestBenchmark
from .llm_proxy import LLMProxy
from .workspace_provider import WorkspaceProvider
from .swe_bench_types import SWEBenchItem
from .benchmark import Benchmark

def cleanup_processes():
    """Kill any existing LLM proxy and workspace provider processes."""
    try:
        # Find and kill amsterdam processes
        subprocess.run(["pkill", "-f", "amsterdam"], check=False)
        # Find and kill derrick processes
        subprocess.run(["pkill", "-f", "derrick"], check=False)
    except Exception as e:
        print(f"Warning: Error cleaning up processes: {e}")

def get_repository_template(repo: str, version: str) -> dict:
    """Get the repository template configuration for a given repo and version."""
    # Convert repo name to template format (e.g., "astropy/astropy" -> "swe-bench/astropy")
    repo_name = repo.split("/")[1]
    template_name = f"swe-bench/{repo_name}_{version}"
    
    templates_dir = os.path.join(os.path.dirname(__file__), "templates", "repositories")
    template_path = os.path.join(templates_dir, f"{template_name}.yaml")
    
    if not os.path.exists(template_path):
        raise ValueError(f"No template found for repository {repo} version {version} at {template_path}")
        
    with open(template_path, "r") as f:
        return yaml.safe_load(f)

def run_swe_bench():
    """Run a SWE-bench benchmark."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Clean up any existing processes
    cleanup_processes()
    
    # Load the dataset
    dataset = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
    logging.info(f"Total items in test split: {len(dataset)}\n")
    predictions = []

    all_repos = list(set([item["repo"] for item in dataset]))

    # Convert dataset to list and sort by instance_id
    dataset_list = list(dataset)
    dataset_list.sort(key=lambda x: x["instance_id"])

    # Get the first 10 items for each repo from the dataset
    raw_dataset_items = []
    for repo in all_repos:
        repo_items = [item for item in dataset_list if item["repo"] == repo]
        raw_dataset_items.extend(repo_items[:10])

    print(f"Total items for each repo: {len(raw_dataset_items)}\n")
    # Print all instance_ids
    print(f"Instance ids: {list(set([item['instance_id'] for item in raw_dataset_items]))}\n")

    # Get agent template
    agent_template_path = os.path.join(os.path.dirname(__file__), "templates", "agents", "kwaak.yaml")
    with open(agent_template_path, "r") as f:
        agent_template = yaml.safe_load(f)

    # Configure benchmark, output path should be current working directory, not relative to the current file
    benchmark_config = {
            "results_path": os.path.join(os.getcwd(), "results"),
            "runs": 1
    }

    logging.info(f"Results path: {benchmark_config['results_path']}")
    logging.info(f"Running benchmark with {benchmark_config['runs']} runs")

    dataset_items = []
    for item in raw_dataset_items[:10]:
        # Parse the JSON strings into lists
        item["FAIL_TO_PASS"] = json.loads(item["FAIL_TO_PASS"])
        item["PASS_TO_PASS"] = json.loads(item["PASS_TO_PASS"])

        item = SWEBenchItem(**item)
        dataset_items.append(item)


    benchmark = Benchmark("swe_bench", benchmark_config, [agent_template], dataset_items)

    # Initialize LLM proxy with default config
    config = {
        "llm_proxy": {
            "port": 8000,
            "host": "127.0.0.1",
            "api_key": os.environ.get("OPENAI_API_KEY"),
            "base_url": os.environ.get("OPENAI_API_BASE"),
            "model": "gpt-4"
        }
    }
    llm_proxy = LLMProxy(config)
    llm_proxy.run()

    while next_run := benchmark.next_run():
        item = next_run["instance"]
        run_name = next_run["run_name"]

        logging.info(f"Running benchmark {run_name} for {item.instance_id} from repository {item.repo} version {item.version} at commit {item.base_commit}")
        logging.info(f"Expected failing tests: {item.FAIL_TO_PASS}")
        logging.info(f"Expected passing tests: {item.PASS_TO_PASS}")
        
        # Get repository template
        repository = get_repository_template(item.repo, item.version)

        # Configure workspace provider
        repo_setup_script = repository.get("setup_script", "")
        agent_setup_script = agent_template.get("setup_script", "")
        setup_script = f"{repo_setup_script}\n\n# Agent setup script:\n\n{agent_setup_script}"

        workspace_provider = WorkspaceProvider(
            name=item.instance_id,
            repository=repository,
            setup_script=setup_script
        )
        workspace_provider.run()
        
        # Run the benchmark
        benchmark_result = AgentTestBenchmark(
            name=item.instance_id,
            llm_proxy=llm_proxy,
            workspace_provider=workspace_provider,
            agent=agent_template,
            repository=repository,
            swebench_item=item
        ).run()

        benchmark_result["instance_id"] = item.instance_id

        workspace_provider.stop()

        if "error" in benchmark_result:
            logging.error(f"Error running benchmark {run_name} for {item.instance_id}: {benchmark_result['error']}")

        benchmark.add_result(run_name, benchmark_result)


    for name, result in benchmark.results.items():
        if "error" in result:
            continue

        prediction = {
            "instance_id": result["instance_id"],
            "model_name_or_path": f"{agent_template['name']}-{agent_template['version']}",
            "model_patch": result['git_diff'],
            "run_name": name
        }

        predictions.append(prediction)

    with open("predictions.jsonl", "w") as f:
        for prediction in predictions:
            f.write(json.dumps(prediction) + "\n")

    with open("swe_bench_results.json", "w") as f:
        json.dump(benchmark.results, f)

if __name__ == "__main__":
    run_swe_bench()
