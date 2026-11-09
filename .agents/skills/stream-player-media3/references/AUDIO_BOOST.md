# 🔊 SoundBoostManager: Hardware LoudnessEnhancer for Sub-Mastered Streams

## 1. Why Software Audio Scaling Fails
- Web scraped streams often have dialogues recorded at low decibel levels (-18dB to -24dB LUFS).
- Multiplying PCM samples in software (`player.volume = 2.0f`) causes clipping, harmonic distortion, and speaker crackling when loud sound effects trigger.

## 2. Hardware LoudnessEnhancer Solution
Android provides `android.media.audiofx.LoudnessEnhancer`, a hardware-accelerated DSP effect designed to compress dynamic range and boost perceived dialogue loudness without clipping.

```kotlin
package com.streamapp.player

import android.media.audiofx.LoudnessEnhancer
import android.util.Log

enum class SoundBoostLevel(val title: String, val gainMilliBels: Int) {
    OFF("ปิดบูสต์เสียง", 0),
    BOOST_125("1.25x (+2.5 dB)", 250),
    BOOST_150("1.50x (+5.0 dB)", 500),
    BOOST_175("1.75x (+7.0 dB)", 700),
    BOOST_200("2.00x (+8.5 dB)", 850),
    BOOST_MAX("MAX (+12.0 dB)", 1200);

    fun next(): SoundBoostLevel {
        val values = entries
        return values[(ordinal + 1) % values.size]
    }
}

class SoundBoostManager {
    private var loudnessEnhancer: LoudnessEnhancer? = null
    var currentLevel: SoundBoostLevel = SoundBoostLevel.OFF
        private set

    fun attachToAudioSession(audioSessionId: Int) {
        release()
        if (audioSessionId <= 0) return

        try {
            loudnessEnhancer = LoudnessEnhancer(audioSessionId).apply {
                enabled = currentLevel != SoundBoostLevel.OFF
                setTargetGain(currentLevel.gainMilliBels)
            }
        } catch (e: Exception) {
            Log.e("SoundBoostManager", "Failed to initialize LoudnessEnhancer", e)
        }
    }

    fun setLevel(level: SoundBoostLevel) {
        currentLevel = level
        loudnessEnhancer?.let {
            try {
                if (level == SoundBoostLevel.OFF) {
                    it.enabled = false
                } else {
                    it.enabled = true
                    it.setTargetGain(level.gainMilliBels)
                }
            } catch (e: Exception) {
                Log.e("SoundBoostManager", "Error updating target gain", e)
            }
        }
    }

    fun cycleNext(): SoundBoostLevel {
        val next = currentLevel.next()
        setLevel(next)
        return next
    }

    fun release() {
        try {
            loudnessEnhancer?.release()
        } catch (ignored: Exception) {}
        loudnessEnhancer = null
    }
}
```
