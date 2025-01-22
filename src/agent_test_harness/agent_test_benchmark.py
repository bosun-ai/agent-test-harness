import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Union

from .llm_proxy import LLMProxy
from .workspace_provider import WorkspaceProvider
from .swe_bench_types import SWEBenchItem
from .test_validation import parse_test_results, validate_test_results

@dataclass
class TestResult:
    output: str
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    
    def failed(self) -> bool:
        """Return True if the test run failed entirely (not just individual tests failing)"""
        # If we can parse the test output, then the test run itself succeeded
        # even if individual tests failed
        try:
            parse_test_results(self.output)
            return False
        except Exception as e:
            return True

class AgentTestBenchmark:
    run_name: str
    llm_proxy: LLMProxy
    agent: dict
    repository: dict
    workspace_provider: WorkspaceProvider
    project: dict
    workspace: dict
    results: dict
    initial_git_ref: str
    name: str
    repository_name: str
    swebench_item: Optional[SWEBenchItem]
    files: Optional[list]

    def __init__(self, name: str, llm_proxy: LLMProxy, workspace_provider: WorkspaceProvider, 
                agent: dict, repository: dict, swebench_item: Optional[SWEBenchItem] = None):
        self.llm_proxy = llm_proxy
        self.workspace_provider = workspace_provider
        self.agent = agent
        self.repository = repository
        self.project = None
        self.workspace = None
        self.initial_git_ref = None
        self.results = {}
        self.repository_name = self.repository["name"]
        self.repository_path = "/" + self.repository_name
        self.name = name
        self.swebench_item = swebench_item
        # Only set files if not in SWE-bench mode
        self.files = None if swebench_item else self.repository["files"]

    def environment_variables(self):
        env = {
            "OPENAI_API_BASE": self.llm_proxy.endpoint,
            "OPENAI_API_KEY": self.project['token'],
            "REPOSITORY_URL": self.repository["url"],
            "PROJECT_ROOT": self.repository_path,
            "TEST_COMMAND": self.repository["test_command"],
        }
        
        if "coverage_report_path" in self.repository:
            env["COVERAGE_REPORT_PATH"] = self.repository["coverage_report_path"]
            
        if self.swebench_item:
            env["COMMIT_SHA"] = self.swebench_item.base_commit
            
        return env

    def run(self):
        logging.info("Provisioning LLM proxy...")
        self.provision_llm_proxy()
        logging.info("Provisioning workspace...")
        self.provision_workspace()
        logging.info("Establishing initial git ref...")
        self.establish_initial_git_ref()
        
        if self.swebench_item:
            logging.info(f"\nRunning SWE-bench item:")
            logging.info(f"Repository: {self.swebench_item.repo}")
            logging.info(f"Version: {self.swebench_item.version}")
            logging.info(f"Base commit: {self.swebench_item.base_commit}")
            logging.info(f"Instance ID: {self.swebench_item.instance_id}")
            return self._run_swebench()
        else:
            return self._run_original()

    def _run_swebench(self):
        """Run the benchmark in SWE-bench mode."""
        logging.info("Running SWE-bench validation...")
        test_result = self.run_test_coverage()
        
        # Parse test results regardless of whether the run failed
        test_results = parse_test_results(test_result.output)
        logging.info("\nTest Results:")
        logging.info(f"Passed tests: {test_results.passed}")
        logging.info(f"Failed tests: {test_results.failed}")
            
        # Apply the test patch before running the agent
        logging.info("Applying test patch...")
        self.write_file("/tmp/test.patch", self.swebench_item.test_patch.encode("utf-8"))
        
        result = self.run_command_in_workdir("git apply /tmp/test.patch")
        if result.failed():
            logging.error(f"Failed to apply test patch: {result.output}")
            self.results["validation_failed"] = True
            self.results["validation_output"] = result.output
            return self.results

        
        # Only validate that expected passing tests are passing in pre-agent state
        validation_passed = all(test in test_results.passed for test in self.swebench_item.PASS_TO_PASS)
        if not validation_passed:
            missing_passing = [test for test in self.swebench_item.PASS_TO_PASS if test not in test_results.passed]
            logging.error(f"SWE-bench validation failed - these tests should be passing but aren't: {missing_passing}")
            self.results["validation_failed"] = True
            self.results["validation_output"] = test_result.output
            return self.results

        test_result = self.run_test_coverage()

        # Validate that there is at least one failing test that's included in FAIL_TO_PASS
        validation_passed = any(test in test_results.failed for test in self.swebench_item.FAIL_TO_PASS)
        if not validation_passed:
            logging.error(f"SWE-bench validation failed - expected:[[{test_results.failed}]] to include one of: [[{self.swebench_item.FAIL_TO_PASS}]]")
            self.results["validation_failed"] = True
            self.results["validation_output"] = test_result.output
            return self.results
        
        # Now run the agent
        logging.info("Running agent...")
        start_time = time.time()
        env = self.environment_variables()
        
        this_env = {
            **env,
            "PROMPT": (
                "A user has reported the following issue:\n\n"
                f"<issue>\n{self.swebench_item.problem_statement}\n</issue>\n\n"
                "Could you solve the issue? I have added a failing test case for it. Using the following patch:\n\n"
                f"<patch>\n{self.swebench_item.patch}\n</patch>\n\n"
                "Please make sure that your solution makes the test(s) in this patch pass, "
                "and does not introduce any new failing tests. "
                "You can ignore tests that were already failing that are not related to the tests in this patch."
                "Do not modify the tests in this patch nor any other tests in the repository, only fix the issue."
            )
        }
        result = self.run_command_in_workdir(self.agent["command"], this_env)
        self.results["agent_output"] = result.output

        # Check if the fix worked
        test_result = self.run_test_coverage()
        if not test_result.failed():
            test_results = parse_test_results(test_result.output)
            logging.info("\nPost-agent test results:")
            logging.info(f"Passed tests: {test_results.passed}")
            logging.info(f"Failed tests: {test_results.failed}")
            
            # Check that all PASS_TO_PASS tests are still passing
            pass_to_pass_ok = all(test in test_results.passed for test in self.swebench_item.PASS_TO_PASS)
            if not pass_to_pass_ok:
                missing_passing = [test for test in self.swebench_item.PASS_TO_PASS if test not in test_results.passed]
                logging.error(f"Regression: these tests should be passing but aren't: {missing_passing}")
                return self.results
            
            # Check that none of the FAIL_TO_PASS tests are failing
            fail_to_pass_ok = not any(test in test_results.failed for test in self.swebench_item.FAIL_TO_PASS)
            if not fail_to_pass_ok:
                still_failing = [test for test in self.swebench_item.FAIL_TO_PASS if test in test_results.failed]
                logging.error(f"Fix incomplete: these tests are still failing: {still_failing}")
                return self.results
            
            logging.info("SWE-bench success - validation passed")
            self.results["swebench_success"] = True

        end_time = time.time()
        self.results["agent_execution_time"] = end_time - start_time
        logging.info("Running git diff...")
        self.results["git_diff"] = self.run_git_diff()
        logging.info("Getting LLM metrics...")
        self.results["llm_metrics"] = self.get_llm_metrics()

        return self.results

    def _run_original(self):
        """Run the benchmark in original mode."""
        logging.info("Running coverage tool...")
        self.results["initial_coverage_tool_output"] = self.get_test_coverage()

        logging.info("Running agent...")
        start_time = time.time()
        env = self.environment_variables()
        log = ""

        for file, test_file in self.files:
            log += f"Running agent on file {file}\n"
            this_env = {
                **env,
                "PROMPT": f"Write unit tests for {file} until it has 100% coverage, make sure to add the files to {test_file}. Do not modify the original code, only add tests. Do not modify other files than {test_file} or test helper files. If you believe that a piece of code can not be tested without modifying it (for example to inject a dependency), skip it. If you added a test that you can't get to pass, remove it before stopping. This is not an interactive chat, so don't ask for extra information or any action from a user. Either use the tools or clean up failing tests and stop."
            }
            result = self.run_command_in_workdir(self.agent["command"], this_env)
            log += result.output

            logging.info("Running tests again...")
            test_result = self.run_test_coverage()
            coverage_result = self.read_test_coverage()
            
            if coverage_result.succeeded():
                self.results["final_coverage_tool_output"] = coverage_result.output

            if test_result.failed():
                logging.info("Test command failed. Stopping benchmark...")
                break

        self.results["agent_output"] = log
        end_time = time.time()
        self.results["agent_execution_time"] = end_time - start_time
        logging.info("Running git diff...")
        self.results["git_diff"] = self.run_git_diff()
        logging.info("Getting LLM metrics...")
        self.results["llm_metrics"] = self.get_llm_metrics()

        return self.results

    def run_command_in_workdir(self, command: str, env=None):
        if env is None:
            env = self.environment_variables()
        else:
            # merge the environment variables
            env = {**self.environment_variables(), **env}
        return self.workspace_provider.run_command_with_output(self.workspace["id"], f"cd {self.repository_path} && {command}", env)

    def write_file(self, path: str, content: bytes):
        return self.workspace_provider.write_file(self.workspace["id"], path, content)

    def provision_llm_proxy(self):
        self.project = self.llm_proxy.create_project(self.name)

    def get_llm_metrics(self):
        return self.llm_proxy.get_metrics(self.project["token"])

    def provision_workspace(self):
        self.workspace = self.workspace_provider.create_workspace(env=self.environment_variables())

    def establish_initial_git_ref(self):
        commit_context = "git config user.name 'agent-test-harness'; git config user.email 'agent-test-harness@example.com';"
        output = self.run_command_in_workdir(f"{commit_context} git commit -a -m \"benchmark-head\" 1>/dev/null; git rev-parse HEAD")
        if output.failed():
            raise Exception(f"Failed to establish initial git ref: {output.output}")
        self.initial_git_ref = output.output.strip()

    def run_test_coverage(self):
        return self.run_command_in_workdir(self.repository["test_command"])

    def read_test_coverage(self):
        return self.run_command_in_workdir(f'cat {self.repository["coverage_report_path"]}')

    def get_test_coverage(self):
        test_run = self.run_test_coverage()
        if test_run.failed():
            raise Exception(f"Test command failed: {test_run.output}")
            
        coverage_output = self.read_test_coverage()
        if coverage_output.failed():
            raise Exception(f"Failed to read coverage report: {coverage_output.output}")
        return coverage_output.output

    def run_git_diff(self):
        result = self.run_command_in_workdir(f"git diff {self.initial_git_ref}")
        if result.failed():
            raise Exception(f"Git diff failed: {result.output}")
        return result.output
