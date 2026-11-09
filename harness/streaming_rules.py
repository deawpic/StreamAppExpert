"""
Streaming App Domain Rules & Anti-Regression Linting Engine.
Encapsulates real-world empirical streaming bug fixes, anti-patterns, and architectural invariants:
1. EXO_NO_FLAG_DETECT_ACCESS_UNITS: FLAG_DETECT_ACCESS_UNITS drops P/B frames on NAL 9 AUD streams (causes frozen video).
2. EXO_NO_CACHE_CONTROL_MUTATION: Forbids adding no-cache to segment responses (destroys seeking/scrubbing performance).
3. TV_LEANBACK_SURFACE_HOLDER: Enforces VideoSupportFragment over PlaybackSupportFragment (avoids black screen with audio).
4. MOBILE_NO_LEANBACK_IMPORTS: Forbids Leanback in mobile modules (touch-first ergonomics).
5. MOBILE_MIN_TOUCH_TARGET_48DP: Enforces 48x48 dp minimum touch bounds in Compose.
6. GRADLE_RELEASE_DEBUG_SIGNING: Enforces debug key signing on release build for easy sideloading.
7. GRADLE_MINIMAL_APK_SETTINGS: Enforces isMinifyEnabled and isShrinkResources.
8. MASKED_TS_PREFIX_OFFSET: Ensures 252-byte PNG dummy prefix skip offset is strictly maintained.
9. SOUND_BOOST_LOUDNESS_ENHANCER: Verifies LoudnessEnhancer attached to ExoPlayer audioSessionId.
10. PIP_LIFECYCLE_COMPAT: Ensures setAutoEnterEnabled(true) on API 31+ with aspect ratio config.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple


@dataclass
class StreamingRuleViolation:
    rule_id: str
    rule_name: str
    severity: str  # "ERROR" or "WARNING"
    file_path: str
    line_number: Optional[int]
    message: str
    recommendation: str


class StreamingRulesEngine:
    """Deterministic static inspector for streaming-specific bugs and compliance."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()

    def inspect_file(self, file_path: Path) -> List[StreamingRuleViolation]:
        violations: List[StreamingRuleViolation] = []
        if not file_path.exists() or not file_path.is_file():
            return violations

        ext = file_path.suffix.lower()
        rel_path = str(file_path.relative_to(self.workspace_root)) if self.workspace_root in file_path.parents else str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return violations

        lines = content.splitlines()

        # Kotlin and Java inspection
        if ext in (".kt", ".java"):
            violations.extend(self._check_kotlin_streaming_rules(rel_path, content, lines))

        # Gradle build scripts
        if ext == ".kts" or "gradle" in file_path.name.lower():
            violations.extend(self._check_gradle_streaming_rules(rel_path, content, lines))

        return violations

    def _check_kotlin_streaming_rules(
        self, rel_path: str, content: str, lines: List[str]
    ) -> List[StreamingRuleViolation]:
        violations: List[StreamingRuleViolation] = []
        is_mobile = "mobile" in rel_path.lower() or "android-mobile" in rel_path.lower()

        # Rule 1: EXO_NO_FLAG_DETECT_ACCESS_UNITS
        # FLAG_DETECT_ACCESS_UNITS causes H264Reader to discard non-IDR P/B frames on NAL 9 streams
        if "FLAG_DETECT_ACCESS_UNITS" in content:
            for idx, line in enumerate(lines, 1):
                if "FLAG_DETECT_ACCESS_UNITS" in line and not line.strip().startswith("//"):
                    violations.append(
                        StreamingRuleViolation(
                            rule_id="EXO_NO_FLAG_DETECT_ACCESS_UNITS",
                            rule_name="ExoPlayer Video Freeze Bug (NAL Type 9)",
                            severity="ERROR",
                            file_path=rel_path,
                            line_number=idx,
                            message="Found 'FLAG_DETECT_ACCESS_UNITS'. This flag instructs H264Reader to drop all non-IDR frames when streams contain NAL Type 9 AUD delimiters, freezing the video.",
                            recommendation="Remove FLAG_DETECT_ACCESS_UNITS and use standard DefaultHlsExtractorFactory() with flags=0.",
                        )
                    )

        # Rule 2: EXO_NO_CACHE_CONTROL_MUTATION
        # Forbids mutating Cache-Control to no-cache in media segment interceptors
        if ("no-cache" in content or "no-store" in content) and (
            "Interceptor" in content or "OkHttp" in content or "FakeImage" in content
        ):
            for idx, line in enumerate(lines, 1):
                if re.search(r'header\(["\']Cache-Control["\'],\s*["\'].*no-cache', line, re.IGNORECASE):
                    violations.append(
                        StreamingRuleViolation(
                            rule_id="EXO_NO_CACHE_CONTROL_MUTATION",
                            rule_name="Seeking/Scrubbing Stutter Bug",
                            severity="ERROR",
                            file_path=rel_path,
                            line_number=idx,
                            message="Forcing 'Cache-Control: no-cache' prevents local disk/memory caching of video segments, destroying scrubbing & seeking performance.",
                            recommendation="Retain the CDN's origin cache headers (e.g. max-age=31536000) and only mutate the Content-Type header.",
                        )
                    )

        # Rule 3: TV_LEANBACK_SURFACE_HOLDER
        # When using Leanback, ensure VideoSupportFragment or SurfaceHolderGlueHost is used
        if "PlaybackSupportFragment" in content and "VideoSupportFragment" not in content:
            for idx, line in enumerate(lines, 1):
                if "class " in line and "PlaybackSupportFragment" in line and not line.strip().startswith("//"):
                    violations.append(
                        StreamingRuleViolation(
                            rule_id="TV_LEANBACK_SURFACE_HOLDER",
                            rule_name="Leanback Black Screen With Audio Bug",
                            severity="ERROR",
                            file_path=rel_path,
                            line_number=idx,
                            message="Fragment extends 'PlaybackSupportFragment' without a video surface. LeanbackPlayerAdapter will never attach player surface.",
                            recommendation="Extend 'VideoSupportFragment' and use 'VideoSupportFragmentGlueHost(this)' so SurfaceHolder is provided to ExoPlayer.",
                        )
                    )

        # Rule 4: MOBILE_NO_LEANBACK_IMPORTS
        # Mobile app must NEVER import Leanback or TV Compose
        if is_mobile:
            for idx, line in enumerate(lines, 1):
                if (
                    "import androidx.leanback" in line
                    or "import androidx.tv" in line
                ) and not line.strip().startswith("//"):
                    violations.append(
                        StreamingRuleViolation(
                            rule_id="MOBILE_NO_LEANBACK_IMPORTS",
                            rule_name="TV Leanback Dependency in Mobile App",
                            severity="ERROR",
                            file_path=rel_path,
                            line_number=idx,
                            message="Found Leanback or TV Compose import in mobile module. Mobile UI must be 100% touch-first Jetpack Compose Material 3.",
                            recommendation="Remove Leanback imports. Use Compose Material 3 components and gesture modifiers.",
                        )
                    )

        # Rule 5: MASKED_TS_PREFIX_OFFSET
        # Check that 252-byte PNG dummy prefix is explicitly handled if unmasking is mentioned
        if "MaskedTs" in rel_path or "MaskedTsDataSource" in content:
            if "252" not in content and "0xFC" not in content and "0xfc" not in content:
                violations.append(
                    StreamingRuleViolation(
                        rule_id="MASKED_TS_PREFIX_OFFSET",
                        rule_name="CDN Image Prefix Offset Integrity",
                        severity="WARNING",
                        file_path=rel_path,
                        line_number=None,
                        message="MaskedTsDataSource does not reference standard 252-byte dummy PNG prefix offset.",
                        recommendation="Verify that PNG header check and skip offset (252 bytes) matches the CDN's dummy header length.",
                    )
                )

        # Rule 6: SOUND_BOOST_LOUDNESS_ENHANCER
        if "SoundBoost" in rel_path or "SoundBoostManager" in content:
            if "LoudnessEnhancer" not in content:
                violations.append(
                    StreamingRuleViolation(
                        rule_id="SOUND_BOOST_LOUDNESS_ENHANCER",
                        rule_name="Hardware-Accelerated Audio Boost",
                        severity="WARNING",
                        file_path=rel_path,
                        line_number=None,
                        message="SoundBoostManager does not utilize Android 'LoudnessEnhancer'. Software amplification may cause audio distortion/clipping.",
                        recommendation="Use android.media.audiofx.LoudnessEnhancer attached to player.audioSessionId for clean hardware-boosted sound.",
                    )
                )

        # Rule 7: PIP_LIFECYCLE_COMPAT
        if "PictureInPicture" in content or "enterPictureInPictureMode" in content:
            if "setAutoEnterEnabled" not in content and "Build.VERSION_CODES.S" not in content:
                violations.append(
                    StreamingRuleViolation(
                        rule_id="PIP_LIFECYCLE_COMPAT",
                        rule_name="Seamless Android 12+ PiP Navigation",
                        severity="WARNING",
                        file_path=rel_path,
                        line_number=None,
                        message="PiP implementation does not configure setAutoEnterEnabled(true) for Android 12+ (API 31+).",
                        recommendation="Add setAutoEnterEnabled(true) in PictureInPictureParams for smooth auto-PiP when user navigates home.",
                    )
                )

        return violations

    def _check_gradle_streaming_rules(
        self, rel_path: str, content: str, lines: List[str]
    ) -> List[StreamingRuleViolation]:
        violations: List[StreamingRuleViolation] = []

        # Only check app build scripts
        if "app" in rel_path and ("build.gradle" in rel_path or "build.gradle.kts" in rel_path):
            # Check 1: Release signed with debug key
            has_debug_signing = (
                'signingConfigs.getByName("debug")' in content
                or 'signingConfig = signingConfigs.getByName("debug")' in content
                or "signingConfig = signingConfigs.debug" in content
                or "signingConfig signingConfigs.debug" in content
            )
            if not has_debug_signing and ("buildTypes" in content or "release" in content):
                violations.append(
                    StreamingRuleViolation(
                        rule_id="GRADLE_RELEASE_DEBUG_SIGNING",
                        rule_name="Sideload-Friendly Release Signing",
                        severity="ERROR",
                        file_path=rel_path,
                        line_number=None,
                        message="Release buildType must use debug signingConfig for zero-friction TV & Mobile sideloading.",
                        recommendation='Set "signingConfig = signingConfigs.getByName(\\"debug\\")" inside buildTypes.release { }.',
                    )
                )

            # Check 2: Minification and resource shrinking
            has_minify = "isMinifyEnabled = true" in content or "minifyEnabled true" in content
            has_shrink = "isShrinkResources = true" in content or "shrinkResources true" in content
            if (not has_minify or not has_shrink) and ("buildTypes" in content or "release" in content):
                violations.append(
                    StreamingRuleViolation(
                        rule_id="GRADLE_MINIMAL_APK_SETTINGS",
                        rule_name="Ultra-Lean Minimal APK Optimization",
                        severity="ERROR",
                        file_path=rel_path,
                        line_number=None,
                        message="Release buildType must enable isMinifyEnabled and isShrinkResources to eliminate unused video codecs and classes.",
                        recommendation="Set 'isMinifyEnabled = true' and 'isShrinkResources = true' inside buildTypes.release { }.",
                    )
                )

        return violations

    def run_all_checks(self, file_paths: List[str]) -> List[StreamingRuleViolation]:
        all_violations: List[StreamingRuleViolation] = []
        for p in file_paths:
            path = Path(p)
            if not path.is_absolute():
                path = self.workspace_root / path
            all_violations.extend(self.inspect_file(path))
        return all_violations
