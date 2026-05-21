package com.ragshoppingguide.app.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException

class ProductRepository(
    private val client: OkHttpClient = OkHttpClient(),
    private val json: Json = Json { ignoreUnknownKeys = true },
) {
    suspend fun fetchProducts(): List<Product> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url(ApiConfig.resolve("/products"))
            .get()
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw IOException("GET /products failed: HTTP ${response.code}")
            }
            val body = response.body?.string() ?: throw IOException("GET /products returned empty body")
            json.decodeFromString<ProductsResponse>(body).products
        }
    }
}
