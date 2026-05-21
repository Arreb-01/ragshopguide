package com.ragshoppingguide.app.data

import com.ragshoppingguide.app.core.ApiEndpoint

object ApiConfig {
    const val EMULATOR_BASE_URL = ApiEndpoint.EMULATOR_BASE_URL

    var baseUrl: String = EMULATOR_BASE_URL

    fun updateBaseUrl(input: String): String {
        baseUrl = ApiEndpoint.normalizeBaseUrl(input)
        return baseUrl
    }

    fun resolve(pathOrUrl: String): String = ApiEndpoint.resolveUrl(baseUrl, pathOrUrl)
}
