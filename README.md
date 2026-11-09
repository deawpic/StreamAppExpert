# 🎬 StreamAppExpert
### Autonomous Deterministic Multi-Agent Harness for OTT, Media3, Android TV & Mobile Streaming Applications

`StreamAppExpert` is an advanced multi-agent development harness and engineering framework crafted specifically for building, maintaining, and scaling video streaming applications.

It synthesizes real-world empirical production insights, bug fixes, and architectural patterns gained across Android TV (Leanback), Android Mobile (Jetpack Compose Material 3), Media3 ExoPlayer, web scraping/reverse engineering, and FastAPI streaming backends.

---

## 🌟 Key Capabilities & Empirical Solutions Synthesized

### 1. 🎬 Media3 ExoPlayer Core
- **The NAL Type 9 AUD Video Freeze Solution**:
  Eliminates the bug where video freezes on the first frame while audio continues playing. Caused by passing `FLAG_DETECT_ACCESS_UNITS` to `DefaultHlsExtractorFactory` on streams encoded with NAL Type 9 delimiters (e.g. TikTok CDN ImageX). Fixed by standardizing on `DefaultHlsExtractorFactory()` with `flags = 0`.
- **Masked TS Stream Unmasking (`MaskedTsDataSource`)**:
  Transparently unmasks video chunks disguised as images (`.image`, `.png`). Identifies the 8-byte PNG signature, discards the **252-byte dummy PNG prefix**, and extracts the MPEG-TS transport stream starting at byte 252 (sync byte `0x47`, PAT PID 0).
- **The `Cache-Control: no-cache` Seeking Trap**:
  Prevents seeking/scrubbing stutter and buffering stalls. Never injects `no-cache` on media segments in OkHttp interceptors; preserves the origin CDN's `max-age=31536000` so ExoPlayer can scrub seamlessly from local buffer cache.
- **Hardware Loudness Enhancement (`SoundBoostManager`)**:
  Replaces distortion-prone software volume multipliers with Android's native hardware `LoudnessEnhancer(player.audioSessionId)`, safely boosting dialogue loudness from +2.5dB up to +12dB.
- **Buffer & LoadControl Tuning**:
  Custom `DefaultLoadControl` configured for high-bitrate OTT streaming (15s min buffer, 50s max buffer, 2.5s playback threshold).

### 2. 📱 Android Mobile (Touch-First Jetpack Compose & Target SDK 36)
- **Target SDK 36 (Android 16 Baklava)** with `minSdk = 26` (Android 8.0 Oreo).
- **VLC / MX Player Touch Gestures**:
  * Left-vertical swipe: Screen brightness adjustment (`WindowManager.LayoutParams.screenBrightness`).
  * Right-vertical swipe: Media audio volume adjustment (`AudioManager.STREAM_MUSIC`).
  * Horizontal swipe: Timeline scrubbing preview with target seek time.
  * Double-tap left/right: Instant ±10s seek with animated visual ripple pills.
  * Screen Lock: Locks all gesture and HUD listeners to prevent palm mis-touches.
- **Picture-in-Picture (PiP) Engine**:
  * Android 12+ (API 31+): Seamless home gesture auto-enter via `setAutoEnterEnabled(true)`.
  * API 26-30 fallback via `enterPictureInPictureMode(params)`.
  * Automatic control bar and chrome suppression in PiP mode.
- **Hardware Guards**:
  * `ACTION_AUDIO_BECOMING_NOISY`: Auto-pauses playback when headphones or Bluetooth audio disconnects.
  * Cutout Insets: Safe rendering avoiding camera notch obstruction (`WindowInsets.displayCutout`).
- **Touch-First Compliance**: Minimum 48×48 dp interactive touch targets; strict ban on Leanback dependencies in mobile.

### 3. 📺 Android TV (Leanback & D-pad UX)
- **Video Surface Binding (The Black Screen Bug Fix)**:
  Subclasses `VideoSupportFragment` with `VideoSupportFragmentGlueHost(this)` (implementing `SurfaceHolderGlueHost`) and explicitly binds `surfaceView` to ExoPlayer, preventing the common "audio plays, but screen is black" Leanback defect.
- **D-pad Focus Navigation**:
  Ensures every card, button, and row is D-pad focusable with visible 1.1x scaling and focus rings. Handles DPAD and media key codes (`PLAY_PAUSE`, `FAST_FORWARD`, `REWIND`).
- **10-Foot UI Ergonomics**: Overscan safe zones and legible typography (subtitles 20sp, titles 24-28sp).

