---
name: redis
description: "Redis caching patterns for OTT streaming: Metadata caching, token expiration TTL, sliding-window rate limiting, and connection pooling."
risk: safe
source: adapted-from-awesome-skills
date_added: "2026-11-09"
---

# ⚡ Redis for OTT Streaming Gateways

You are a Redis specialist optimizing in-memory data caching and rate limiting for high-traffic video streaming gateways.

## 🎯 Streaming Key Design & TTL Strategy

| Key Pattern | Data Structure | Recommended TTL | Purpose |
|---|---|---|---|
| `catalog:categories` | JSON String | 3,600s (1 hour) | Cache homepage categories & subcategories |
| `series:{id}:detail` | JSON String | 21,600s (6 hours) | Cache series synopsis, poster, and episode lists |
| `stream:{id}:token` | Hash | 600s (10 mins) | Cache short-lived resolved m3u8 tokens |
| `ratelimit:{ip}` | Integer | 60s (Sliding) | Prevent scraper ban by limiting client requests |

---

## 🛠️ Python Async Redis Implementation

```python
import redis.asyncio as aioredis
import json
from typing import Optional, Dict, Any

class StreamCache:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.pool = aioredis.ConnectionPool.from_url(redis_url, max_connections=20)
        self.client = aioredis.Redis(connection_pool=self.pool)

    async def get_series_detail(self, series_id: str) -> Optional[Dict[str, Any]]:
        val = await self.client.get(f"series:{series_id}:detail")
        return json.loads(val) if val else None

    async def set_series_detail(self, series_id: str, data: Dict[str, Any], ttl_seconds: int = 21600):
        await self.client.set(
            f"series:{series_id}:detail",
            json.dumps(data),
            ex=ttl_seconds
        )

    async def is_rate_limited(self, client_ip: str, limit: int = 60, window_sec: int = 60) -> bool:
        key = f"ratelimit:{client_ip}"
        current = await self.client.incr(key)
        if current == 1:
            await self.client.expire(key, window_sec)
        return current > limit
```
