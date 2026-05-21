package com.ragshoppingguide.app.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ProductsResponse(
    val products: List<Product>,
)

@Serializable
data class Product(
    @SerialName("product_id")
    val productId: String,
    val title: String,
    val brand: String,
    val category: String,
    @SerialName("sub_category")
    val subCategory: String,
    @SerialName("base_price")
    val basePrice: Double,
    @SerialName("image_path")
    val imagePath: String,
    @SerialName("image_url")
    val imageUrl: String,
    val tags: List<String> = emptyList(),
)

@Serializable
data class ChatHistoryItemDto(
    val role: String,
    val content: String,
)

@Serializable
data class ChatRequestDto(
    val query: String,
    @SerialName("session_id")
    val sessionId: String,
    val history: List<ChatHistoryItemDto>,
)
