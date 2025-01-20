"""Tests for test validation functions."""

import pytest
import json
from datasets import load_dataset
from agent_test_harness.test_validation import parse_test_results, validate_test_results, TestResults
from agent_test_harness.swe_bench_types import SWEBenchItem


def test_parse_test_results():
    """Test parsing of test output."""
    with open('test_output.txt', 'r') as f:
        test_output = f.read()
        
    results = parse_test_results(test_output)
    
    # Check some known passing tests
    assert 'test_requests.py::RequestsTestCase::test_basic_building' in results.passed
    assert 'test_requests.py::RequestsTestCase::test_cannot_send_unprepared_requests' in results.passed
    assert 'test_requests.py::RequestsTestCase::test_cookie_parameters' in results.passed
    
    # Check some known failing tests
    assert 'test_requests.py::RequestsTestCase::test_BASICAUTH_TUPLE_HTTP_200_OK_GET' in results.failed
    assert 'test_requests.py::RequestsTestCase::test_DIGESTAUTH_WRONG_HTTP_401_GET' in results.failed
    assert 'test_requests.py::RequestsTestCase::test_DIGEST_HTTP_200_OK_GET' in results.failed


def test_validate_test_results():
    """Test validation of test results."""
    results = TestResults(
        passed=['test_a', 'test_b', 'test_c'],
        failed=['test_d', 'test_e', 'test_f'],
        output='dummy output'
    )
    
    # All tests match expected state
    assert validate_test_results(
        results,
        fail_to_pass=['test_d', 'test_e'],
        pass_to_pass=['test_a', 'test_b']
    )
    
    # Some failing tests missing
    assert not validate_test_results(
        results,
        fail_to_pass=['test_d', 'test_x'],  # test_x should fail but doesn't exist
        pass_to_pass=['test_a', 'test_b']
    )
    
    # Some passing tests missing
    assert not validate_test_results(
        results,
        fail_to_pass=['test_d', 'test_e'],
        pass_to_pass=['test_a', 'test_x']  # test_x should pass but doesn't exist
    )


def test_validate_swebench_item():
    """Test validation using actual SWE-bench dataset item."""
    # Load the dataset and find the requests item
    dataset = load_dataset('princeton-nlp/SWE-bench_Lite', split='test')
    requests_item = next(item for item in dataset if "requests" in item["repo"].lower())
    
    print("\nDataset item properties:")
    for key, value in requests_item.items():
        print(f"{key}: {value}")
    
    # Parse the JSON strings into lists
    requests_item["FAIL_TO_PASS"] = json.loads(requests_item["FAIL_TO_PASS"])
    requests_item["PASS_TO_PASS"] = json.loads(requests_item["PASS_TO_PASS"])
    
    item = SWEBenchItem(**requests_item)
    
    print("\nSWE-bench item properties:")
    print(f"FAIL_TO_PASS: {item.FAIL_TO_PASS}")
    print(f"PASS_TO_PASS: {item.PASS_TO_PASS}")
    
    # Load and parse the test output
    with open('test_output.txt', 'r') as f:
        test_output = f.read()
    test_results = parse_test_results(test_output)
    
    print("\nParsed test results:")
    print(f"Passed tests: {test_results.passed}")
    print(f"Failed tests: {test_results.failed}")
    
    # Validate against the item's expected test states
    validation_passed = validate_test_results(
        test_results,
        fail_to_pass=item.FAIL_TO_PASS,
        pass_to_pass=item.PASS_TO_PASS
    )
    
    # The validation should fail since this is the pre-fix state
    assert not validation_passed, "Validation should fail since tests are in pre-fix state"
    
    # Verify specific test states
    for test in item.FAIL_TO_PASS:
        assert test in test_results.failed, f"Test {test} should be failing"
    for test in item.PASS_TO_PASS:
        assert test in test_results.passed, f"Test {test} should be passing"
