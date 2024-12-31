import os
import yaml
from typing import Dict, Any, Optional

class BenchmarkConfig:
    """Class for loading and validating benchmark configuration"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize with config dict"""
        self.templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.config = config
        self.validate_config()
        self.config = self.preprocess_config(config)

    def validate_config(self) -> None:
        """Validate the configuration"""
        if not self.config:
            raise ValueError("Config cannot be empty")
        
        # Validate required sections
        required_fields = {
            "agents": "Config must contain 'agents' section",
            "repositories": "Config must contain 'repositories' section",
            "runs": "Config must contain 'runs' field",
            "results_path": "Config must contain 'results_path' field"
        }
        
        for field, error_message in required_fields.items():
            if field not in self.config:
                raise ValueError(error_message)
        
        # Validate field types
        if not isinstance(self.config["runs"], int):
            raise ValueError("'runs' must be an integer")
        
        if not isinstance(self.config["results_path"], str):
            raise ValueError("'results_path' must be a string")
        
        # Validate non-empty lists
        if not self.config["agents"]:
            raise ValueError("'agents' section cannot be empty")
        
        if not self.config["repositories"]:
            raise ValueError("'repositories' section cannot be empty")

    def _load_template(self, template_type: str, name: str) -> Optional[Dict[str, Any]]:
        """Load a template configuration file"""
        template_path = os.path.join(self.templates_dir, template_type, f"{name}.yaml")
        if os.path.exists(template_path):
            with open(template_path, "r") as f:
                return yaml.safe_load(f)
        return None

    def preprocess_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get the processed configuration with templates loaded"""
        # Create copies of agents and repositories to avoid modifying them while iterating
        agents = []
        for agent_overrides in config["agents"]:
            agent = {}
            if "name" in agent_overrides:
                template = self._load_template("agents", agent_overrides["name"])
                if template:
                    agent = template
            agent.update(agent_overrides)
            agents.append(agent)
        
        repositories = []
        for repo_overrides in config["repositories"]:
            repo = {}
            
            # Load repository template if name is specified
            if "name" in repo_overrides:
                repo_template = self._load_template("repositories", repo_overrides["name"])
                if repo_template:
                    repo = repo_template

            repo.update(repo_overrides)

            # Load platform template if specified
            if "platform" in repo_overrides:
                platform_template = self._load_template("platforms", repo_overrides["platform"])
                if platform_template:
                    platform_template = platform_template.copy()
                    repo.update(platform_template)  # Platform template has lowest precedence

            # override again because platform template might have overridden some fields
            repo.update(repo_overrides)

            repositories.append(repo)
        
        # Update the config with the processed agents and repositories
        config["agents"] = agents
        config["repositories"] = repositories
        
        return config
