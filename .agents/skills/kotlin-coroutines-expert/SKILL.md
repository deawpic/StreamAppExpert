---
name: kotlin-coroutines-expert
description: "Expert patterns for Kotlin Coroutines and Flow tailored for video streaming: StateFlow for player states, network scraping concurrency, cancellation, and memory leak prevention."
risk: safe
source: adapted-from-awesome-skills
date_added: "2026-11-09"
---

# ⚡ Kotlin Coroutines Expert (Streaming Edition)

You are an expert Kotlin engineer specializing in structured concurrency, asynchronous flows, and reactive state management for streaming applications.

## 🚨 Concurrency Invariants for Streaming

1. **Dispatcher Separation**:
   - `Dispatchers.Main`: UI updates, Compose state transitions, and ExoPlayer controls (ExoPlayer must be called on the main thread).
   - `Dispatchers.IO`: Network requests, HTML web scraping, token resolution, and disk caching.
   - `Dispatchers.Default`: Heavy parsing, regex processing, and JSON serialization.

2. **Player State Modeling with StateFlow**:
   Represent player status with a strongly-typed sealed interface:
   ```kotlin
   sealed interface PlayerUiState {
       data object Loading : PlayerUiState
       data class Ready(
           val title: String,
           val durationMs: Long,
           val currentPositionMs: Long,
           val isPlaying: Boolean,
           val bufferPercentage: Int
       ) : PlayerUiState
       data class Error(val message: String, val canRetry: Boolean) : PlayerUiState
   }
   ```

3. **Resilient Network Scraping with Exponential Backoff**:
   ```kotlin
   suspend fun <T> retryScrape(
       retries: Int = 3,
       initialDelayMs: Long = 1000,
       maxDelayMs: Long = 4000,
       factor: Double = 2.0,
       block: suspend () -> T
   ): T {
       var currentDelay = initialDelayMs
       repeat(retries - 1) {
           try {
               return block()
           } catch (e: Exception) {
               delay(currentDelay)
               currentDelay = (currentDelay * factor).toLong().coerceAtMost(maxDelayMs)
           }
       }
       return block() // Last attempt
   }
   ```

4. **Structured Concurrency in ViewModels**:
   Always launch network tasks in `viewModelScope` so requests cancel automatically when the user navigates away, avoiding orphaned network sockets or memory leaks.
