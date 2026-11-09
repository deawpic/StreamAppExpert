# 🔑 Tokenplay 2-Step HLS Stream Resolution Engine

```kotlin
package com.streamapp.scraper

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.regex.Pattern

class TokenplayResolver(private val client: OkHttpClient) {

    private val iframePattern = Pattern.compile("""src=["'](https?://[^"']+/embed/([a-f0-9]{32}))["']""")

    fun resolveM3u8(baseUrl: String, postId: String, parentDomain: String = "goseries4k.com"): String? {
        // Step 1: POST to admin-ajax.php
        val ajaxUrl = "$baseUrl/wp-admin/admin-ajax.php"
        val formBody = "action=miru_custom_player&post_id=$postId"
            .toRequestBody("application/x-www-form-urlencoded".toMediaType())

        val ajaxReq = Request.Builder()
            .url(ajaxUrl)
            .post(formBody)
            .header("X-Requested-With", "XMLHttpRequest")
            .header("Referer", baseUrl)
            .build()

        val ajaxHtml = client.newCall(ajaxReq).execute().use { it.body?.string() } ?: return null
        val matcher = iframePattern.matcher(ajaxHtml)
        if (!matcher.find()) return null

        val embedUrl = matcher.group(1)
        val md5Hash = matcher.group(2)

        // Step 2: POST to tokenplay
        val tokenplayUrl = "https://torbo007.com/api/tokenplay"
        val payload = JSONObject().apply {
            put("md5", md5Hash)
            put("parent", parentDomain)
        }.toString()

        val tokenReq = Request.Builder()
            .url(tokenplayUrl)
            .post(payload.toRequestBody("application/json".toMediaType()))
            .header("Origin", "https://torbo007.com")
            .header("Referer", embedUrl)
            .header("X-Requested-With", "XMLHttpRequest")
            .build()

        val tokenRes = client.newCall(tokenReq).execute().use { it.body?.string() } ?: return null
        val json = JSONObject(tokenRes)

        val streamId = json.optString("stream_id")
        val token = json.optString("token")
        val expires = json.optLong("expires")
        val sessionId = json.optString("session_id")

        if (streamId.isEmpty() || token.isEmpty()) return null

        return "https://torbo007.com/api/stream/$streamId/index.m3u8?token=$token&expires=$expires&parent=$parentDomain&sid=$sessionId"
    }
}
```
