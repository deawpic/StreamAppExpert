# 🎭 CDN Disguised Video Unmasking (MaskedTsDataSource & Interceptor)

## 1. Problem Background
Video streaming servers frequently mask MPEG-TS transport stream segments as static image files (`.image`, `.png`, `.jpg`, `.webp`) hosted on third-party image CDNs (e.g. TikTok ImageX, ByteDance CDN, Cloudflare Image Cache).

They prepend a 252-byte valid PNG header to trick CDN mime-type sniffing into serving the segment under image caching rules (`Cache-Control: max-age=31536000`).

## 2. Binary Hex Signature
```
Offset 0x00: 89 50 4E 47 0D 0A 1A 0A ... (252-byte 1x1 Pixel Dummy PNG)
Offset 0xFC (252): 47 40 00 10 ... (Sync byte 0x47, PID 0 PAT Packet)
Segment stride: Exactly 188 bytes per MPEG-TS packet
```

## 3. MaskedTsDataSource Implementation
```kotlin
package com.streamapp.player

import android.net.Uri
import androidx.media3.common.C
import androidx.media3.datasource.DataSource
import androidx.media3.datasource.DataSpec
import androidx.media3.datasource.TransferListener
import java.io.IOException

class MaskedTsDataSource(private val upstream: DataSource) : DataSource {

    companion object {
        private const val PNG_HEADER_SIZE = 252
        private val PNG_MAGIC = byteArrayOf(
            0x89.toByte(), 0x50.toByte(), 0x4E.toByte(), 0x47.toByte(),
            0x0D.toByte(), 0x0A.toByte(), 0x1A.toByte(), 0x0A.toByte()
        )
    }

    private var bytesSkipped = 0
    private var isMaskedStream = false
    private var headerBuffer = ByteArray(PNG_HEADER_SIZE)
    private var headerBuffered = 0

    override fun open(dataSpec: DataSpec): Long {
        bytesSkipped = 0
        headerBuffered = 0
        isMaskedStream = false

        val uriStr = dataSpec.uri.toString().lowercase()
        val likelyMasked = uriStr.contains(".image") || uriStr.contains("tiktokcdn") || uriStr.contains(".png")

        val responseLength = upstream.open(dataSpec)

        if (likelyMasked && dataSpec.position == 0L) {
            // Read first 252 bytes to verify PNG magic
            while (headerBuffered < PNG_HEADER_SIZE) {
                val read = upstream.read(headerBuffer, headerBuffered, PNG_HEADER_SIZE - headerBuffered)
                if (read == C.RESULT_END_OF_INPUT) break
                headerBuffered += read
            }

            if (headerBuffered >= 8 && matchesPngMagic(headerBuffer)) {
                isMaskedStream = true
                // Discard the 252 bytes, TS starts immediately at byte 252
                return if (responseLength != C.LENGTH_UNSET.toLong()) responseLength - PNG_HEADER_SIZE else C.LENGTH_UNSET.toLong()
            }
        }

        return responseLength
    }

    override fun read(buffer: ByteArray, offset: Int, length: Int): Int {
        if (!isMaskedStream && headerBuffered > 0) {
            // Drain unmasked buffered data
            val bytesToCopy = minOf(headerBuffered, length)
            System.arraycopy(headerBuffer, 0, buffer, offset, bytesToCopy)
            headerBuffered -= bytesToCopy
            return bytesToCopy
        }
        return upstream.read(buffer, offset, length)
    }

    private fun matchesPngMagic(data: ByteArray): Boolean {
        for (i in PNG_MAGIC.indices) {
            if (data[i] != PNG_MAGIC[i]) return false
        }
        return true
    }

    override fun addTransferListener(transferListener: TransferListener) = upstream.addTransferListener(transferListener)
    override fun getUri(): Uri? = upstream.uri
    override fun getResponseHeaders(): Map<String, List<String>> = upstream.responseHeaders
    override fun close() = upstream.close()
}
```

## 4. HlsFakeImageInterceptor Implementation
```kotlin
package com.streamapp.player

import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody

class HlsFakeImageInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val response = chain.proceed(request)
        val url = request.url.toString().lowercase()

        if (url.contains(".image") || url.contains("tiktokcdn") || url.contains("/ts/")) {
            val contentType = response.header("Content-Type")?.lowercase() ?: ""
            if (!contentType.contains("mp2t") && !contentType.contains("video")) {
                // Return response with Content-Type rewritten to video/mp2t while keeping origin Cache-Control
                return response.newBuilder()
                    .header("Content-Type", "video/mp2t")
                    .build()
            }
        }
        return response
    }
}
```
