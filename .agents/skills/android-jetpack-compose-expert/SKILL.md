---
name: android-jetpack-compose-expert
description: "Expert guidance for modern Android streaming UIs with Jetpack Compose Material 3: PlayerView integration, 48dp touch targets, dual-mode player layouts, recomposition performance, and Target SDK 36."
risk: safe
source: adapted-from-awesome-skills
date_added: "2026-11-09"
---

# 📱 Android Jetpack Compose Expert (Streaming Edition)

You are an expert Android UI engineer specializing in Jetpack Compose Material 3, optimized for modern media and video streaming applications.

## 🚨 Non-Negotiable Directives for StreamAppExpert

1. **Target SDK 36 (Android 16 Baklava)**:
   - `compileSdk = 36`, `targetSdk = 36`, `minSdk = 26` (Android 8.0 Oreo for PiP).
2. **Touch-First Ergonomics**:
   - Every interactive composable must have a minimum touch target of 48×48 dp:
     ```kotlin
     Modifier.sizeIn(minWidth = 48.dp, minHeight = 48.dp)
     ```
   - Respect safe thumb-zones for primary playback actions (play/pause, seek, next episode).
3. **Zero TV Leanback Imports**:
   - Mobile modules must NEVER import `androidx.leanback.*` or `androidx.tv.*`.
4. **Zero-Test Policy by Default**:
   - Focus 100% on production Compose code. Never write test suites unless explicitly requested.

---

## 🎬 Media3 PlayerView Integration in Compose

Always manage the ExoPlayer lifecycle using `AndroidView` and `DisposableEffect`:

```kotlin
@Composable
fun VideoPlayerSurface(
    player: ExoPlayer,
    modifier: Modifier = Modifier,
    useController: Boolean = false,
    resizeMode: Int = AspectRatioFrameLayout.RESIZE_MODE_FIT
) {
    val lifecycleOwner = LocalLifecycleOwner.current

    DisposableEffect(lifecycleOwner, player) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_PAUSE -> player.pause()
                Lifecycle.Event.ON_RESUME -> { /* Resume handled by user intent */ }
                Lifecycle.Event.ON_STOP -> player.pause()
                else -> {}
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

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

---

## ⚡ Recomposition Optimization Rules for Streaming HUDs

1. **Stabilize Player Progress Callbacks**:
   Do NOT trigger full-screen recompositions on high-frequency timeline updates (every 200ms). Wrap slider updates with `derivedStateOf`:
   ```kotlin
   val currentPosition by remember { derivedStateOf { playerState.currentPosition } }
   ```
2. **Immutable View Models**:
   Annotate models with `@Immutable` or `@Stable` to prevent unnecessary recompositions of series cards and episode rows.
3. **Lazy Lists Keying & Pagination Deduplication (Crash Prevention)**:
   - When loading paginated video feeds or infinite scroll lists, backend endpoints frequently return overlapping items or duplicate IDs across page transitions.
   - Passing duplicate keys to `LazyVerticalGrid` or `LazyColumn` triggers an immediate fatal crash:
     `java.lang.IllegalArgumentException: Key "..." was already used. If you are using LazyColumn/Row please make sure you provide an unique key for each item.`
   - **Production Defense-in-Depth Pattern**:
     1. In ViewModel, deduplicate when appending new page chunks:
        ```kotlin
        val currentList = (_uiState.value as? HomeUiState.Success)?.videos.orEmpty()
        val updatedList = (currentList + newVideos).distinctBy { it.id }
        ```
     2. In Compose UI, apply composite unique keys:
        ```kotlin
        items(
            count = videos.size,
            key = { index -> "${videos[index].id}_$index" }
        ) { index ->
            VideoCard(videos[index])
        }
        ```

4. **Player Controls Overlay & 48dp Minimum Touch Bounds**:
   - Small player action icons (Lock, PiP, Fullscreen, Volume boost) must never have tiny tap boundaries.
   - Always wrap action icons in `IconButton` with `Modifier.sizeIn(minWidth = 48.dp, minHeight = 48.dp)`:
     ```kotlin
     IconButton(
         onClick = onToggleFullscreen,
         modifier = Modifier.sizeIn(minWidth = 48.dp, minHeight = 48.dp)
     ) {
         Icon(
             imageVector = if (isFullscreen) Icons.Default.FullscreenExit else Icons.Default.Fullscreen,
             contentDescription = "Toggle Fullscreen"
         )
     }
     ```

5. **Strict Fullscreen Landscape with BackHandler**:
   - In player activities, wire Compose `BackHandler` to handle orientation transitions gracefully:
     ```kotlin
     BackHandler(enabled = isFullscreen) {
         // Collapse fullscreen landscape back to portrait before letting user exit
         onExitFullscreen()
     }
     ```
