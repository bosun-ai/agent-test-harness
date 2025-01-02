import pytest
import yaml
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock, mock_open

from agent_test_harness.benchmark_config import BenchmarkConfig

@pytest.fixture
def base_config():
    return {
        "agents": [{"name": "test_agent"}],
        "repositories": [{"name": "test_repo"}],
        "runs": 1,
        "results_path": "results"
    }

def test_load_config():
    """Test loading a basic configuration"""
    config = {
        "agents": [{"name": "test_agent"}],
        "repositories": [{"name": "test_repo"}],
        "runs": 1,
        "results_path": "results"
    }
    
    benchmark_config = BenchmarkConfig(config)
    assert benchmark_config.config == config

def test_merge_config():
    """Test merging configurations"""
    config = {
        "agents": [{
            "name": "test_agent",
            "config_key": "config_value"
        }],
        "repositories": [{
            "name": "test_repo",
            "config_key": "config_value"
        }],
        "runs": 1,
        "results_path": "results"
    }
    
    template = {
        "template_key": "template_value"
    }
    
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=yaml.dump(template))):
        benchmark_config = BenchmarkConfig(config)
        final_config = benchmark_config.config
    
    assert final_config["agents"][0]["template_key"] == "template_value"
    assert final_config["agents"][0]["config_key"] == "config_value"

def test_agent_config_with_template():
    """Test loading agent configuration with template"""
    config = {
        "agents": [{
            "name": "test_agent",
            "config_key": "config_value"
        }],
        "repositories": [{"name": "test_repo"}],
        "runs": 1,
        "results_path": "results"
    }
    
    template = {
        "template_key": "template_value"
    }
    
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=yaml.dump(template))):
        benchmark_config = BenchmarkConfig(config)
        final_config = benchmark_config.config
    
    assert final_config["agents"][0]["template_key"] == "template_value"
    assert final_config["agents"][0]["config_key"] == "config_value"

def test_repository_config_with_template():
    """Test loading repository configuration with template"""
    config = {
        "agents": [{"name": "test_agent"}],
        "repositories": [{
            "name": "test_repo",
            "platform": "test_platform",
            "config_key": "config_value"
        }],
        "runs": 1,
        "results_path": "results"
    }
    
    template = {
        "template_key": "template_value"
    }
    
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=yaml.dump(template))):
        benchmark_config = BenchmarkConfig(config)
        final_config = benchmark_config.config
    
    assert final_config["repositories"][0]["template_key"] == "template_value"
    assert final_config["repositories"][0]["config_key"] == "config_value"

def test_repository_config_with_platform():
    """Test loading repository configuration with platform template"""
    config = {
        "agents": [{"name": "test_agent"}],
        "repositories": [{
            "name": "test_repo",
            "platform": "test_platform",
            "config_key": "config_value"
        }],
        "runs": 1,
        "results_path": "results"
    }
    
    platform_template = {
        "platform_key": "platform_value",
    }
    
    repo_template = {
        "repo_key": "repo_value"
    }
    
    def mock_open_side_effect(*args, **kwargs):
        path = args[0] if args else kwargs.get('file')
        if 'platforms' in str(path):
            return mock_open(read_data=yaml.dump(platform_template))()
        elif 'repositories' in str(path):
            return mock_open(read_data=yaml.dump(repo_template))()
        return mock_open()()
    
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', side_effect=mock_open_side_effect):
        benchmark_config = BenchmarkConfig(config)
        final_config = benchmark_config.config
    
    assert final_config["repositories"][0]["platform_key"] == "platform_value"
    assert final_config["repositories"][0]["repo_key"] == "repo_value"
    assert final_config["repositories"][0]["config_key"] == "config_value"

def test_repository_config_platform_and_template():
    """Test loading repository configuration with platform and template"""
    config = {
        "agents": [{"name": "test_agent"}],
        "repositories": [{
            "name": "test_repo",
            "config_key": "config_value"
        }],
        "runs": 1,
        "results_path": "results"
    }
    
    platform_template = {
        "platform_key": "platform_value"
    }
    
    repo_template = {
        "platform": "test_platform",
        "repo_key": "repo_value"
    }

    def load_template_side_effect(template_type: str, name: str) -> Optional[Dict[str, Any]]:
        if template_type == "platforms" and name == "test_platform":
            return platform_template
        elif template_type == "repositories" and name == "test_repo":
            return repo_template
        elif template_type == "agents" and name == "test_agent":
            return {}
        raise ValueError(f"Template not found: {template_type}/{name}")
    
    with patch('agent_test_harness.benchmark_config.BenchmarkConfig._load_template', side_effect=load_template_side_effect):
        benchmark_config = BenchmarkConfig(config)
        final_config = benchmark_config.config
    
        assert final_config["repositories"][0]["repo_key"] == "repo_value"
        assert final_config["repositories"][0]["config_key"] == "config_value"
        assert final_config["repositories"][0]["platform_key"] == "platform_value"

def test_repository_config_platform_only():
    """Test loading repository configuration with only platform template"""
    config = {
        "agents": [{"name": "test_agent"}],
        "repositories": [{
            "platform": "test_platform",
            "config_key": "config_value"
        }],
        "runs": 1,
        "results_path": "results"
    }
    
    platform_template = {
        "platform_key": "platform_value"
    }
    
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=yaml.dump(platform_template))):
        benchmark_config = BenchmarkConfig(config)
        final_config = benchmark_config.config
    
    assert final_config["repositories"][0]["platform_key"] == "platform_value"
    assert final_config["repositories"][0]["config_key"] == "config_value"

def test_config_validation():
    """Test configuration validation"""
    # Test missing required fields
    with pytest.raises(ValueError, match="Config must contain 'agents' section"):
        BenchmarkConfig({"repositories": [], "runs": 1, "results_path": "results"})
    
    with pytest.raises(ValueError, match="Config must contain 'repositories' section"):
        BenchmarkConfig({"agents": [], "runs": 1, "results_path": "results"})
    
    with pytest.raises(ValueError, match="Config must contain 'runs' field"):
        BenchmarkConfig({"agents": [], "repositories": [], "results_path": "results"})
    
    with pytest.raises(ValueError, match="Config must contain 'results_path' field"):
        BenchmarkConfig({"agents": [], "repositories": [], "runs": 1})
    
    # Test invalid field types
    with pytest.raises(ValueError, match="'runs' must be an integer"):
        BenchmarkConfig({
            "agents": [{"name": "test"}],
            "repositories": [{"name": "test"}],
            "runs": "1",
            "results_path": "results"
        })
    
    with pytest.raises(ValueError, match="'results_path' must be a string"):
        BenchmarkConfig({
            "agents": [{"name": "test"}],
            "repositories": [{"name": "test"}],
            "runs": 1,
            "results_path": 123
        })
    
    # Test empty lists
    with pytest.raises(ValueError, match="'agents' section cannot be empty"):
        BenchmarkConfig({
            "agents": [],
            "repositories": [{"name": "test"}],
            "runs": 1,
            "results_path": "results"
        })
    
    with pytest.raises(ValueError, match="'repositories' section cannot be empty"):
        BenchmarkConfig({
            "agents": [{"name": "test"}],
            "repositories": [],
            "runs": 1,
            "results_path": "results"
        })
