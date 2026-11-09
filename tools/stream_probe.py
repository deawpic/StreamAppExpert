"""
StreamProbe: Binary & Protocol Diagnostic Tool for Streaming Media.
Analyzes M3U8 playlists and video segment chunks without running Android Studio or Gradle.
Detects:
1. Disguised CDN Image Chunks (252-byte PNG dummy prefix)
2. MPEG-TS Sync Bytes (0x47) & 188-byte packet stride
3. H.264 NAL Type 9 AUD Delimiters (Warns against FLAG_DETECT_ACCESS_UNITS)
4. Cache-Control header pitfalls (Flags no-cache / warns on low max-age)
"""

from __future__ import annotations
import argparse
import sys
import urllib.request
import urllib.error
from urllib.parse import urljoin, urlparse

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
TS_SYNC_BYTE = 0x47
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


def fetch_data(url: str, referer: str = "", byte_range: str = "bytes=0-131071") -> tuple[bytes, dict]:
    """Fetches up to 128KB of stream data."""
    headers = {
        "User-Agent": DEFAULT_UA,
        "Accept": "*/*",
    }
    if referer:
        headers["Referer"] = referer
    if byte_range:
        headers["Range"] = byte_range

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            data = response.read()
            resp_headers = {k.lower(): v for k, v in response.headers.items()}
            return data, resp_headers
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Network Error: {e}", file=sys.stderr)
        sys.exit(1)


def analyze_chunk(data: bytes, headers: dict, url: str) -> bool:
    print("=" * 65)
    print(f"🔬 STREAM PROBE BINARY INSPECTION: {url[:70]}...")
    print("=" * 65)

    all_good = True

    # 1. Inspect HTTP Headers
    content_type = headers.get("content-type", "unknown")
    cache_control = headers.get("cache-control", "none")
    print(f"📄 Content-Type:  {content_type}")
    print(f"⏱️ Cache-Control: {cache_control}")

    if "no-cache" in cache_control.lower() or "no-store" in cache_control.lower():
        print("  ❌ WARNING: 'no-cache' detected! This will ruin scrubbing/seeking in ExoPlayer.")
        all_good = False
    elif "max-age" in cache_control.lower():
        print("  ✅ PASS: CDN caching headers preserved for smooth scrubbing.")
    else:
        print("  ⚠️ NOTICE: Missing explicit max-age cache header.")

    print("-" * 65)

    # 2. Inspect Prefix (PNG Magic Check)
    has_png_prefix = False
    if len(data) >= 8 and data[:8] == PNG_MAGIC:
        has_png_prefix = True
        print("🎭 [MASKED STREAM DETECTED] First 8 bytes match PNG header (\x89PNG\r\n\x1a\n)")
        print(f"   Size: At least {len(data)} bytes downloaded.")

        if len(data) >= 256:
            byte_252 = data[252]
            if byte_252 == TS_SYNC_BYTE:
                print(f"   ✅ Offset 252 (0xFC): Found MPEG-TS Sync Byte (0x47)! Pattern perfectly confirmed.")
                print(f"   💡 Recommendation: Use MaskedTsDataSource to discard 252-byte PNG dummy header.")
            else:
                print(f"   ❌ Offset 252 byte is 0x{byte_252:02X} (Expected 0x47 Sync Byte). Custom offset needed.")
                all_good = False
    else:
        if len(data) > 0 and data[0] == TS_SYNC_BYTE:
            print("✅ Pure unmasked MPEG-TS chunk: Starts directly with Sync Byte 0x47.")
        else:
            print(f"ℹ️ First byte is 0x{data[0]:02X} (Non-standard or raw payload).")

    print("-" * 65)

    # 3. Inspect Packet Stride (188 bytes)
    start_offset = 252 if has_png_prefix else 0
    if len(data) > start_offset + 564:
        sync1 = data[start_offset]
        sync2 = data[start_offset + 188]
        sync3 = data[start_offset + 376]
        if sync1 == TS_SYNC_BYTE and sync2 == TS_SYNC_BYTE and sync3 == TS_SYNC_BYTE:
            print("✅ Packet Stride: Verified 188-byte MPEG-TS packet alignment across multiple chunks.")
        else:
            print("⚠️ Packet Stride: 188-byte sync alignment could not be verified.")

    print("-" * 65)

    # 4. Inspect H.264 NAL Type 9 AUD Delimiters (The ExoPlayer Freeze Bug)
    # NAL Type 9 pattern: 00 00 01 09 or 00 00 00 01 09
    nal9_count = 0
    idx = start_offset
    limit = min(len(data), 65536)
    while idx < limit - 5:
        if data[idx:idx+4] == b"\x00\x00\x01\x09" or data[idx:idx+5] == b"\x00\x00\x00\x01\x09":
            nal9_count += 1
            idx += 4
        else:
            idx += 1

    if nal9_count > 0:
        print(f"🚨 [CRITICAL NAL TYPE 9 AUD DETECTED] Found {nal9_count} AUD delimiters in sample!")
        print("   ⚠️ EXOPLAYER FREEZE WARNING:")
        print("   This stream includes explicit AUD markers. DO NOT use FLAG_DETECT_ACCESS_UNITS in")
        print("   DefaultHlsExtractorFactory, or H264Reader will drop all non-IDR frames, freezing the video!")
        print("   👉 Use: DefaultHlsExtractorFactory() with flags = 0.")
    else:
        print("ℹ️ No NAL Type 9 AUD delimiters detected in first 64KB sample.")

    print("=" * 65)
    return all_good


def main() -> None:
    parser = argparse.ArgumentParser(description="StreamProbe: Video Stream & Segment Binary Diagnostics")
    parser.add_argument("url", help="M3U8 Master playlist URL or direct video chunk URL")
    parser.add_argument("--referer", default="", help="HTTP Referer header (e.g. portal origin)")

    args = parser.parse_args()
    target_url = args.url

    print(f"🚀 Probing target: {target_url}...")
    data, headers = fetch_data(target_url, referer=args.referer)

    # Check if target is M3U8 playlist
    if b"#EXTM3U" in data:
        print("📋 Target is M3U8 Master / Media Playlist.")
        lines = data.decode("utf-8", errors="ignore").splitlines()
        first_chunk_url = ""
        for line in lines:
            line_str = line.strip()
            if line_str and not line_str.startswith("#"):
                first_chunk_url = urljoin(target_url, line_str)
                break

        if first_chunk_url:
            print(f"🎯 Discovered first segment: {first_chunk_url}")
            chunk_data, chunk_headers = fetch_data(first_chunk_url, referer=args.referer)
            analyze_chunk(chunk_data, chunk_headers, first_chunk_url)
        else:
            print("⚠️ No media chunk URLs found in playlist lines.")
    else:
        analyze_chunk(data, headers, target_url)


if __name__ == "__main__":
    main()
