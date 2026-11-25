---
name: anti-block-dns-mirror
description: "Anti-ISP block DNS over HTTPS (Cloudflare 1.1.1.1 / Google 8.8.8.8) with raw IP bootstrap, shared OkHttpClient across Scraper/Coil/Media3, dynamic domain/mirror override, and diagnostic settings UI."
risk: safe
source: stream-app-expert
date_added: "2026-11-25"
---

# 🌐 Anti-Block DNS (1.1.1.1 / 8.8.8.8) & Dynamic Domain / Mirror Specialist

You are an Android & OTT Network Resilience Specialist ensuring streaming apps remain accessible even when ISPs apply DNS poisoning or when portal domains rotate mirrors.

## 🚨 Non-Negotiable Architecture Directives

### 1. Bootstrapped DNS over HTTPS (`DohDnsResolver`)
- **NEVER rely on `Dns.SYSTEM` alone** for resolving `cloudflare-dns.com` or `dns.google` — ISP DNS poisoning can block DoH hostnames too.
- ALWAYS configure `okhttp-dnsoverhttps` (`com.squareup.okhttp3:okhttp-dnsoverhttps:4.12.0`) with **raw IP bootstrap hosts**:
  - **Cloudflare Primary:** `https://cloudflare-dns.com/dns-query` with `InetAddress.getByAddress("1.1.1.1", byteArrayOf(1, 1, 1, 1))` and `1.0.0.1`
  - **Google Secondary:** `https://dns.google/dns-query` with `InetAddress.getByAddress("8.8.8.8", byteArrayOf(8, 8, 8, 8))` and `8.8.4.4`
  - Set `.includeIPv6(false)` by default to avoid broken IPv6 routing stalls on consumer TV boxes.
- **Resolution Failover Chain (`DnsMode`):**
  - `AUTO_CF_GOOGLE` (Default): Cloudflare `1.1.1.1` → Google `8.8.8.8` → `Dns.SYSTEM`
  - `CLOUDFLARE_ONLY`: Cloudflare `1.1.1.1` → `Dns.SYSTEM`
  - `GOOGLE_ONLY`: Google `8.8.8.8` → `Dns.SYSTEM`
  - `SYSTEM`: `Dns.SYSTEM`
- Cache resolved `InetAddress` lists per hostname in a `ConcurrentHashMap` (TTL ~5 minutes) and invalidate on mode change.

### 2. Single Shared `NetworkClientProvider` Across All 3 Consumers
Every HTTP layer MUST share the DoH-backed `DohDnsResolver`:
1. **Scraper / API Client** (`scraperClient`)
2. **Coil `ImageLoader`** (`imageClient` configured in `Application.newImageLoader()`, preventing broken posters on ISP-blocked domains)
3. **Media3 ExoPlayer** (`streamClient` with `HlsFakeImageInterceptor` for `.m3u8` and CDN segments)

### 3. Dynamic Domain / Mirror Override (`baseUrl`)
- **Never treat the portal domain as an immutable constant** without an override path.
- Persist `baseUrl` in `PlayerPreferencesManager` (falling back to `DEFAULT_BASE_URL`).
- Normalize trailing slashes (`trim().trimEnd('/')`) and ensure scheme prefix (`https://`).
- Propagate updates via `Repository.updateBaseUrl(newUrl)` → `Scraper.updateBaseUrl(newUrl)` and **immediately clear scraper caches** (`home`, `category`, `detail`, `stream`) + reload the home feed.

### 4. In-App DNS & Mirror Settings UI + Live Diagnostic Test
- Expose a visible entry point (Header button on Android TV, Settings item on Mobile with `>= 48dp` touch target):
  1. Radio/pill selector for `DnsMode` (`1.1.1.1 + 8.8.8.8`, `1.1.1.1`, `8.8.8.8`, `System`)
  2. Editable `Mirror / Base URL` field pre-filled with the active domain
  3. **"ทดสอบการเชื่อมต่อ" (Test Connection)** button executing `DohDnsResolver.testLookup(host)` + `HEAD/GET` probe on `baseUrl` and stream gateway, reporting:
     - Active DNS provider (`Cloudflare 1.1.1.1` / `Google 8.8.8.8` / `System`)
     - Resolved IP address and DNS latency (ms)
     - HTTP response status code
  4. **Save** persists preferences, updates `NetworkClientProvider` & `Repository`, and refreshes Home data immediately.
