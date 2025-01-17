from datasets import load_dataset
import os
import yaml
import signal
import subprocess
import json
from typing import Optional

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
    """Download and run benchmark on first item from SWE-bench dataset."""
    # Clean up any existing processes
    cleanup_processes()
    
    dataset = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
    print(f"Total items in test split: {len(dataset)}\n")
    
    # Find first item from a requests-related repository
    requests_item = next(item for item in dataset if "requests" in item["repo"].lower())
    
    # Parse the JSON strings into lists
    requests_item["FAIL_TO_PASS"] = json.loads(requests_item["FAIL_TO_PASS"])
    requests_item["PASS_TO_PASS"] = json.loads(requests_item["PASS_TO_PASS"])
    
    first_item = SWEBenchItem(**requests_item)
    print(f"Running benchmark for {first_item.instance_id} from repository {first_item.repo} version {first_item.version}")
    
    # Get repository template
    repository = get_repository_template(first_item.repo, first_item.version)
    
    # Create dummy agent config (we'll implement the real agent later)
    agent = {
        "name": "swe-bench-agent",
        "command": "echo 'Agent would run here'",
        "setup_script": ""  # No setup needed for dummy agent
    }
    
    # Configure LLM proxy
    llm_proxy = LLMProxy({
        "endpoint": "http://localhost:8000",
        "admin_token": "test"
    })
    llm_proxy.run()

    # Configure workspace provider
    setup_script = repository.get("setup_script", "")

    workspace_provider = WorkspaceProvider(
        name=first_item.instance_id,
        repository=repository,
        setup_script=setup_script
    )
    workspace_provider.run()
    
    # Create and run benchmark
    benchmark = AgentTestBenchmark(
        name=first_item.instance_id,
        llm_proxy=llm_proxy,
        workspace_provider=workspace_provider,
        agent=agent,
        repository=repository,
        swebench_item=first_item
    )
    
    results = benchmark.run()
    print("\nBenchmark results:")
    print("-" * 40)
    for key, value in results.items():
        print(f"\n{key}:")
        if isinstance(value, str) and len(value) > 500:
            print(f"{value[:500]}...\n[truncated, total length: {len(value)} chars]")
        else:
            print(value)
        print("-" * 40)

if __name__ == "__main__":
    run_swe_bench()
