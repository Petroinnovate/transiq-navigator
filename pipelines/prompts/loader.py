"""
Prompt Loader - Dynamic loading of versioned prompts with caching and A/B testing
"""
import os
import yaml
import random
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from functools import lru_cache
from core.logging.logger import get_logger

logger = get_logger(__name__)


class PromptVersion:
    """Represents a single versioned prompt"""
    
    def __init__(self, data: Dict[str, Any], file_path: Path):
        self.version = data.get("version", "unknown")
        self.name = data.get("name", "unknown")
        self.description = data.get("description", "")
        self.created_at = data.get("created_at", "")
        self.template = data.get("template", "")
        self.metadata = data.get("metadata", {})
        self.file_path = file_path
        self.stable = data.get("stable", False)
        self.fallback_version = data.get("fallback_version", None)
        
    def render(self, **kwargs) -> str:
        """Render template with provided variables"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing variable in prompt template: {e}")
            raise ValueError(f"Prompt template requires variable: {e}")
    
    def __repr__(self):
        return f"PromptVersion(name={self.name}, version={self.version}, stable={self.stable})"


class PromptLoader:
    """
    Prompt versioning system with caching, A/B testing, and fallback support
    
    Features:
    - Load prompts from YAML files (app/prompts/{name}/{version}.yaml)
    - Automatic version selection (latest, stable, specific)
    - A/B testing with random version selection
    - LRU caching for performance
    - Fallback mechanism for failed prompts
    """
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize prompt loader
        
        Args:
            prompts_dir: Directory containing prompt files (defaults to app/prompts)
        """
        if prompts_dir is None:
            # Auto-detect prompts directory
            current_file = Path(__file__).resolve()
            self.prompts_dir = current_file.parent
        else:
            self.prompts_dir = Path(prompts_dir)
        
        logger.info(f"PromptLoader initialized with directory: {self.prompts_dir}")
        
        # Cache for loaded prompt versions
        self._cache: Dict[Tuple[str, str], PromptVersion] = {}
        
        # A/B testing configuration
        self._ab_tests: Dict[str, List[str]] = {}
    
    def register_ab_test(self, prompt_name: str, versions: List[str], weights: Optional[List[float]] = None):
        """
        Register A/B test for a prompt
        
        Args:
            prompt_name: Name of the prompt
            versions: List of version strings to test (e.g., ["1.0.0", "1.1.0"])
            weights: Optional weights for each version (must sum to 1.0)
        
        Example:
            loader.register_ab_test("dashboard", ["1.0.0", "1.1.0"], weights=[0.5, 0.5])
        """
        if weights and sum(weights) != 1.0:
            raise ValueError("Weights must sum to 1.0")
        
        self._ab_tests[prompt_name] = {
            "versions": versions,
            "weights": weights or [1.0 / len(versions)] * len(versions)
        }
        logger.info(f"Registered A/B test for '{prompt_name}': {versions}")
    
    def get_ab_version(self, prompt_name: str) -> Optional[str]:
        """
        Get version for A/B testing (random selection based on weights)
        
        Args:
            prompt_name: Name of the prompt
            
        Returns:
            Selected version string, or None if no A/B test configured
        """
        if prompt_name not in self._ab_tests:
            return None
        
        test_config = self._ab_tests[prompt_name]
        selected_version = random.choices(
            test_config["versions"],
            weights=test_config["weights"]
        )[0]
        
        logger.debug(f"A/B test selected version '{selected_version}' for '{prompt_name}'")
        return selected_version
    
    def list_versions(self, prompt_name: str) -> List[str]:
        """
        List all available versions for a prompt
        
        Args:
            prompt_name: Name of the prompt
            
        Returns:
            List of version strings (sorted newest first)
        """
        prompt_dir = self.prompts_dir / prompt_name
        
        if not prompt_dir.exists():
            logger.warning(f"Prompt directory not found: {prompt_dir}")
            return []
        
        versions = []
        for file_path in prompt_dir.glob("*.yaml"):
            # Extract version from filename (e.g., "1.0.0.yaml" -> "1.0.0")
            version = file_path.stem
            versions.append(version)
        
        # Sort by semantic version (newest first)
        versions.sort(key=lambda v: self._parse_version(v), reverse=True)
        return versions
    
    def get_latest_version(self, prompt_name: str) -> Optional[str]:
        """
        Get the latest version number for a prompt
        
        Args:
            prompt_name: Name of the prompt
            
        Returns:
            Latest version string, or None if no versions found
        """
        versions = self.list_versions(prompt_name)
        return versions[0] if versions else None
    
    def get_stable_version(self, prompt_name: str) -> Optional[str]:
        """
        Get the latest stable version for a prompt
        
        Args:
            prompt_name: Name of the prompt
            
        Returns:
            Latest stable version string, or None if no stable versions found
        """
        versions = self.list_versions(prompt_name)
        
        for version in versions:
            prompt_version = self._load_prompt_file(prompt_name, version)
            if prompt_version and prompt_version.stable:
                logger.debug(f"Found stable version '{version}' for '{prompt_name}'")
                return version
        
        logger.warning(f"No stable version found for '{prompt_name}'")
        return None
    
    def load_prompt(
        self,
        prompt_name: str,
        version: str = "latest",
        use_ab_test: bool = False
    ) -> PromptVersion:
        """
        Load a prompt by name and version
        
        Args:
            prompt_name: Name of the prompt (e.g., "dashboard")
            version: Version string ("latest", "stable", or specific like "1.0.0")
            use_ab_test: If True, override version with A/B test selection
            
        Returns:
            PromptVersion object
            
        Raises:
            FileNotFoundError: If prompt or version not found
            ValueError: If prompt file is invalid
        """
        # A/B testing override
        if use_ab_test:
            ab_version = self.get_ab_version(prompt_name)
            if ab_version:
                version = ab_version
                logger.info(f"Using A/B test version '{version}' for '{prompt_name}'")
        
        # Resolve special version keywords
        if version == "latest":
            resolved_version = self.get_latest_version(prompt_name)
            if not resolved_version:
                raise FileNotFoundError(f"No versions found for prompt '{prompt_name}'")
            version = resolved_version
        elif version == "stable":
            resolved_version = self.get_stable_version(prompt_name)
            if not resolved_version:
                # Fallback to latest if no stable version
                logger.warning(f"No stable version for '{prompt_name}', using latest")
                resolved_version = self.get_latest_version(prompt_name)
            if not resolved_version:
                raise FileNotFoundError(f"No versions found for prompt '{prompt_name}'")
            version = resolved_version
        
        # Check cache
        cache_key = (prompt_name, version)
        if cache_key in self._cache:
            logger.debug(f"Cache hit for prompt '{prompt_name}' v{version}")
            return self._cache[cache_key]
        
        # Load from file
        prompt_version = self._load_prompt_file(prompt_name, version)
        
        if not prompt_version:
            raise FileNotFoundError(
                f"Prompt '{prompt_name}' version '{version}' not found. "
                f"Available versions: {self.list_versions(prompt_name)}"
            )
        
        # Cache for future use
        self._cache[cache_key] = prompt_version
        logger.info(f"Loaded prompt '{prompt_name}' v{version}")
        
        return prompt_version
    
    def load_with_fallback(
        self,
        prompt_name: str,
        version: str = "latest",
        use_ab_test: bool = False
    ) -> PromptVersion:
        """
        Load prompt with automatic fallback to stable version on failure
        
        Args:
            prompt_name: Name of the prompt
            version: Version string
            use_ab_test: If True, use A/B test version selection
            
        Returns:
            PromptVersion object (may be fallback version)
        """
        try:
            return self.load_prompt(prompt_name, version, use_ab_test)
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Failed to load prompt '{prompt_name}' v{version}: {e}")
            logger.info(f"Attempting fallback to stable version...")
            
            try:
                return self.load_prompt(prompt_name, version="stable", use_ab_test=False)
            except (FileNotFoundError, ValueError) as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                raise
    
    def _load_prompt_file(self, prompt_name: str, version: str) -> Optional[PromptVersion]:
        """
        Load prompt from YAML file
        
        Args:
            prompt_name: Name of the prompt
            version: Version string
            
        Returns:
            PromptVersion object or None if not found
        """
        file_path = self.prompts_dir / prompt_name / f"{version}.yaml"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                raise ValueError(f"Invalid YAML structure in {file_path}")
            
            return PromptVersion(data, file_path)
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            raise ValueError(f"Invalid YAML in prompt file: {e}")
        except Exception as e:
            logger.error(f"Error loading prompt file {file_path}: {e}")
            raise
    
    def _parse_version(self, version_str: str) -> Tuple[int, ...]:
        """
        Parse semantic version string into tuple for comparison
        
        Args:
            version_str: Version string (e.g., "1.2.3")
            
        Returns:
            Tuple of integers (e.g., (1, 2, 3))
        """
        try:
            # Extract numeric version parts (handles "1.2.3-beta" -> (1, 2, 3))
            parts = re.findall(r'\d+', version_str)
            return tuple(int(p) for p in parts)
        except:
            # Fallback for non-semantic versions
            return (0,)
    
    def clear_cache(self):
        """Clear the prompt cache (useful for development)"""
        self._cache.clear()
        logger.info("Prompt cache cleared")


# Global singleton instance
_global_loader: Optional[PromptLoader] = None


def get_loader() -> PromptLoader:
    """Get or create global PromptLoader instance"""
    global _global_loader
    if _global_loader is None:
        _global_loader = PromptLoader()
    return _global_loader


def load_prompt(
    prompt_name: str,
    version: str = "latest",
    use_ab_test: bool = False,
    **template_vars
) -> str:
    """
    Convenience function to load and render a prompt
    
    Args:
        prompt_name: Name of the prompt
        version: Version string ("latest", "stable", or specific)
        use_ab_test: Use A/B testing if configured
        **template_vars: Variables to render in the template
        
    Returns:
        Rendered prompt string
        
    Example:
        prompt = load_prompt("dashboard", version="1.0.0", content="...", num_chunks=5)
    """
    loader = get_loader()
    prompt_version = loader.load_with_fallback(prompt_name, version, use_ab_test)
    return prompt_version.render(**template_vars)


def list_prompt_versions(prompt_name: str) -> List[str]:
    """
    Convenience function to list available prompt versions
    
    Args:
        prompt_name: Name of the prompt
        
    Returns:
        List of version strings
    """
    loader = get_loader()
    return loader.list_versions(prompt_name)
