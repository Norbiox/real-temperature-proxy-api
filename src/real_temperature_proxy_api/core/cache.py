"""Custom LRU cache backend for fastapi-cache2 with size limits."""

from collections import OrderedDict
from typing import Any

from fastapi_cache.backends.inmemory import InMemoryBackend


class LRUInMemoryBackend(InMemoryBackend):
    """In-memory cache backend with LRU eviction and max size limit.

    When the cache reaches max_size, the least recently used (LRU) entry
    is evicted to make room for new entries.

    Example:
        >>> cache = LRUInMemoryBackend(max_size=3)
        >>> # Cache can hold max 3 items with LRU eviction
    """

    def __init__(self, max_size: int = 10000):
        """Initialize LRU cache backend.

        Args:
            max_size: Maximum number of entries before LRU eviction (default: 10000)

        Example:
            >>> cache = LRUInMemoryBackend(max_size=100)
            >>> cache.max_size
            100
        """
        super().__init__()
        self.max_size = max_size
        # Replace the default dict with OrderedDict for LRU tracking
        self._store: OrderedDict[str, Any] = OrderedDict()

    async def get(self, key: str) -> Any:
        """Get value from cache and mark as recently used.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found

        Example:
            >>> cache = LRUInMemoryBackend(max_size=3)
            >>> import asyncio
            >>> asyncio.run(cache.set("key1", "value1", 60))
            >>> asyncio.run(cache.get("key1"))
            'value1'
        """
        if key in self._store:
            # Move to end (most recently used)
            self._store.move_to_end(key)
            return self._store[key]
        return None

    async def set(self, key: str, value: Any, expire: int | None = None) -> None:
        """Set value in cache with LRU eviction if needed.

        If cache is at max_size, evicts the least recently used entry.

        Args:
            key: Cache key
            value: Value to cache
            expire: TTL in seconds (not used by this backend, handled by fastapi-cache2)

        Example:
            >>> cache = LRUInMemoryBackend(max_size=2)
            >>> import asyncio
            >>> asyncio.run(cache.set("a", 1, 60))
            >>> asyncio.run(cache.set("b", 2, 60))
            >>> asyncio.run(cache.set("c", 3, 60))  # Evicts "a"
            >>> asyncio.run(cache.get("a"))  # Returns None
        """
        # Check if we need to evict before adding
        if key not in self._store and len(self._store) >= self.max_size:
            # Evict least recently used (first item)
            evicted_key = next(iter(self._store))
            del self._store[evicted_key]

        # Add or update (move to end if exists)
        self._store[key] = value
        if key in self._store:
            self._store.move_to_end(key)

    async def delete(self, key: str) -> None:
        """Delete key from cache.

        Args:
            key: Cache key to delete

        Example:
            >>> cache = LRUInMemoryBackend(max_size=3)
            >>> import asyncio
            >>> asyncio.run(cache.set("key1", "value1", 60))
            >>> asyncio.run(cache.delete("key1"))
            >>> asyncio.run(cache.get("key1"))
        """
        if key in self._store:
            del self._store[key]

    async def clear(self, namespace: str | None = None, key: str | None = None) -> None:
        """Clear cache entries.

        Args:
            namespace: Namespace prefix to clear (not implemented)
            key: Specific key to clear

        Example:
            >>> cache = LRUInMemoryBackend(max_size=3)
            >>> import asyncio
            >>> asyncio.run(cache.set("a", 1, 60))
            >>> asyncio.run(cache.clear())
            >>> asyncio.run(cache.get("a"))
        """
        if key:
            await self.delete(key)
        else:
            self._store.clear()

    def size(self) -> int:
        """Get current cache size.

        Returns:
            Number of entries in cache

        Example:
            >>> cache = LRUInMemoryBackend(max_size=3)
            >>> import asyncio
            >>> asyncio.run(cache.set("a", 1, 60))
            >>> cache.size()
            1
        """
        return len(self._store)
