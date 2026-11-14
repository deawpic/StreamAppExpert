# 📚 OTT Media Streaming Case Study & Bug Post-Mortems
## Critical Real-World Bugs, Root-Cause Post-Mortems, and Anti-Regression Knowledge Base

This document records the critical real-world bugs discovered and resolved during the native development of the **Javidia** mobile streaming client and OTT Media3 player. It serves as an authoritative knowledge base for autonomous AI agents collaborating within the `StreamAppExpert` framework.

---

## 📑 Index of Documented Bugs & Post-Mortems

1. [Bug 1: Ephemeral Presigned CDN URLs & History Expiration (`403 Forbidden`)](#bug-1-ephemeral-presigned-cdn-urls--history-expiration-403-forbidden)
2. [Bug 2: Android 14+ (Target SDK 36) `SecurityException` on `registerReceiver`](#bug-2-android-14-target-sdk-36-securityexception-on-registerreceiver)
3. [Bug 3: Brittle Rigid Regex vs Semantic JSON Parsing & Silent Error Swallowing](#bug-3-brittle-rigid-regex-vs-semantic-json-parsing--silent-error-swallowing)
4. [Bug 4: Jetpack Compose `LazyVerticalGrid` Infinite Scroll Duplicate Key Crash](#bug-4-jetpack-compose-lazyverticalgrid-infinite-scroll-duplicate-key-crash)
5. [Bug 5: Card Cover Images Blank due to Preview Video `.mp4` Regex Capture](#bug-5-card-cover-images-blank-due-to-preview-video-mp4-regex-capture)
6. [Bug 6: Orientation Lock Toggle Failing to Restrict Physical Device Sensor Rotation](#bug-6-orientation-lock-toggle-failing-to-restrict-physical-device-sensor-rotation)
7. [Bug 7: Hardware Audio Boost TV SoC Crash & Rebuffering Loops](#bug-7-hardware-audio-boost-tv-soc-crash--rebuffering-loops)
8. [Bug 8: Compose Navigation Context & Missing `FLAG_ACTIVITY_NEW_TASK`](#bug-8-compose-navigation-context--missing-flag_activity_new_task)

---

### Bug 1: Ephemeral Presigned CDN URLs & History Expiration (`403 Forbidden`)

#### 🔴 Symptom
Users cannot resume playback from the "Continue Watching" row on the Home tab for videos watched yesterday or more than 1 hour ago. ExoPlayer fails to play or enters `STATE_IDLE` with `ERROR_CODE_IO_BAD_HTTP_STATUS (403 Forbidden)`.

#### 🔍 Root Cause
Media streaming CDNs (Cloudflare R2, AWS S3, Akamai, Javtiful) secure MP4/HLS chunks using signed temporary URLs. These URLs contain cryptographic signatures with short expiration timestamps:
- Javtiful: `expires=1794599531` (Unix epoch seconds)
- Cloudflare R2 / AWS S3: `X-Amz-Date=20261113T185211Z&X-Amz-Expires=3600` (valid for exactly 1 hour).

The application was storing the resolved ephemeral `streamUrl` into `WatchHistoryItem` in local storage (`SharedPreferences`). When accessed the next day, the presigned signature had expired by 12–24 hours, causing the CDN to immediately reject requests with `<Code>AccessDenied</Code><Message>Request has expired</Message>`.

#### ❌ Anti-Pattern (What Failed)
```kotlin
// BAD: Storing the ephemeral 1-hour presigned URL in persistent history!
fun saveCurrentWatchProgress() {
    historyManager.saveProgress(
        videoId = videoId,
        title = videoTitle,
        url = streamUrl, // ❌ STALE: Expired after 3600 seconds!
        positionMs = player.currentPosition
    )
}
```

#### ✅ Golden Solution (How It Was Fixed)
1. **Permanent Content Identity**: Always store the canonical web URL (`https://javtiful.com/video/$videoId`) in watch history and favorites—never the signed media stream URL.
2. **Dynamic Expiration Detection**: Before playing, inspect the URL using `isStreamUrlExpired(url)`.
3. **On-the-Fly Direct API Resolution**: When an expired URL or permanent video URL is received, display a quick loading spinner (*"กำลังดึงสตรีมสดใหม่ผ่าน Direct API..."*), query `POST /video/{id}/playback`, obtain fresh Cloudflare R2 302 presigned location, and seek immediately to `currentPositionMs`.
4. **Auto-Healing on Player Error**: If a token expires during long pauses, catch `onPlayerError` and automatically re-resolve a fresh URL and resume.

```kotlin
// GOOD: Store canonical URL and dynamically re-resolve on playback
private fun isStreamUrlExpired(url: String): Boolean {
    if (url.isBlank() || (url.contains("/video/") && !url.contains("/media/"))) return true
    
    // Check Javtiful signature timestamp
    val expiresMatch = Regex("""expires=(\d+)""").find(url)
    if (expiresMatch != null) {
        val expiresSec = expiresMatch.groupValues[1].toLongOrNull() ?: 0L
        if (System.currentTimeMillis() / 1000L >= (expiresSec - 120L)) return true
    }
    
    // Check AWS S3 / Cloudflare R2 presigned parameters
    val amzExpires = Regex("""X-Amz-Expires=(\d+)""").find(url)
    val amzDate = Regex("""X-Amz-Date=(\d{8}T\d{6}Z)""").find(url)
    if (amzExpires != null && amzDate != null) {
        try {
            val sdf = SimpleDateFormat("yyyyMMdd'T'HHmmss'Z'", Locale.US).apply {
                timeZone = TimeZone.getTimeZone("UTC")
            }
            val date = sdf.parse(amzDate.groupValues[1])
            if (date != null) {
                val expireTimeMs = date.time + ((amzExpires.groupValues[1].toLongOrNull() ?: 3600L) * 1000L)
                if (System.currentTimeMillis() >= (expireTimeMs - 120_000L)) return true
            }
        } catch (_: Exception) {}
    }
    return false
}
```

---

### Bug 2: Android 14+ (Target SDK 36) `SecurityException` on `registerReceiver`

#### 🔴 Symptom
Pressing "Play Now" on `DetailScreen` immediately crashed `MobilePlayerActivity` inside `onCreate()` before rendering any frame, sending the user back to the detail screen with zero visual indication.

#### 🔍 Root Cause
Starting with Android 14 (API 34) and strictly enforced in Target SDK 36 (Android 16), every context-registered `BroadcastReceiver` that is not purely for system-protected broadcasts MUST specify either `RECEIVER_EXPORTED` or `RECEIVER_NOT_EXPORTED`.
Calling `context.registerReceiver(this, filter)` for `AudioManager.ACTION_AUDIO_BECOMING_NOISY` without an explicit export flag causes Android to throw:
`java.lang.SecurityException: com.javidia.mobile: One of RECEIVER_EXPORTED or RECEIVER_NOT_EXPORTED should be specified when a receiver isn't being registered exclusively for system broadcasts`.

#### ❌ Anti-Pattern (What Failed)
```kotlin
// BAD: Crashes on Android 14+ (Target SDK 34, 35, 36) with SecurityException!
val filter = IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY)
context.registerReceiver(this, filter) // ❌ CRASH
```

#### ✅ Golden Solution (How It Was Fixed)
Use `androidx.core.content.ContextCompat.registerReceiver` with `ContextCompat.RECEIVER_NOT_EXPORTED` wrapped in a defensive `try-catch`:
```kotlin
// GOOD: Safe across all Android versions from API 26 to API 36
fun register() {
    if (!isRegistered) {
        try {
            val filter = IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY)
            ContextCompat.registerReceiver(
                context,
                this,
                filter,
                ContextCompat.RECEIVER_NOT_EXPORTED
            )
            isRegistered = true
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
```

---

### Bug 3: Brittle Rigid Regex vs Semantic JSON Parsing & Silent Error Swallowing

#### 🔴 Symptom
Tapping "Play Video" on `DetailScreen` showed a progress spinner for ~0.5 seconds, then stopped without playing and without opening the player screen.

#### 🔍 Root Cause
1. **Rigid Regex Failure**: The ticket parser used `Pattern.compile("\"playback\"\\s*:\\s*\\{\\s*\"endpoint\"\\s*:\\s*\"([^\"]+)\"\\s*,\\s*\"ticket\"\\s*:\\s*\"([^\"]+)\"\\s*\\}")`. When Javtiful changed the key order (e.g. `"ticket"` before `"endpoint"`), or added other keys inside `"playback"`, the regex returned empty strings.
2. **Silent Error Swallowing**: In `DetailScreen.kt`, the error view was conditioned on `state.error != null && state.detail == null`. When `state.detail != null`, any stream resolution error was completely ignored and never surfaced to the user.

#### ❌ Anti-Pattern (What Failed)
```kotlin
// BAD: Assumes rigid key order in JSON!
val TICKET_REGEX = Pattern.compile(
    "\"playback\"\\s*:\\s*\\{\\s*\"endpoint\"\\s*:\\s*\"([^\"]+)\"\\s*,\\s*\"ticket\"\\s*:\\s*\"([^\"]+)\"\\s*\\}"
)

// BAD: DetailScreen ignores errors when detail is already loaded!
when {
    state.isLoading -> { LoadingIndicator() }
    state.error != null && state.detail == null -> { ErrorRetryView() } // ❌ Error ignored if detail != null!
    state.detail != null -> { DetailContent() }
}
```

#### ✅ Golden Solution (How It Was Fixed)
1. **Semantic JSON Extraction**: Parse `<script id="watch-config" type="application/json">` using `org.json.JSONObject`.
2. **Multi-Tier Fallback**: Independent regex for `ticket` and `endpoint`.
3. **Auto-Construction**: If `endpoint` is blank, construct `/video/$id/playback` from the video ID.
4. **Referer Auto-Healing**: If `ticket` is blank during `resolvePlaybackStream`, fetch the referer page to parse a fresh ticket.
5. **UI Error Toast**: Add `LaunchedEffect(state.error)` to show Toast feedback even when `state.detail != null`.

---

### Bug 4: Jetpack Compose `LazyVerticalGrid` Infinite Scroll Duplicate Key Crash

#### 🔴 Symptom
When users scrolled to the bottom of the Home feed or Category detail grid, the app abruptly crashed with:
`java.lang.IllegalArgumentException: Key '115854' was already used. If you are using LazyColumn/LazyRow/LazyGrid, please ensure all items have unique keys.`

#### 🔍 Root Cause
Pagination endpoints (`/foryou?page=1`, `/foryou?page=2`) on video portals frequently contain overlapping videos due to newly published items shifting pagination boundaries. When combining pages `videos + newPageVideos`, duplicate video IDs were passed into `items(items = videos, key = { it.id })`.

#### ❌ Anti-Pattern (What Failed)
```kotlin
// BAD: Duplicate items across pages cause fatal Compose crash!
LazyVerticalGrid(columns = GridCells.Fixed(2)) {
    items(items = videos, key = { it.id }) { video -> // ❌ CRASH on duplicate it.id
        VideoCard(video)
    }
}
```

#### ✅ Golden Solution (How It Was Fixed)
1. **Deduplication in ViewModel**:
   ```kotlin
   val combined = (_uiState.value.videos + newVideos).distinctBy { it.id }
   _uiState.update { it.copy(videos = combined) }
   ```
2. **Compound Unique Keys in Grid**:
   ```kotlin
   items(
       count = videos.size,
       key = { index -> "${videos[index].id}_$index" } // ✅ 100% unique key guarantee
   ) { index ->
       VideoCard(videos[index])
   }
   ```

---

### Bug 5: Card Cover Images Blank due to Preview Video `.mp4` Regex Capture

#### 🔴 Symptom
Video cards showed placeholder rabbit icons or blank grey boxes instead of real poster images.

#### 🔍 Root Cause
Javtiful video cards include preview video URLs in attributes:
`<article class="video-card" data-front-video-preview-src="https://.../preview.mp4">`
The scraper's image regex matched attributes indiscriminately, capturing `https://.../preview.mp4` as the poster URL. Coil (an image loader) could not decode `.mp4` files as static bitmaps and fell back to the error placeholder.

#### ❌ Anti-Pattern (What Failed)
```kotlin
// BAD: Matches .mp4 preview links as image URLs!
val srcMatch = Pattern.compile("""\bsrc=["']([^"']+)["']""").matcher(articleHtml)
```

#### ✅ Golden Solution (How It Was Fixed)
Strictly isolate `<img>` tags, prioritize `data-front-lazy-src`, and explicitly filter out any string ending in `.mp4` or containing `placeholder`:
```kotlin
// GOOD: Strictly isolated image tags without video preview contamination
val imgTagMatch = Pattern.compile("""<img[^>]+>""").matcher(articleHtml)
if (imgTagMatch.find()) {
    val tag = imgTagMatch.group(0) ?: ""
    val lazyMatch = Pattern.compile("""data-front-lazy-src=["']([^"']+)["']""").matcher(tag)
    val srcMatch = Pattern.compile("""\bsrc=["']([^"']+)["']""").matcher(tag)
    val candidate = lazyMatch.find() ?: srcMatch.find() ...
    if (candidate.isNotBlank() && !candidate.endsWith(".mp4", ignoreCase = true) && !candidate.contains("placeholder")) {
        poster = absoluteUrl(candidate)
    }
}
```

---

### Bug 6: Orientation Lock Toggle Failing to Restrict Physical Device Sensor Rotation

#### 🔴 Symptom
When users tapped the padlock lock button or fullscreen toggle, the device would still auto-rotate back to portrait when the phone was held vertically or laid down in bed.

#### 🔍 Root Cause
The padlock toggle only modified Compose state (`isLocked = true`) which hid gesture detection, but never notified the Android Window Manager via `Activity.requestedOrientation`.

#### ✅ Golden Solution (How It Was Fixed)
1. **Strict Landscape Mode**:
   ```kotlin
   fun enterFullscreenLandscape() {
       isFullscreenLandscapeState.value = true
       requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
   }
   ```
   `SCREEN_ORIENTATION_SENSOR_LANDSCAPE` allows 90° and 270° landscape tilts, but **completely locks out portrait orientations** until the user explicitly taps shrink/exit or Back.
2. **Clean Collapse to Portrait**:
   ```kotlin
   fun exitFullscreenLandscape() {
       isFullscreenLandscapeState.value = false
       requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
       window.decorView.postDelayed({
           if (!isDestroyed && !isFinishing) {
               requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
           }
       }, 500L)
   }
   ```
3. **Dedicated HUD Button & Back Handler**:
   - Bottom-right corner button with 48×48 dp touch target.
   - `BackHandler` collapses landscape fullscreen back to portrait first before exiting the activity.

---

### Bug 7: Hardware Audio Boost TV SoC Crash & Rebuffering Loops

#### 🔴 Symptom
On Android TV boxes (Amlogic S905X4, ZTE B866V2K) and multi-audio HLS streams, enabling audio boost caused `IllegalStateException`, `ERROR_CODE_AUDIO_TRACK_WRITE_FAILED`, and infinite rebuffering.

#### 🔍 Root Cause
Native AudioFlinger and hardware DSPs on low-cost TV chipsets reject hardware `AudioEffect` (`LoudnessEnhancer`) on passthrough, AC3, or HLS multi-track streams.

#### ❌ Anti-Pattern (What Failed)
```kotlin
// BAD: Hardware LoudnessEnhancer crashes TV DSP AudioFlinger!
val enhancer = LoudnessEnhancer(player.audioSessionId)
enhancer.setTargetGain(1500) // ❌ CRASH on TV SoCs
```

#### ✅ Golden Solution (How It Was Fixed)
Enforce **Linear Software Volume Scaling directly via `exoPlayer.volume = multiplier`** (1.0x to 2.4x). Software volume scaling is 100% stable across all Android TV, Mobile, and Tablet chipsets.

---

### Bug 8: Compose Navigation Context & Missing `FLAG_ACTIVITY_NEW_TASK`

#### 🔴 Symptom
Calling `MobilePlayerActivity.start(context, ...)` from certain Jetpack Compose composables threw:
`android.util.AndroidRuntimeException: Calling startActivity() from outside of an Activity context requires the FLAG_ACTIVITY_NEW_TASK flag.`

#### 🔍 Root Cause
`LocalContext.current` inside deeply nested composables or subgraphs can occasionally resolve to an `Application` context or wrapped `ContextThemeWrapper` rather than direct `Activity`.

#### ✅ Golden Solution (How It Was Fixed)
Always add `Intent.FLAG_ACTIVITY_NEW_TASK` in activity launch helper methods:
```kotlin
fun start(context: Context, streamUrl: String, title: String, videoId: String, posterUrl: String, startPositionMs: Long = 0L) {
    val intent = Intent(context, MobilePlayerActivity::class.java).apply {
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK) // ✅ Prevents AndroidRuntimeException
        putExtra(EXTRA_STREAM_URL, streamUrl)
        putExtra(EXTRA_TITLE, title)
        putExtra(EXTRA_VIDEO_ID, videoId)
        putExtra(EXTRA_POSTER_URL, posterUrl)
        putExtra(EXTRA_START_POSITION, startPositionMs)
    }
    context.startActivity(intent)
}
```

---

### Bug 9: Audio Playing with Black Screen & Stuck Direct API Spinner (Compose Race Condition)

#### 🔴 Symptom
When opening a video from Watch History, audio plays clearly through the speakers, but the screen stays 100% black with the Direct API loading spinner (`CircularProgressIndicator`) spinning indefinitely in the center.

#### 🔍 Root Cause
1. **Screen Swapping Anti-Pattern**: The UI conditionally swapped `PlayerScreen` out with a loading Box:
   ```kotlin
   if (isResolving || player == null) {
       Box(...) // Fullscreen black box with spinner
   } else {
       PlayerScreen(...)
   }
   ```
   When `PlayerScreen` is not in the composition tree, `AndroidView(PlayerView)` is unmounted and has no `SurfaceView` attached to the window.
2. **State Notification Race Condition**: `isResolvingStreamState.value = false` was called *before* `exoPlayer` was initialized, causing Compose to recompose while `player` was still `null`. Because `exoPlayer` was a plain non-State JVM property (`var exoPlayer: ExoPlayer? = null`), subsequent assignment to `exoPlayer` did NOT trigger recomposition, stranding Compose in the loading spinner branch while ExoPlayer played audio in the background.

#### ✅ Golden Solution (How It Was Fixed)
1. **Always Mount `PlayerScreen`**: Build and bind `ExoPlayer` in `onCreate()` before calling `setContent()`. `PlayerScreen` and `AndroidView(PlayerView)` remain permanently mounted in the Compose hierarchy.
2. **Overlay Pattern Instead of Screen Swapping**: Render the Direct API loading spinner as a semi-transparent overlay *on top* of `PlayerView` rather than unmounting the player.
3. **Bind Surface in Both Factory and Update**: Ensure `playerView.player = player` is present in both `factory` and `update` blocks of `AndroidView`.

---

## 🛡️ Summary of Non-Negotiable Directives for Agents

| Rule | Area | Requirement |
|---|---|---|
| **No Stale Presigned URLs** | Media3 / Storage | Store canonical `/video/$id` in History; always resolve fresh presigned tokens dynamically |
| **Android 14+ Receiver Security** | Mobile OS | Use `ContextCompat.registerReceiver(..., RECEIVER_NOT_EXPORTED)` |
| **Strict Landscape Lock** | Video Player | Use `SCREEN_ORIENTATION_SENSOR_LANDSCAPE` for full screen mode |
| **Compose Key Deduplication** | Jetpack Compose | Apply `.distinctBy { it.id }` and compound keys `"${item.id}_$index"` |
| **Semantic JSON Over Regex** | Reverse Eng. | Extract config JSON via `JSONObject` before using regex fallbacks |
| **Safe Software Audio Boost** | Audio Engineering | Use `exoPlayer.volume = multiplier`; avoid hardware `LoudnessEnhancer` |
| **Always Mount Player Surface** | Compose / Media3 | Keep `PlayerView` mounted; render loading indicators as overlays, never unmounting player |
| **Deterministic Verification** | QA / Engineering | All code must pass bracket balancing and AST validation exit code 0 |
