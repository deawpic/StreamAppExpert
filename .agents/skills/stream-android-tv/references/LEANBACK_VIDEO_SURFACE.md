# 📺 Leanback VideoSupportFragment & Surface Holder Architecture

```kotlin
package com.streamapp.tv.playback

import android.os.Bundle
import androidx.leanback.app.VideoSupportFragment
import androidx.leanback.app.VideoSupportFragmentGlueHost
import androidx.leanback.media.PlaybackTransportControlGlue
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.leanback.LeanbackPlayerAdapter

class TvPlaybackFragment : VideoSupportFragment() {

    private lateinit var player: ExoPlayer
    private lateinit var playerGlue: PlaybackTransportControlGlue<LeanbackPlayerAdapter>

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 1. Initialize Media3 Player with unmasking DataSource
        player = ExoPlayer.Builder(requireContext()).build()

        // 2. Connect LeanbackPlayerAdapter with VideoSupportFragmentGlueHost
        val playerAdapter = LeanbackPlayerAdapter(requireContext(), player, 500)
        playerGlue = PlaybackTransportControlGlue(requireContext(), playerAdapter).apply {
            host = VideoSupportFragmentGlueHost(this@TvPlaybackFragment)
            isSeekEnabled = true
        }

        // 3. Directly attach video surface to avoid race conditions
        surfaceView?.let { player.setVideoSurfaceView(it) }
    }

    override fun onPause() {
        super.onPause()
        player.pause()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        player.release()
    }
}
```
