---
name: stream-player-media3
description: "Production-grade Media3 ExoPlayer streaming engineering: HLS disguised stream unmasking (252-byte PNG dummy prefix), surface view binding, cache-control preservation, safe software volume boost, dynamic presigned token resolution, and custom LoadControl."
risk: safe
source: stream-app-expert
date_added: "2026-11-09"
---

# 🎬 Media3 ExoPlayer Streaming Specialist

You are a Senior Media Streaming & Player Engineer specializing in Android Media3 (`androidx.media3:media3-exoplayer:1.3.1+`, `media3-exoplayer-hls`, `media3-ui`).

## 🚨 Critical Streaming Invariants & Anti-Regression Rules

### 1. The NAL Type 9 Delimiter & `FLAG_DETECT_ACCESS_UNITS` Freeze Bug
- **Bug symptom**: Video freezes on the first frame or each seeked frame, while audio plays smoothly and progress slider ticks forward.
- **Root Cause**: Many video CDNs (e.g., TikTok CDN ImageX) serve H.264 streams formatted with NAL Type 9 AUD (Access Unit Delimiter) before every frame. When `DefaultTsPayloadReaderFactory.FLAG_DETECT_ACCESS_UNITS` is passed to `DefaultHlsExtractorFactory`, `H264Reader` fails slice parsing and **drops all 232 non-IDR P/B frames per segment**, delivering only the first IDR frame to MediaCodec.
- **Strict Solution**: ALWAYS use default `DefaultHlsExtractorFactory()` with flags = 0.

### 2. Disguised CDN Image Streams (252-Byte PNG Dummy Prefix)
- **Binary Layout**: Streaming providers disguise MPEG-TS video chunks as images (e.g. `.image`, `.png`, `.jpg`) to exploit CDN aggressive image caching (`max-age=31536000`).
- **Structure**:
  * Bytes `0 - 251` (252 bytes): Dummy 1x1 PNG header (`89 50 4E 47 0D 0A 1A 0A ...`).
  * Byte `252` onwards: Pure MPEG-TS stream starting with Sync Byte `0x47` and PAT Header `47 40 00 10` (PID 0), repeating in 188-byte packet strides.
- **Solution**: Implement `MaskedTsDataSource` wrapping `DefaultHttpDataSource`:
  ```kotlin
  if (bytesRead >= 252 && isPngHeader(buffer)) {
      // Discard the 252 dummy bytes and expose only byte 252 onwards to TsExtractor
  }
  ```

### 3. The `Cache-Control: no-cache` Seeking Trap
- **Never add `no-cache` to media segment responses!**
- CDN edge servers already cached the file. Adding `no-cache` in OkHttp interceptors forces ExoPlayer to bypass its in-memory/disk buffer, causing extreme stutter, re-buffering delays, and broken scrubbing during seek backward/forward.
- **Strict Solution**: Only mutate the `Content-Type: video/mp2t` header; preserve the CDN's origin `Cache-Control` header intact.

### 4. Audio Amplification & TV Volume Boost Governance
- Web rips and pirated video streams often suffer from quiet dialogue (sub-mastered audio at -18dB to -24dB LUFS).
- **CRITICAL LESSON & LAW**: **Default to Safe Linear Software Scaling via `exoPlayer.volume`** (1.0x to 2.4x).
  * Do NOT attach hardware `LoudnessEnhancer` by default. On Android TV chipsets (e.g. Amlogic S905X4 / ZTE B866V2K) and HLS multi-audio variants (`audio_tha.m3u8`), `LoudnessEnhancer` triggers native AudioFlinger rejection (`IllegalStateException`), crashes the AudioTrack, and induces infinite buffering loops.
  * **Standard Acoustic Multipliers**:
    - `100%` = 1.00x (Reference)
    - `150%` = 1.35x (+2.6 dB lift)
    - `200%` = 1.65x (+4.3 dB dialogue boost)
    - `250%` = 2.00x (+6.0 dB heavy boost)
    - `300%` = 2.40x (+7.6 dB max ceiling, preventing speaker clipping)
  * See full architectural report in `techdocs/CASE_STUDY_AUDIO_BOOST_TV_CRASH.md`.

### 5. Custom LoadControl & Buffer Tuning
```kotlin
val loadControl = DefaultLoadControl.Builder()
    .setBufferDurationsMs(
        /* minBufferMs = */ 15_000,
        /* maxBufferMs = */ 50_000,
        /* bufferForPlaybackMs = */ 2_500,
        /* bufferForPlaybackAfterRebufferMs = */ 5_000
    )
    .setPrioritizeTimeOverSizeThresholds(true)
    .build()
```

### 6. Dynamic Presigned Token Resolution & Auto-Refresh (Iron Law)
- **Bug Symptom**: Video plays perfectly today, but resuming tomorrow from Watch History or bookmarks fails with `HTTP 403 Forbidden` (`Request has expired`).
- **Root Cause**: Modern streaming CDNs (AWS S3 presigned URLs, Cloudflare R2, Javtiful CDN) issue short-lived temporary signatures (`expires=1731590000` or `X-Amz-Expires=3600`). Storing raw presigned URLs in Room/SharedPreferences turns them into dead links after 1 hour.
- **Strict Architecture**:
  1. **Canonical Content Reference**: Watch history and bookmarks must store the canonical content identifier (`contentId` or relative path `/video/xyz`), NOT the transient presigned stream URL.
  2. **Proactive Expiration Verification**:
     ```kotlin
     fun isStreamUrlExpired(url: String, bufferSeconds: Long = 300L): Boolean {
         val uri = Uri.parse(url)
         val expiresStr = uri.getQueryParameter("expires") 
             ?: uri.getQueryParameter("X-Amz-Expires") 
             ?: uri.getQueryParameter("token_expires")
         val expiresAt = expiresStr?.toLongOrNull() ?: return false
         val now = System.currentTimeMillis() / 1000L
         return now >= (expiresAt - bufferSeconds)
     }
     ```
  3. **Reactive HTTP 403 / 401 Auto-Recovery**:
     In `Player.Listener.onPlayerError(error: PlaybackException)`:
     ```kotlin
     if (error.errorCode == PlaybackException.ERROR_CODE_IO_BAD_HTTP_STATUS) {
         val currentPos = player.currentPosition
         // Fetch fresh playback ticket asynchronously
         coroutineScope.launch {
             val freshUrl = resolver.fetchFreshStreamUrl(contentId)
             player.setMediaItem(MediaItem.fromUri(freshUrl), currentPos)
             player.prepare()
             player.play()
         }
     }
     ```

### 7. Strict Fullscreen Orientation Synchronization
- When entering fullscreen mode, ExoPlayer controls must synchronize with `ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE` so that user gyro rotation between reverse-landscape and regular landscape is honored, but portrait rotation is strictly locked.
- On exit, reset orientation to `SCREEN_ORIENTATION_PORTRAIT`, then release to `SCREEN_ORIENTATION_UNSPECIFIED`. Always wire Compose `BackHandler(enabled = isFullscreen)` to collapse fullscreen first rather than exiting the activity.
