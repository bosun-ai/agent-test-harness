#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import yaml
import xml.etree.ElementTree as ET
from pathlib import Path
from .benchmark_config import BenchmarkConfig

def load_repository_config(repo_name: str, platform_name: str = None) -> dict:
    """Load the repository configuration using BenchmarkConfig."""
    config = {
        "agents": [{
            "name": "dummy",  # Add dummy agent to satisfy validation
            "type": "dummy"
        }],
        "repositories": [{
            "name": repo_name
        }],
        "runs": 1,
        "results_path": "dummy"  # Not used in this context
    }
    
    if platform_name:
        config["repositories"][0]["platform"] = platform_name
    
    benchmark_config = BenchmarkConfig(config)
    return benchmark_config.config["repositories"][0]

def run_docker_command(command: str, check: bool = True, print_output: bool = False) -> subprocess.CompletedProcess:
    """Run a docker command and optionally check its return code."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if print_output or result.returncode != 0:
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
    
    if check and result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(1)
    return result

def verify_repository_setup(container_id: str) -> bool:
    """Verify that the repository is properly set up."""
    # Check if repository was cloned
    result = run_docker_command(
        f"docker exec {container_id} test -d /repo/.git",
        check=False
    )
    if result.returncode != 0:
        print("Repository was not properly cloned")
        return False
    return True

def verify_coverage_report(container_id: str, coverage_path: str) -> bool:
    """Verify that the coverage report exists and is valid XML."""
    # First check if the file exists in the container
    result = run_docker_command(
        f"docker exec {container_id} test -f {coverage_path}",
        check=False
    )
    if result.returncode != 0:
        print(f"Coverage report not found at {coverage_path}")
        return False

    # Copy coverage report from container to host
    temp_path = "/tmp/coverage.xml"
    copy_cmd = f"docker cp {container_id}:{coverage_path} {temp_path}"
    result = run_docker_command(copy_cmd, check=False)
    if result.returncode != 0:
        print(f"Failed to copy coverage report from {coverage_path}")
        return False

    # Verify it's valid XML
    try:
        tree = ET.parse(temp_path)
        root = tree.getroot()
        if root.tag != 'coverage':
            print("Invalid coverage report: root element is not 'coverage'")
            return False
        
        # Even if there are no tests, we should have a valid coverage report
        print("Coverage report structure is valid")
        return True
    except ET.ParseError as e:
        print(f"Invalid XML in coverage report: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)

def main():
    parser = argparse.ArgumentParser(description='Test a repository template')
    parser.add_argument('repository', help='Name of the repository template to test')
    parser.add_argument('--debug', action='store_true', help='Print debug output')
    args = parser.parse_args()

    # Load repository config
    repo_config = load_repository_config(args.repository)

    # Start container
    container_name = f"test-{args.repository}"
    run_docker_command(f"docker rm -f {container_name}", check=False)  # Clean up any existing container
    run_docker_command(
        f"docker run -d --name {container_name} bosunai/build-baseimage sleep infinity"
    )

    failed = True

    try:
        # Clone repository
        run_docker_command(
            f"docker exec {container_name} bash -c '"
            f"git clone {repo_config['url']} /repo'"
        )

        # Verify repository setup
        if not verify_repository_setup(container_name):
            print("Repository setup verification failed")
            sys.exit(1)

        # Debug: List files before setup
        if args.debug:
            run_docker_command(
                f"docker exec {container_name} find /repo -name '*.py' -not -path '*/venv/*'",
                print_output=True
            )

        # Run setup script
        setup_script = repo_config['setup_script'].replace('$PROJECT_ROOT', '/repo')
        run_docker_command(
            f"docker exec {container_name} bash -c '{setup_script}'",
            print_output=args.debug
        )

        # Debug: List files after setup
        if args.debug:
            run_docker_command(
                f"docker exec {container_name} find /repo -name '*.py' -not -path '*/venv/*'",
                print_output=True
            )

        # Run test command
        test_command = repo_config['test_command'].replace('$PROJECT_ROOT', '/repo')
        run_docker_command(
            f"docker exec -w /repo {container_name} bash -c '{test_command}'",
            print_output=True  # Always show test output
        )

        # Debug: Show test command output
        if args.debug:
            run_docker_command(
                f"docker exec {container_name} cat /tmp/repo-setup.log",
                check=False,
                print_output=True
            )

        # Verify coverage report
        if not verify_coverage_report(container_name, repo_config['coverage_report_path'].replace('$PROJECT_ROOT', '/repo')):
            print("Coverage report verification failed")
            sys.exit(1)

        print(f"Repository {args.repository} tested successfully!")
        failed = False
    finally:
        if failed:
            input("Test failed, going to remove container. Press Enter to continue...")
        # Cleanup
        run_docker_command(f"docker rm -f {container_name}")

if __name__ == '__main__':
    main()
