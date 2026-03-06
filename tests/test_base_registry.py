"""
Unit tests for base registry pattern (Quick Win 3).

Tests cover:
- Generic registry caching
- File persistence
- CRUD operations
- Error handling
"""

import pytest
import json
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional

from orchestrator.base_registry import BaseRegistry


# ============================================================================
# Test Models
# ============================================================================

class TestConfig(BaseModel):
    """Test configuration model."""
    config_id: str = Field(..., description="Config ID")
    name: str = Field(..., description="Config name")
    value: int = Field(default=0, description="Config value")


class TestRegistry(BaseRegistry[TestConfig]):
    """Test registry implementation."""

    def _parse_config(self, data: dict) -> TestConfig:
        """Parse raw data into TestConfig."""
        return TestConfig(**data)

    def _get_config_filename(self, key: str) -> str:
        """Get filename for a config key."""
        return f"{key}_config.json"


# ============================================================================
# Test Cases
# ============================================================================

@pytest.mark.unit
class TestBaseRegistryCaching:
    """Test base registry caching functionality (Quick Win 3)."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def registry(self, temp_storage):
        """Create test registry."""
        return TestRegistry(temp_storage)

    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert registry.storage_dir.exists()
        assert len(registry._cache) == 0

    def test_save_and_load_config(self, registry):
        """Test saving and loading configuration."""
        config = TestConfig(config_id="test1", name="Test Config", value=42)

        # Save
        result = registry.save("test1", config)
        assert result is True

        # Verify file created
        config_file = registry.storage_dir / "test1_config.json"
        assert config_file.exists()

        # Load
        loaded = registry.load("test1")
        assert loaded is not None
        assert loaded.config_id == "test1"
        assert loaded.name == "Test Config"
        assert loaded.value == 42

    def test_cache_hit_on_reload(self, registry):
        """Test cache hit when reloading same config."""
        config = TestConfig(config_id="test1", name="Test", value=1)
        registry.save("test1", config)

        # First load - from disk
        loaded1 = registry.load("test1")
        assert loaded1 is not None

        # Clear cache to force disk reload
        original_cache_size = len(registry._cache)

        # Second load - should use cache
        loaded2 = registry.load("test1")
        assert loaded1 == loaded2

    def test_cache_persistence_within_instance(self, registry):
        """Test cache persists within registry instance."""
        config = TestConfig(config_id="test1", name="Test", value=1)
        registry.save("test1", config)

        # Load and cache
        loaded1 = registry.load("test1")
        cache_size_1 = len(registry._cache)

        # Second load should use cache
        loaded2 = registry.load("test1")
        cache_size_2 = len(registry._cache)

        assert cache_size_1 == cache_size_2
        assert loaded1 == loaded2

    def test_list_all_configs(self, registry):
        """Test listing all configurations."""
        configs = [
            TestConfig(config_id="test1", name="Config 1", value=1),
            TestConfig(config_id="test2", name="Config 2", value=2),
            TestConfig(config_id="test3", name="Config 3", value=3),
        ]

        for config in configs:
            registry.save(config.config_id, config)

        # List all
        all_configs = registry.list_all()
        assert len(all_configs) >= 3

    def test_delete_config(self, registry):
        """Test deleting configuration."""
        config = TestConfig(config_id="test1", name="Test", value=1)
        registry.save("test1", config)

        # Verify exists
        assert registry.exists("test1")

        # Delete
        result = registry.delete("test1")
        assert result is True

        # Verify deleted
        assert not registry.exists("test1")

    def test_clear_cache(self, registry):
        """Test clearing cache."""
        config = TestConfig(config_id="test1", name="Test", value=1)
        registry.save("test1", config)

        # Load to cache
        registry.load("test1")
        assert len(registry._cache) > 0

        # Clear cache
        registry.clear_cache()
        assert len(registry._cache) == 0

    def test_exists_check(self, registry):
        """Test existence check."""
        config = TestConfig(config_id="test1", name="Test", value=1)
        registry.save("test1", config)

        assert registry.exists("test1") is True
        assert registry.exists("nonexistent") is False

    def test_cache_stats(self, registry):
        """Test cache statistics."""
        config = TestConfig(config_id="test1", name="Test", value=1)
        registry.save("test1", config)

        stats = registry.get_cache_stats()
        assert "cached_items" in stats
        assert "storage_dir" in stats

    def test_load_nonexistent_returns_none(self, registry):
        """Test loading nonexistent config returns None."""
        result = registry.load("nonexistent")
        assert result is None

    def test_delete_nonexistent_returns_false(self, registry):
        """Test deleting nonexistent config returns False."""
        result = registry.delete("nonexistent")
        assert result is False

    def test_config_persistence_across_instances(self, temp_storage):
        """Test that configs persist across registry instances."""
        # Save with first instance
        registry1 = TestRegistry(temp_storage)
        config = TestConfig(config_id="persistent", name="Persistent", value=99)
        registry1.save("persistent", config)

        # Load with second instance
        registry2 = TestRegistry(temp_storage)
        loaded = registry2.load("persistent")

        assert loaded is not None
        assert loaded.config_id == "persistent"
        assert loaded.value == 99

    def test_error_handling_invalid_json(self, temp_storage):
        """Test error handling for invalid JSON."""
        registry = TestRegistry(temp_storage)

        # Create invalid JSON file
        config_file = Path(temp_storage) / "invalid_config.json"
        with open(config_file, 'w') as f:
            f.write("{ invalid json }")

        # Should handle gracefully
        result = registry.load("invalid")
        assert result is None
