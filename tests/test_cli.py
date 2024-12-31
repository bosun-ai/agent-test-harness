import pytest
import os
import tempfile
import yaml
import json
from unittest.mock import patch, MagicMock, mock_open

from agent_test_harness.cli import Cli

@pytest.fixture
def temp_config():
    """Create a temporary config file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config = {
            "agents": [
                {
                    "name": "test_agent",
                    "platform": "github"
                }
            ],
            "repositories": [
                {
                    "name": "test_repo",
                    "url": "test/repo"
                }
            ],
            "runs": 1,
            "results_path": "results"
        }
        yaml.dump(config, f)
        yield f.name
    os.unlink(f.name)

@pytest.fixture
def cli(temp_config):
    """Create a CLI instance with test arguments"""
    cli = Cli()
    with patch('argparse.ArgumentParser.parse_args') as mock_parse:
        mock_parse.return_value = MagicMock(
            config=temp_config,
            report_results=False,
            print_config=False,
            agent=None,
            repository=None
        )
        cli.parse_args()
    return cli

@pytest.fixture
def mock_config():
    return {
        "agents": [{"name": "test_agent"}],
        "repositories": [{"name": "test_repo"}],
        "runs": 1,
        "results_path": "results"
    }

def test_cli_initialize(cli, mock_config):
    """Test that CLI initialization loads config correctly"""
    with patch('builtins.open', mock_open(read_data=yaml.dump(mock_config))), \
         patch('os.path.exists', return_value=True):
        cli.initialize()
    
    assert cli.config is not None

def test_cli_print_config(cli, mock_config, capsys):
    """Test that --print-config outputs the configuration"""

    cli.read_config = MagicMock(return_value=mock_config)
    cli.args.print_config = True
    cli.initialize()
    cli.execute()
    
    captured = capsys.readouterr()
    assert json.loads(captured.out) == mock_config

def test_cli_missing_config():
    """Test that missing config file raises error"""
    cli = Cli()
    cli.args = MagicMock(config="nonexistent.yaml")
    
    with pytest.raises(FileNotFoundError):
        cli.initialize()

def test_cli_agent_repository_override(cli):
    """Test that --agent and --repository override the config"""
    cli.args = MagicMock(
        config="config.yaml",  # This file doesn't need to exist
        report_results=False,
        print_config=False,
        agent="override_agent",
        repository="override_repo"
    )
    
    base_config = {
        "agents": [{"name": "test_agent"}],
        "repositories": [{"name": "test_repo"}],
        "runs": 1,
        "results_path": "results"
    }
    
    with patch('builtins.open', mock_open(read_data=yaml.dump(base_config))), \
         patch('os.path.exists', return_value=True):
        cli.initialize()
    
    config = cli.benchmark_config.get_config()
    assert config["agents"][0]["name"] == "override_agent"
    assert config["repositories"][0]["name"] == "override_repo"

def test_cli_agent_repository_partial_override(cli):
    """Test that --agent and --repository can override specific items"""
    cli.args = MagicMock(
        config="config.yaml",
        report_results=False,
        print_config=False,
        agent="override_agent",
        repository=None
    )
    
    base_config = {
        "agents": [{"name": "test_agent"}],
        "repositories": [{"name": "test_repo"}],
        "runs": 1,
        "results_path": "results"
    }
    
    with patch('builtins.open', mock_open(read_data=yaml.dump(base_config))), \
         patch('os.path.exists', return_value=True):
        cli.initialize()
    
    config = cli.benchmark_config.get_config()
    assert config["agents"][0]["name"] == "override_agent"
    assert config["repositories"][0]["name"] == "test_repo"

@patch('agent_test_harness.cli.AgentTestHarness')
@patch('agent_test_harness.cli.report_results')
def test_cli_run_benchmark(mock_report, mock_harness, cli, mock_config):
    """Test that benchmark execution works correctly"""
    # Setup mock with proper results format
    mock_instance = mock_harness.return_value
    mock_instance.benchmark_agents.return_value = [{
        "agent_name": "test_agent",
        "repository": "test_repo",
        "result": "success",
        "run": "test_run"
    }]
    mock_report.return_value = {"stats": "test"}

    # Run benchmark
    with patch('builtins.open', mock_open(read_data=yaml.dump(mock_config))), \
         patch('os.path.exists', return_value=True), \
         patch('json.dump'):  # Mock json.dump to avoid file writes
        cli.initialize()
        cli.execute()
    
    # Verify that benchmark was run
    mock_instance.benchmark_agents.assert_called_once()
    mock_report.assert_not_called()  # report_results should not be called since args.report_results is False

@pytest.fixture
def cli():
    cli = Cli()
    cli.args = MagicMock(
        config="config.yaml",
        report_results=False,
        print_config=False,
        agent=None,
        repository=None
    )
    return cli

@patch('agent_test_harness.cli.AgentTestHarness')
@patch('agent_test_harness.cli.report_results')
def test_cli_run_benchmark(mock_report, mock_harness, cli, mock_config):
    """Test that benchmark execution works correctly"""
    # Setup mock with proper results format
    mock_instance = mock_harness.return_value
    mock_instance.benchmark_agents.return_value = [{
        "agent_name": "test_agent",
        "repository": "test_repo",
        "result": "success",
        "run": "test_run"
    }]
    mock_report.return_value = {"stats": "test"}

    # Run benchmark
    with patch('builtins.open', mock_open(read_data=yaml.dump(mock_config))), \
         patch('os.path.exists', return_value=True), \
         patch('json.dump'):  # Mock json.dump to avoid file writes
        cli.initialize()
        cli.execute()

    # Verify
    mock_instance.benchmark_agents.assert_called_once()
    mock_report.assert_called_once()

def test_cli_missing_config():
    """Test that CLI handles missing config file correctly"""
    cli = Cli()
    cli.args = MagicMock(
        config="nonexistent.yaml",
        report_results=False,
        print_config=False,
        agent=None,
        repository=None
    )
    
    with pytest.raises(SystemExit):
        cli.initialize()

def test_cli_agent_repository_override(cli):
    """Test that --agent and --repository override the config"""
    cli.args = MagicMock(
        config="config.yaml",  # This file doesn't need to exist
        report_results=False,
        print_config=False,
        agent="override_agent",
        repository="override_repo"
    )
    
    cli.initialize()
    
    # Verify config was overridden
    assert len(cli.config["agents"]) == 1
    assert cli.config["agents"][0]["name"] == "override_agent"
    assert len(cli.config["repositories"]) == 1
    assert cli.config["repositories"][0]["name"] == "override_repo"

def test_cli_agent_repository_partial_override():
    """Test that providing only one of --agent or --repository fails"""
    cli = Cli()
    cli.args = MagicMock(
        config="config.yaml",
        report_results=False,
        print_config=False,
        agent="override_agent",
        repository=None
    )
    
    with pytest.raises(SystemExit):
        cli.initialize()
