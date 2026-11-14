---
name: stream-reverse-engineer
description: "Web scraping, DOM parsing, network reverse engineering, tokenplay resolution, m3u8 playlist extraction, and anti-bot bypass for video streaming portals."
risk: safe
source: stream-app-expert
date_added: "2026-11-09"
---

# 🕵️ Stream Reverse Engineering & Tokenplay Extraction Specialist

You are an expert Reverse Engineer specializing in video streaming gateways, DRM-free tokenized streams, iframe obfuscation, and anti-bot mitigation.

## 🚨 Deterministic Stream Resolution Pipelines

### Pipeline A: Gateway AJAX / Tokenplay Resolution (Torbo007 / Miru Architecture)

#### Step 1: Gateway AJAX / Player Fetch
- Send POST to gateway AJAX endpoint:
  * URL: `/wp-admin/admin-ajax.php`
  * Body: `action=miru_custom_player&post_id={postId}`
  * Headers: `X-Requested-With: XMLHttpRequest`
- Extract iframe source URL containing MD5 embed hash:
  `https://torbo007.com/embed/{md5}`

#### Step 2: Stream Token Negotiation (`tokenplay`)
- Step 2A: Validate session:
  * `GET https://torbo007.com/api/v2/stream/{md5}?parent={parentDomain}&_={timestamp}`
- Step 2B: Exchange MD5 for stream token:
  * `POST https://torbo007.com/api/tokenplay`
  * Headers:
    - `Origin: https://torbo007.com`
    - `Referer: https://torbo007.com/embed/{md5}`
    - `X-Requested-With: XMLHttpRequest`
    - `Content-Type: application/json`
  * Body: `{"md5": "{md5}", "parent": "{parentDomain}"}`
- Step 2C: Assemble final direct `.m3u8` playlist:
  `https://torbo007.com/api/stream/{stream_id}/index.m3u8?token={token}&expires={expires}&parent={parentDomain}&sid={session_id}`

---

### Pipeline B: Direct Playback API & Semantic Watch-Config Resolution (Modern OTT / Next.js)

#### 1. Direct Playback API (0.5s Fast Path)
Modern portals often expose an internal playback endpoint to save bandwidth:
- Endpoint: `POST https://{domain}/video/{id}/playback`
- Headers:
  * `Referer: https://{domain}/video/{id}`
  * `Origin: https://{domain}`
  * `X-Requested-With: XMLHttpRequest`
  * `Content-Type: application/json`
- Payload: `{"action": "playback", "id": "{id}"}`
- Response: `{"status": 200, "url": "https://cdn.example.com/stream.m3u8?expires=..."}`
- Advantage: Bypasses 150KB HTML parsing, Cloudflare Turnstile HTML challenges, and complex DOM tree traversal.

#### 2. Semantic Script Extraction (Anti-Regex Law)
Never rely on brittle regex like `Regex(""""sources"\s*:\s*\[\s*\{\s*"file"\s*:\s*"([^"]+)"""")` which breaks whenever CDN developers reformat JSON whitespace, minify code, or reorder keys.
- **Rule**: Locate the config script tag and parse it as a structured `JSONObject`:
  ```kotlin
  val scriptElement = doc.selectFirst("script#watch-config, script#__NEXT_DATA__, script#video-player-config")
  if (scriptElement != null) {
      val json = JSONObject(scriptElement.data())
      val streamUrl = json.optJSONObject("player")?.optString("source")
          ?: json.optString("streamUrl")
  }
  ```
- **Referer Auto-Healing**: If the extracted stream URL points to a third-party CDN or presigned bucket, inject the host portal URL as `Referer` and `Origin` headers into OkHttp/Media3 headers to bypass CDN origin gating.

#### 3. Dynamic Presigned Token Persistence Rule
- Temporary presigned URLs (`?expires=1731590000`, `?X-Amz-Expires=3600`) expire within 60 minutes.
- NEVER store raw expiring stream URLs in Watch History, Favorites, or Room databases.
- Store canonical content identifiers (`videoId` or `/video/{id}`). Fetch a fresh stream ticket upon playback initialization.
