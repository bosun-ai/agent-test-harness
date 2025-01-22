from datasets import load_dataset
import os
import yaml
import signal
import subprocess
import json
from typing import Optional
import logging

from .agent_test_benchmark import AgentTestBenchmark
from .llm_proxy import LLMProxy
from .workspace_provider import WorkspaceProvider
from .swe_bench_types import SWEBenchItem

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
    dataset = load_dataset('princeton-nlp/SWE-bench_Lite', split='test')
    logging.info(f"Total items in test split: {len(dataset)}\n")
    
    # Find nth item from a requests-related repository
    n = 2
    repo_name = "requests"
    items = [item for item in dataset if repo_name in item["repo"].lower()]
    requests_item = items[n-1]
    # Parse the JSON strings into lists
    requests_item["FAIL_TO_PASS"] = json.loads(requests_item["FAIL_TO_PASS"])
    requests_item["PASS_TO_PASS"] = json.loads(requests_item["PASS_TO_PASS"])
    
    first_item = SWEBenchItem(**requests_item)
    logging.info(f"Running benchmark for {first_item.instance_id} from repository {first_item.repo} version {first_item.version} at commit {first_item.base_commit}")
    logging.info(f"Expected failing tests: {first_item.FAIL_TO_PASS}")
    logging.info(f"Expected passing tests: {first_item.PASS_TO_PASS}")
    
    # Get repository template
    repository = get_repository_template(first_item.repo, first_item.version)
    
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
    
    # Get agent template
    agent_template_path = os.path.join(os.path.dirname(__file__), "templates", "agents", "kwaak.yaml")
    with open(agent_template_path, "r") as f:
        agent_template = yaml.safe_load(f)

    # Configure workspace provider
    repo_setup_script = repository.get("setup_script", "")
    agent_setup_script = agent_template.get("setup_script", "")
    setup_script = f"{repo_setup_script}\n\n# Agent setup script:\n\n{agent_setup_script}"

    workspace_provider = WorkspaceProvider(
        name=first_item.instance_id,
        repository=repository,
        setup_script=setup_script
    )
    workspace_provider.run()
    
    # Run the benchmark
    benchmark = AgentTestBenchmark(
        name=first_item.instance_id,
        llm_proxy=llm_proxy,
        workspace_provider=workspace_provider,
        agent=agent_template,
        repository=repository,
        swebench_item=first_item
    )
    
    results = benchmark.run()
    logging.info("\nBenchmark results:")
    logging.info("-" * 40)
    for key, value in results.items():
        logging.info(f"\n{key}:")
        if isinstance(value, str) and len(value) > 500:
            logging.info(f"{value[:500]}...\n[truncated, total length: {len(value)} chars]")
        else:
            logging.info(value)
        logging.info("-" * 40)

if __name__ == "__main__":
    run_swe_bench()
