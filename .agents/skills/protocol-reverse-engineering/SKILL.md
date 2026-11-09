---
name: protocol-reverse-engineering
description: "Network protocol reverse engineering for streaming media: Sniffing HLS/DASH traffic, reconstructing tokenplay handshakes, intercepting CDN segments, and bypassing anti-bot mitigations."
risk: safe
source: adapted-from-awesome-skills
date_added: "2026-11-09"
---

# 🌐 Protocol Reverse Engineering (Streaming & OTT Edition)

You are an expert Protocol Reverse Engineer specializing in media delivery protocols (HLS, MPEG-DASH, WebSockets) and streaming API handshakes.

## 🎯 Protocol Analysis Checklist for Video Gateways

### 1. The 4-Stage Stream Discovery Chain
When reverse-engineering a web streaming portal, trace the full handshake flow:
```text
1. Portal Page (HTML) -> Extract Post ID & Category Metadata
2. AJAX Player Request -> POST /admin-ajax.php (action=miru_custom_player)
3. Iframe Gateway -> Extract embed URL (https://embed-provider.com/embed/{md5})
4. Token Exchange -> POST /api/tokenplay {"md5": "...", "parent": "..."}
5. Master Manifest -> GET /api/stream/{id}/index.m3u8?token=...&sid=...
6. Media Chunks -> GET /api/stream/{id}/chunk_001.image (Masked MPEG-TS)
```

### 2. Identifying Anti-Bot & Fingerprint Traps
- **Missing Referer / Origin**: Many streaming APIs immediately return 403 Forbidden or 401 Unauthorized if the `Referer` does not match the parent embed origin.
- **Header Order Sensitivity**: Some WAFs fingerprint requests by header casing and order (`User-Agent`, `Accept`, `Sec-Fetch-*`).
- **Session Expiration Timing**: Verify `expires` and `timestamp` fields in the JSON response; tokens typically expire after 4 to 8 hours.

### 3. Sniffing Network Traffic with mitmproxy
Run mitmproxy with a filter script to isolate media playlists:
```python
# dump_m3u8.py
def response(flow):
    url = flow.request.pretty_url
    if ".m3u8" in url or "tokenplay" in url:
        print(f"[FOUND STREAM] {flow.request.method} {url}")
        if flow.response.text:
            print(f"[BODY] {flow.response.text[:300]}")
```
Run: `mitmdump -s dump_m3u8.py "~u m3u8 | ~u tokenplay"`
