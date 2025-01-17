"""Functions for validating test output in SWE-bench tests."""

from dataclasses import dataclass
from typing import List


@dataclass
class TestResults:
    passed: List[str]
    failed: List[str]
    output: str


def parse_test_results(test_output: str) -> TestResults:
    """Parse test output to determine which tests passed and failed.
    
    Args:
        test_output: Raw output from the test run
        
    Returns:
        TestResults containing lists of passed and failed tests
    """
    passed = []
    failed = []
    
    for line in test_output.split('\n'):
        if line.startswith('PASSED '):
            test_name = line.replace('PASSED ', '').strip()
            passed.append(test_name)
        elif line.startswith('FAILED '):
            test_name = line.split(' - ')[0].replace('FAILED ', '').strip()
            failed.append(test_name)
            
    return TestResults(passed=passed, failed=failed, output=test_output)


def validate_test_results(test_results: TestResults, fail_to_pass: List[str], pass_to_pass: List[str]) -> bool:
    """Validate that test results match expected state.
    
    Args:
        test_results: TestResults from parse_test_results
        fail_to_pass: List of tests that should be failing
        pass_to_pass: List of tests that should be passing
        
    Returns:
        True if validation passes, False otherwise
    """
    for test in fail_to_pass:
        if test not in test_results.failed:
            print(f"Expected test {test} to be failing, but it was not in failed tests.")
            print(f"Failed tests were: {test_results.failed}")
            return False
            
    for test in pass_to_pass:
        if test not in test_results.passed:
            print(f"Expected test {test} to be passing, but it was not in passed tests.")
            print(f"Passed tests were: {test_results.passed}")
            return False
            
    return True
