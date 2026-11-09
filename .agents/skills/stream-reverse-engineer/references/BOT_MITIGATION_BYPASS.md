# 🛡️ Anti-Bot Mitigation, Cookie Persistence & Header Spoofing

## 1. Required Headers for Gateway Scraping
Web portals and tokenplay endpoints check browser fingerprint headers. Always set:
```kotlin
val standardHeaders = mapOf(
    "User-Agent" to "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept" to "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language" to "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua" to "\"Chromium\";v=\"128\", \"Not;A=Brand\";v=\"24\"",
    "Sec-Ch-Ua-Mobile" to "?0",
    "Sec-Ch-Ua-Platform" to "\"Windows\""
)
```

## 2. In-Memory Persistent CookieJar
```kotlin
class PersistentMemoryCookieJar : okhttp3.CookieJar {
    private val cookieStore = mutableMapOf<String, MutableList<okhttp3.Cookie>>()

    override fun saveFromResponse(url: okhttp3.HttpUrl, cookies: List<okhttp3.Cookie>) {
        val host = url.host
        val current = cookieStore.getOrPut(host) { mutableListOf() }
        cookies.forEach { newCookie ->
            current.removeAll { it.name == newCookie.name }
            current.add(newCookie)
        }
    }

    override fun loadForRequest(url: okhttp3.HttpUrl): List<okhttp3.Cookie> {
        return cookieStore[url.host] ?: emptyList()
    }
}
```