### 4. 🕵️ Scraper & Reverse Engineering Pipeline
- **2-Step Tokenplay Extraction**:
  * Step 1: POST to gateway player AJAX (`admin-ajax.php`) -> extract iframe MD5 embed hash.
  * Step 2: POST MD5 and parent domain to `/api/tokenplay` -> extract signed `stream_id`, `token`, `expires`, and `session_id`.
  * Step 3: Assemble direct tokenized `.m3u8` master playlist.
- **Anti-Bot Mitigation**: Header rotation, User-Agent spoofing, and persistent in-memory cookie jars.

### 5. 🛡️ Build Governance & Ultra-Lean APKs
- **Zero Gradle Debug Builds**: Autonomous execution of `./gradlew assembleDebug` is strictly forbidden. The developer builds in Android Studio.
- **Sideloading-Friendly Release Build**: Release build signed with debug key (`signingConfig = signingConfigs.getByName("debug")`) for zero-friction installation on TV boxes and phones.
- **Minimal APK Size**: R8 fullMode, ProGuard rules, `isMinifyEnabled = true`, `isShrinkResources = true`, and resource language filtering (`resConfigs("th", "en")`) keeping APKs under 12MB.

### 6. ⚙️ Deterministic Multi-Agent State Machine & Call-Stack
- **Persistent Call-Stack (`stack.json`)**: Hierarchical task frames, parent-child links, and atomic state saving.
- **Hyper-Disciplined Stack Hygiene**: Deterministic boundary enforcement rejecting modifications outside `allowed_files`.
- **Atomic Decomposition**: Enforces `< 200` line modifications per task frame.
- **Mandatory Verification before Pop**: Fast ground-truth AST/syntax checking (Python, Kotlin, XML, Gradle) and streaming domain compliance before state transitions.
- **Prompt-on-Demand (JIT)**: Assembles zero-bloat, token-optimized prompts with skill templates and git unified diffs.
- **Domain-Specific Streaming Linter (`streaming-lint`)**: Scans code for streaming anti-patterns (e.g. `FLAG_DETECT_ACCESS_UNITS`, `no-cache` insertion, missing `VideoSupportFragment`).

---

## 📁 Repository Directory Structure

```text
StreamAppExpert/
├── .agents/
│   └── skills/
│       ├── stream-player-media3/         # Media3 ExoPlayer, Unmasking, Surface, Audio Boost
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── CDN_UNMASKING.md
│       │       ├── SURFACE_BINDING.md
│       │       └── AUDIO_BOOST.md
│       ├── stream-android-mobile/        # Compose M3, Gestures, PiP, Hardware Guards
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── GESTURE_CONTROLS.md
│       │       ├── PIP_ENGINE.md
│       │       └── HARDWARE_GUARDS.md
│       ├── stream-android-tv/            # Leanback, D-pad Navigation, 10-foot UI
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── LEANBACK_VIDEO_SURFACE.md
│       │       └── DPAD_FOCUS_ENGINE.md
│       ├── stream-reverse-engineer/      # 2-step Tokenplay, DOM Scraper, Anti-Bot
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── TOKENPLAY_M3U8_RESOLUTION.md
│       │       └── BOT_MITIGATION_BYPASS.md
│       ├── stream-backend-gateway/       # FastAPI Gateway, Proxy, M3U8 Rewriter
│       │   └── SKILL.md
│       ├── anti-hallucination-guardian/  # Zero-Test Policy, Ground Truth Verification
│       │   └── SKILL.md
│       ├── software-architecture/        # OTT Architecture, Mermaid Blueprints
│       │   └── SKILL.md
│       ├── qa-automation/                # Static Checks, AST Linters, Build Guards
│       │   └── SKILL.md
│       ├── android-jetpack-compose-expert/# Compose M3, 48dp Targets, PlayerView Binding
│       │   └── SKILL.md
│       ├── kotlin-coroutines-expert/     # StateFlow Player States, Resilient Scraping
│       │   └── SKILL.md
│       ├── apk-reverse/                  # Decompilation with jadx, Endpoint Discovery
│       │   └── SKILL.md
│       ├── protocol-reverse-engineering/ # HLS/DASH Traffic Sniffing, Handshake Analysis
│       │   └── SKILL.md
│       ├── mobile-design/                # Cinematic Dark Theme (#0A0D14), Player HUD
│       │   └── SKILL.md
│       ├── python-fastapi-development/   # Streaming Proxy, Chunk Streaming, M3U8 Rewrite
│       │   └── SKILL.md
│       ├── redis/                        # Token Expiration TTL, Series Metadata Cache
│       │   └── SKILL.md
│       ├── web-scraper/                  # DOM-First + Regex Fallback Extraction
│       │   └── SKILL.md
│       ├── android-dev/                  # Ultra-Lean APK (<12MB), Debug Key Sideloading
│       │   └── SKILL.md
│       └── code-review-sensei/           # 5-Point Review catching Streaming Regressions
│           └── SKILL.md
├── harness/
│   ├── __init__.py
│   ├── schemas.py                        # TaskFrame, StructuredOutput, Domains, Receipts
│   ├── task_stack.py                     # Atomic stack.json manager
│   ├── state_machine.py                  # Deterministic FSM, handoffs, circuit breaker
│   ├── prompt_builder.py                 # JIT context assembler with skills & diff
│   ├── verifier.py                       # Ground-truth AST, syntax, boundary & blast radius
│   ├── streaming_rules.py                # Specialized streaming anti-regression engine
│   ├── sanitizer.py                      # JSON repair, extreme brevity trimmer, fluff stripping
│   ├── git_diff.py                       # Unified git diff token saver
│   └── cli.py                            # Harness CLI
├── techdocs/
│   ├── STREAMING_PLAYBOOK.md             # Comprehensive handbook of all solved streaming issues
│   ├── ARCHITECTURE_BLUEPRINT.md         # Mobile vs TV vs Scraper vs Gateway architecture
│   └── APK_OPTIMIZATION_GUIDE.md         # Minimal APK, R8, ProGuard, debug key signing
├── AGENTS.md                             # Multi-Agent governance rules & role profiles
├── README.md                             # Master documentation (this file)
├── setup.py                              # Python packaging
├── harness.bat                           # Windows batch launcher
└── harness.ps1                           # Windows PowerShell launcher
```

