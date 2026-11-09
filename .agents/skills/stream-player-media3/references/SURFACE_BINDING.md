# 🖥️ SurfaceView Binding: Leanback TV vs Compose Mobile

## 1. Android TV Leanback Surface Binding (The Black Screen Bug)
### Root Cause
`PlaybackSupportFragment` has NO `SurfaceView` in its hierarchy.
`LeanbackPlayerAdapter` only binds the surface when its glue host implements `SurfaceHolderGlueHost`.
If you pass `PlaybackSupportFragmentGlueHost`, the check fails:
```java
// Inside LeanbackPlayerAdapter:
if (mGlueHost instanceof SurfaceHolderGlueHost) {
    ((SurfaceHolderGlueHost) mGlueHost).setSurfaceHolderCallback(...);
}
```
ExoPlayer never receives a Surface, resulting in:
- Audio playing clearly
- Timeline slider advancing
- **Completely black screen**

### Correct TV Leanback Solution
```kotlin
// In TV Leanback: PlaybackFragment must extend VideoSupportFragment
class PlaybackFragment : VideoSupportFragment() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Pass VideoSupportFragmentGlueHost(this) which implements SurfaceHolderGlueHost
        val glueHost = VideoSupportFragmentGlueHost(this)
        val playerAdapter = LeanbackPlayerAdapter(requireContext(), exoPlayer, UPDATE_INTERVAL_MS)
        val transportControlGlue = PlaybackTransportControlGlue(requireContext(), playerAdapter)
        transportControlGlue.host = glueHost
        
        // Explicitly attach surfaceView to ExoPlayer
        surfaceView?.let { exoPlayer.setVideoSurfaceView(it) }
    }
}
```

---

## 2. Android Mobile Jetpack Compose Surface Binding
In Compose, integrate ExoPlayer using `AndroidView` wrapping `PlayerView`:
```kotlin
@Composable
fun ExoPlayerSurface(
    player: ExoPlayer,
    modifier: Modifier = Modifier,
    useController: Boolean = false,
    resizeMode: Int = AspectRatioFrameLayout.RESIZE_MODE_FIT
) {
    val context = LocalContext.current
    
    AndroidView(
        factory = { ctx ->
            PlayerView(ctx).apply {
                this.player = player
                this.useController = useController
                this.resizeMode = resizeMode
                layoutParams = FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT
                )
            }
        },
        update = { playerView ->
            playerView.player = player
            playerView.resizeMode = resizeMode
        },
        modifier = modifier
    )
}
```
