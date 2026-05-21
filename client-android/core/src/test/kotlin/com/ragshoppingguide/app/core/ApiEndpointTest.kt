package com.ragshoppingguide.app.core

import org.junit.Assert.assertEquals
import org.junit.Test

class ApiEndpointTest {
    @Test
    fun normalizeBaseUrlAddsHttpAndRemovesTrailingSlash() {
        assertEquals(
            "http://192.168.1.10:8000",
            ApiEndpoint.normalizeBaseUrl(" 192.168.1.10:8000/ "),
        )
    }

    @Test
    fun normalizeBaseUrlFallsBackForBlankInput() {
        assertEquals(ApiEndpoint.EMULATOR_BASE_URL, ApiEndpoint.normalizeBaseUrl(" "))
    }

    @Test
    fun resolveKeepsAbsoluteUrls() {
        assertEquals(
            "https://cdn.example.com/a.jpg",
            ApiEndpoint.resolveUrl("http://10.0.2.2:8000", "https://cdn.example.com/a.jpg"),
        )
    }

    @Test
    fun resolveJoinsBaseAndPath() {
        assertEquals(
            "http://10.0.2.2:8000/static/images/a.jpg",
            ApiEndpoint.resolveUrl("http://10.0.2.2:8000/", "/static/images/a.jpg"),
        )
    }
}