---

## 🚀 Quick Start & CLI Usage

You can invoke the harness using `python -m harness.cli`, `.\harness.bat`, or `.\harness.ps1`.

### 1. Run Doctor Diagnostics
Check system environment, Git repository, and skills catalog:
```powershell
.\harness.bat doctor
```

### 2. Initialize a Streaming Task
Push a new root streaming task onto the call-stack:
```powershell
.\harness.bat init `
  --task-id "STREAM-001" `
  --title "Implement MaskedTsDataSource for Disguised CDN Segments" `
  --domain exoplayer `
  --agent stream_player_agent `
  --allowed-files app/src/main/java/com/streamapp/player/MaskedTsDataSource.kt `
  --max-lines 150
```

### 3. Check System Status & Top of Stack
```powershell
.\harness.bat status
```

### 4. Build JIT Token-Optimized Prompt on Demand
Generate the exact, grounded prompt for the current agent:
```powershell
.\harness.bat build-prompt
```

### 5. Run Ground-Truth Verification
Verify physical artifacts, syntax, and boundaries:
```powershell
.\harness.bat verify
```

### 6. Run Streaming Anti-Pattern Linting
Scan modified or repository files for known streaming bugs (e.g., `FLAG_DETECT_ACCESS_UNITS`, `no-cache`, black screen patterns):
```powershell
.\harness.bat streaming-lint
```

### 7. Step Deterministic State Transition
Advance the state machine using agent structured output:
```powershell
.\harness.bat transition --input '{"action": "complete", "status": "completed", "summary": "Implemented MaskedTsDataSource with 252-byte prefix discard.", "artifacts": ["app/src/main/java/com/streamapp/player/MaskedTsDataSource.kt"]}'
```

---

## 👥 Multi-Agent Team Directory

| Agent Name | Role | Primary Focus |
|---|---|---|
| `stream_pm_agent` | Product Manager | User stories, touch flows, OTT requirement definitions |
| `stream_architect_agent` | Software Architect | System design, Mermaid diagrams, clean architecture |
| `stream_player_agent` | Media3 ExoPlayer Specialist | HLS unmasking, SurfaceView, LoudnessEnhancer, LoadControl |
| `stream_mobile_agent` | Android Mobile Developer | Jetpack Compose M3, VLC/MX gestures, Screen Lock, PiP, SDK 36 |
| `stream_tv_agent` | Android TV Developer | Leanback UI, D-pad navigation, 10-foot ergonomics |
| `stream_scraper_agent` | Reverse Engineer / Scraper | 2-step tokenplay extraction, cookie jar, anti-bot bypass |
| `stream_backend_agent` | Backend Gateway Engineer | FastAPI streaming proxy, Redis caching, M3U8 rewrite |
| `stream_reviewer_agent` | Code Reviewer | Static review, boundary enforcement, anti-hallucination |
| `stream_qa_agent` | QA & Gatekeeper | AST verification, streaming lint compliance, build guard |

---

## 📄 License & Attribution
Crafted with pride by the Google DeepMind Antigravity Team for production-grade video streaming application engineering.
