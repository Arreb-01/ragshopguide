package com.ragshoppingguide.app.core

object ApiEndpoint {
    const val EMULATOR_BASE_URL = "http://10.0.2.2:8000"

    fun normalizeBaseUrl(input: String): String {
        val trimmed = input.trim().trimEnd('/')
        if (trimmed.isEmpty()) return EMULATOR_BASE_URL

        return if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
            trimmed
        } else {
            "http://$trimmed"
        }
    }

    fun resolveUrl(baseUrl: String, pathOrUrl: String): String {
        if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
            return pathOrUrl
        }
        return normalizeBaseUrl(baseUrl).trimEnd('/') + "/" + pathOrUrl.trimStart('/')
    }
}
