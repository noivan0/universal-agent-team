"""
Base registry class for managing configuration files.

Provides a reusable foundation for all registry patterns:
- ProjectRegistry
- TeamRegistry
- SpecialistRegistry

Features:
- Generic caching with type safety
- File-based persistence
- CRUD operations
- Logging and error handling
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRegistry(ABC, Generic[T]):
    """
    Abstract base class for registry patterns.

    Subclasses must implement:
    1. _parse_config(data: dict) -> T
    2. _get_config_filename(key: str) -> str
    """

    def __init__(self, storage_dir: str):
        """
        Initialize registry with storage directory.

        Args:
            storage_dir: Directory for storing configuration files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, T] = {}
        logger.info(f"Registry initialized: {self.storage_dir}")

    @abstractmethod
    def _parse_config(self, data: dict) -> T:
        """
        Parse raw configuration data into typed object.

        Args:
            data: Raw configuration dictionary

        Returns:
            Parsed configuration object of type T
        """
        pass

    @abstractmethod
    def _get_config_filename(self, key: str) -> str:
        """
        Get filename for a configuration key.

        Args:
            key: Configuration key

        Returns:
            Filename (should end with .json or similar)
        """
        pass

    def validate_config(self, config: T) -> bool:
        """
        Validate configuration before saving.

        Can be overridden by subclasses for custom validation.
        Default implementation only checks Pydantic validation.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        # Default: only use Pydantic validation if available
        if hasattr(config, 'model_validate'):
            try:
                config.model_validate(config.model_dump())
                return True
            except Exception as e:
                logger.warning(f"Config validation failed: {e}")
                return False
        return True

    def load(self, key: str) -> Optional[T]:
        """
        Load configuration with caching.

        Args:
            key: Configuration key to load

        Returns:
            Configuration object if found, None otherwise
        """
        # Check cache first
        if key in self._cache:
            logger.debug(f"Cache hit for {key}")
            return self._cache[key]

        # Load from disk
        file_path = self.storage_dir / self._get_config_filename(key)
        if not file_path.exists():
            logger.debug(f"File not found: {file_path}")
            return None

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                config = self._parse_config(data)
                self._cache[key] = config
                logger.debug(f"Loaded and cached: {key}")
                return config
        except Exception as e:
            logger.error(f"Failed to load {key} from {file_path}: {e}")
            return None

    def save(self, key: str, config: T) -> bool:
        """
        Save configuration to disk with validation.

        Args:
            key: Configuration key
            config: Configuration object to save

        Returns:
            True if save successful, False otherwise
        """
        # Validate configuration
        if not self.validate_config(config):
            logger.error(f"Configuration validation failed for {key}")
            return False

        file_path = self.storage_dir / self._get_config_filename(key)

        try:
            # Serialize to dict
            if hasattr(config, 'model_dump'):
                # Pydantic model
                data = config.model_dump()
            elif hasattr(config, '__dict__'):
                # Regular Python object
                data = config.__dict__
            else:
                data = config

            # Write to file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            # Update cache
            self._cache[key] = config
            logger.info(f"Saved configuration: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save {key}: {e}")
            return False

    def list_all(self) -> Dict[str, T]:
        """
        Load all configurations from storage.

        Returns:
            Dictionary of all configurations {key: config}
        """
        result = {}

        # Iterate through JSON files in storage directory
        for file_path in self.storage_dir.glob("*.json"):
            try:
                key = file_path.stem
                config = self.load(key)
                if config:
                    result[key] = config
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")

        return result

    def delete(self, key: str) -> bool:
        """
        Delete configuration from disk and cache.

        Args:
            key: Configuration key to delete

        Returns:
            True if delete successful, False otherwise
        """
        file_path = self.storage_dir / self._get_config_filename(key)

        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")

            self._cache.pop(key, None)
            logger.info(f"Deleted configuration: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {key}: {e}")
            return False

    def clear_cache(self) -> None:
        """
        Clear in-memory cache.

        Configurations will be reloaded from disk on next access.
        """
        self._cache.clear()
        logger.info("Cache cleared")

    def exists(self, key: str) -> bool:
        """
        Check if configuration exists.

        Args:
            key: Configuration key

        Returns:
            True if configuration exists, False otherwise
        """
        file_path = self.storage_dir / self._get_config_filename(key)
        return file_path.exists()

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cached_items": len(self._cache),
            "storage_dir": str(self.storage_dir)
        }
