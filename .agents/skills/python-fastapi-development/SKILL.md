---
name: python-fastapi-development
description: "High-performance Python FastAPI development for streaming gateways: Async proxying with StreamingResponse, M3U8 playlist rewriting, Redis caching, and Pydantic V2 schemas."
risk: safe
source: adapted-from-awesome-skills
date_added: "2026-11-09"
---

# 🚀 Python FastAPI Streaming Development

You are an expert Backend Engineer specializing in FastAPI, asynchronous streaming gateways, and reverse proxying for media apps.

## 🎯 Core Streaming Gateway Patterns

### 1. Transparent M3U8 Playlist URL Rewriter
When origin CDNs enforce IP restrictions or CORS on client devices, the FastAPI gateway proxies the playlist and rewrites segment URLs:

```python
from fastapi import APIRouter, Response, HTTPException
import httpx
import re

router = APIRouter(prefix="/proxy")
client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)

@router.get("/playlist.m3u8")
async def proxy_m3u8(origin_url: str):
    res = await client.get(origin_url)
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail="Upstream CDN error")

    lines = res.text.splitlines()
    rewritten_lines = []
    base_origin = origin_url.rsplit("/", 1)[0]

    for line in lines:
        line_clean = line.strip()
        if line_clean and not line_clean.startswith("#"):
            # Resolve relative chunk URLs to proxy URL
            chunk_url = line_clean if line_clean.startswith("http") else f"{base_origin}/{line_clean}"
            rewritten_lines.append(f"/proxy/chunk?url={chunk_url}")
        else:
            rewritten_lines.append(line)

    return Response(
        content="\n".join(rewritten_lines),
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "max-age=300"}
    )
```

### 2. High-Throughput Chunk Proxy with StreamingResponse
```python
from fastapi.responses import StreamingResponse

@router.get("/chunk")
async def proxy_chunk(url: str):
    req = client.build_request("GET", url)
    res = await client.send(req, stream=True)

    # Discard 252-byte dummy PNG prefix if detected
    async def chunk_generator():
        first_chunk = True
        async for chunk in res.aiter_bytes(chunk_size=65536):
            if first_chunk and len(chunk) >= 252 and chunk.startswith(b"\x89PNG\r\n\x1a\n"):
                chunk = chunk[252:]
                first_chunk = False
            yield chunk

    return StreamingResponse(
        chunk_generator(),
        media_type="video/mp2t",
        headers={"Cache-Control": "max-age=31536000"}  # Preserve CDN caching!
    )
```

### 3. Pydantic V2 Typed Models
Always enforce strict typing and schema validation using Pydantic V2 (`BaseModel`, `Field`).
