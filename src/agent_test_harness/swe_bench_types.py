from dataclasses import dataclass

@dataclass
class SWEBenchItem:
    repo: str
    instance_id: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    version: str
    FAIL_TO_PASS: list[str]
    PASS_TO_PASS: list[str]
    environment_setup_commit: str
