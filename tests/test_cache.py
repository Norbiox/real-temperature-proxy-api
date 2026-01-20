"""Tests for LRU cache backend."""

import pytest

from src.real_temperature_proxy_api.core.cache import LRUInMemoryBackend


class TestLRUCache:
    """Test LRU cache implementation."""

    @pytest.mark.asyncio
    async def test_basic_get_set(self):
        """Test basic cache get/set operations."""
        cache = LRUInMemoryBackend(max_size=3)

        # Set and get
        await cache.set("key1", "value1", 60)
        result = await cache.get("key1")

        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_missing_key(self):
        """Test getting a non-existent key."""
        cache = LRUInMemoryBackend(max_size=3)

        result = await cache.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test that LRU eviction works correctly."""
        cache = LRUInMemoryBackend(max_size=3)

        # Fill cache to max
        await cache.set("a", 1, 60)
        await cache.set("b", 2, 60)
        await cache.set("c", 3, 60)

        assert cache.size() == 3

        # Access "a" to make it recently used
        await cache.get("a")

        # Add new item - should evict "b" (least recently used)
        await cache.set("d", 4, 60)

        assert cache.size() == 3
        assert await cache.get("a") == 1  # Still there (accessed recently)
        assert await cache.get("b") is None  # Evicted (LRU)
        assert await cache.get("c") == 3  # Still there
        assert await cache.get("d") == 4  # New item

    @pytest.mark.asyncio
    async def test_update_existing_key(self):
        """Test updating an existing key marks it as recently used."""
        cache = LRUInMemoryBackend(max_size=3)

        # Fill cache
        await cache.set("a", 1, 60)
        await cache.set("b", 2, 60)
        await cache.set("c", 3, 60)

        # Update "a" (marks as recently used)
        await cache.set("a", 10, 60)

        # Add new item - should evict "b" (LRU)
        await cache.set("d", 4, 60)

        assert await cache.get("a") == 10  # Updated and still there
        assert await cache.get("b") is None  # Evicted
        assert await cache.get("c") == 3  # Still there
        assert await cache.get("d") == 4  # New item

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting a cache entry."""
        cache = LRUInMemoryBackend(max_size=3)

        await cache.set("key1", "value1", 60)
        await cache.delete("key1")

        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing the cache."""
        cache = LRUInMemoryBackend(max_size=3)

        await cache.set("a", 1, 60)
        await cache.set("b", 2, 60)
        await cache.set("c", 3, 60)

        assert cache.size() == 3

        await cache.clear()

        assert cache.size() == 0
        assert await cache.get("a") is None
        assert await cache.get("b") is None
        assert await cache.get("c") is None

    @pytest.mark.asyncio
    async def test_clear_specific_key(self):
        """Test clearing a specific key."""
        cache = LRUInMemoryBackend(max_size=3)

        await cache.set("a", 1, 60)
        await cache.set("b", 2, 60)

        await cache.clear(key="a")

        assert cache.size() == 1
        assert await cache.get("a") is None
        assert await cache.get("b") == 2

    @pytest.mark.asyncio
    async def test_size_tracking(self):
        """Test that size() returns correct count."""
        cache = LRUInMemoryBackend(max_size=5)

        assert cache.size() == 0

        await cache.set("a", 1, 60)
        assert cache.size() == 1

        await cache.set("b", 2, 60)
        assert cache.size() == 2

        await cache.delete("a")
        assert cache.size() == 1

        await cache.clear()
        assert cache.size() == 0
