# 🏗️ StreamAppExpert Architecture Blueprint
## High-Performance Streaming Platform Architecture

```mermaid
flowchart TD
    subgraph Data & Resolver Core [100% Shared Logic]
        MODELS["Data Models\nSeriesItem, EpisodeItem, StreamResponse, WatchHistory"]
        RESOLVER["Stream Resolvers\nNativeScraper + 2-Step Tokenplay Extractor"]
        UNMASK["Media3 Unmasker\nMaskedTsDataSource + HlsFakeImageInterceptor\n(252-byte PNG dummy prefix discard)"]
        AUDIO_BOOST["Hardware SoundBoost\nLoudnessEnhancer DSP (+2.5dB to +12dB)"]
        PERSIST["Local Storage\nWatchHistoryManager & Favorites (Zero-Migration JSON)"]
    end

    subgraph Client Layer: Android TV [Leanback 10-Foot Experience]
        TV_LEANBACK["Leanback Presenters\nBrowseSupportFragment & DetailsSupportFragment"]
        TV_PLAYER["TvPlaybackFragment\nextends VideoSupportFragment (SurfaceHolderGlueHost)"]
        TV_DPAD["D-pad Focus Navigation & Key Interceptors"]
    end

    subgraph Client Layer: Android Mobile [Touch-First Compose SDK 36]
        M3_COMPOSE["Jetpack Compose Material 3\nScaffold, BottomNavBar, LazyVerticalGrid"]
        TOUCH_PLAYER["Dual-Mode Player\nPortrait Split + Fullscreen Landscape"]
        GESTURES["VLC/MX Player Gestures\nBrightness, Volume, Scrubbing, Double-Tap +/-10s"]
        PIP["Picture-in-Picture Engine\nAPI 31+ setAutoEnterEnabled(true)"]
        GUARDS["Hardware Protections\nBecoming Noisy & Cutout Safe Insets"]
    end

    subgraph Backend Layer [FastAPI Fallback & Reverse Proxy]
        API["FastAPI REST API\nAsync HTTPX + Redis Caching"]
        M3U8_PROXY["M3U8 Proxy & TS Stream Rewriter"]
    end

    RESOLVER --> UNMASK
    UNMASK --> TV_PLAYER
    UNMASK --> TOUCH_PLAYER
    AUDIO_BOOST --> TV_PLAYER
    AUDIO_BOOST --> TOUCH_PLAYER
    PERSIST --> TV_LEANBACK
    PERSIST --> M3_COMPOSE
    API --> RESOLVER
```

---

## Shared vs Platform-Specific Separation Matrix

| Component | Android TV (`android/`) | Android Mobile (`android-mobile/`) | Backend Gateway (`backend/`) |
|---|---|---|---|
| **UI Framework** | AndroidX Leanback XML | Jetpack Compose Material 3 | FastAPI / Jinja2 (optional) |
| **Input System** | D-pad Remote DPAD Focus | Multi-touch Gestures & Tap | REST JSON API |
| **Video Surface** | `VideoSupportFragment` | `AndroidView(PlayerView)` | N/A |
| **Stream Engine** | Media3 ExoPlayer | Media3 ExoPlayer | HLS Reverse Proxy |
| **Unmasking** | `MaskedTsDataSource` | `MaskedTsDataSource` | M3U8 Rewriter |
| **Audio Boost** | `SoundBoostManager` | `SoundBoostManager` | N/A |
| **Target SDK** | 34-36 (TV) | 36 (Mobile Baklava) | Python 3.12+ |
| **Min SDK** | 21 (TV Android 5.0) | 26 (Mobile Android 8.0 Oreo) | N/A |
