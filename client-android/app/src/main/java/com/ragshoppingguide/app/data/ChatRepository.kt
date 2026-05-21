package com.ragshoppingguide.app.data

import com.ragshoppingguide.app.core.SseParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

sealed interface ChatStreamEvent {
    data class Meta(val retrievedProductIds: List<String>) : ChatStreamEvent
    data class Token(val token: String) : ChatStreamEvent
    data class Done(val productIds: List<String>) : ChatStreamEvent
    data class Error(val message: String) : ChatStreamEvent
}

class ChatRepository(
    private val client: OkHttpClient = defaultSseClient(),
    private val json: Json = Json { ignoreUnknownKeys = true },
) {
    fun streamChat(
        query: String,
        sessionId: String,
        history: List<ChatHistoryItemDto>,
    ): Flow<ChatStreamEvent> = flow {
        val payload = json.encodeToString(ChatRequestDto(query, sessionId, history))
        val request = Request.Builder()
            .url(ApiConfig.resolve("/chat"))
            .post(payload.toRequestBody("application/json; charset=utf-8".toMediaType()))
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw IOException("POST /chat failed: HTTP ${response.code}")
            }

            val body = response.body ?: throw IOException("POST /chat returned empty body")
            val parser = SseParser()
            val source = body.source()

            while (!source.exhausted()) {
                val line = source.readUtf8Line() ?: break
                val event = parser.accept(line) ?: continue
                emit(event.toChatStreamEvent(json))
            }
        }
    }.flowOn(Dispatchers.IO)

    private fun com.ragshoppingguide.app.core.SseEvent.toChatStreamEvent(json: Json): ChatStreamEvent {
        val payload = runCatching { json.parseToJsonElement(data).jsonObject }.getOrNull()
        return when (event) {
            "meta" -> ChatStreamEvent.Meta(
                retrievedProductIds = payload?.get("retrieved_product_ids")
                    ?.toStringList()
                    .orEmpty()
            )
            "token" -> ChatStreamEvent.Token(
                token = payload?.get("token")?.jsonPrimitive?.contentOrNull.orEmpty()
            )
            "done" -> ChatStreamEvent.Done(
                productIds = payload?.get("product_ids")?.toStringList().orEmpty()
            )
            "error" -> ChatStreamEvent.Error(
                message = payload?.get("message")?.jsonPrimitive?.contentOrNull ?: "服务暂时不可用"
            )
            else -> ChatStreamEvent.Error("未知事件：$event")
        }
    }
}

private fun defaultSseClient(): OkHttpClient {
    return OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS)
        .build()
}

private fun JsonElement.toStringList(): List<String> {
    return (this as? JsonArray)
        ?.mapNotNull { item -> item.jsonPrimitive.contentOrNull }
        .orEmpty()
}
