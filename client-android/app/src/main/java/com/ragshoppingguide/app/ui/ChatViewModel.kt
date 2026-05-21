package com.ragshoppingguide.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ragshoppingguide.app.core.MessageBlock
import com.ragshoppingguide.app.core.StreamMarkerParser
import com.ragshoppingguide.app.core.appendMerged
import com.ragshoppingguide.app.data.ApiConfig
import com.ragshoppingguide.app.data.ChatHistoryItemDto
import com.ragshoppingguide.app.data.ChatRepository
import com.ragshoppingguide.app.data.ChatStreamEvent
import com.ragshoppingguide.app.data.Product
import com.ragshoppingguide.app.data.ProductRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID

enum class ChatRole(val wireName: String) {
    User("user"),
    Assistant("assistant"),
}

data class ChatMessageUi(
    val id: String = UUID.randomUUID().toString(),
    val role: ChatRole,
    val blocks: List<MessageBlock>,
    val isStreaming: Boolean = false,
) {
    val textContent: String
        get() = blocks.joinToString("") { block ->
            when (block) {
                is MessageBlock.Text -> block.value
                is MessageBlock.SourceText -> block.value
                is MessageBlock.ProductCards,
                is MessageBlock.Compare -> ""
            }
        }
}

data class ChatUiState(
    val messages: List<ChatMessageUi> = emptyList(),
    val productsById: Map<String, Product> = emptyMap(),
    val input: String = "",
    val serverBaseUrl: String = ApiConfig.baseUrl,
    val serverInput: String = ApiConfig.baseUrl,
    val isStreaming: Boolean = false,
    val errorMessage: String? = null,
) {
    val promptTiles: List<String> = listOf(
        "健身入门装备怎么配",
        "推荐一款适合油皮的洗面奶",
        "300 元以下的真无线耳机有哪些",
        "iPhone 17 Pro 续航好不好",
        "推荐跑鞋，要轻便",
        "防晒霜不要日系品牌",
    )
}

class ChatViewModel(
    private val productRepository: ProductRepository = ProductRepository(),
    private val chatRepository: ChatRepository = ChatRepository(),
) : ViewModel() {
    private val sessionId = UUID.randomUUID().toString()
    private var parser = StreamMarkerParser()

    private val _state = MutableStateFlow(ChatUiState())
    val state: StateFlow<ChatUiState> = _state.asStateFlow()

    init {
        loadProducts()
    }

    fun updateInput(value: String) {
        _state.update { it.copy(input = value) }
    }

    fun updateServerInput(value: String) {
        _state.update { it.copy(serverInput = value) }
    }

    fun applyServerBaseUrl() {
        if (state.value.isStreaming) return
        val normalized = ApiConfig.updateBaseUrl(state.value.serverInput)
        _state.update {
            it.copy(
                serverBaseUrl = normalized,
                serverInput = normalized,
                productsById = emptyMap(),
                errorMessage = null,
            )
        }
        loadProducts()
    }

    fun sendCurrentInput() {
        val query = state.value.input.trim()
        if (query.isEmpty()) return
        _state.update { it.copy(input = "") }
        send(query)
    }

    fun sendPrompt(query: String) {
        send(query)
    }

    private fun loadProducts() {
        viewModelScope.launch {
            runCatching { productRepository.fetchProducts() }
                .onSuccess { products ->
                    _state.update {
                        it.copy(productsById = products.associateBy(Product::productId))
                    }
                }
                .onFailure { error ->
                    _state.update { it.copy(errorMessage = "商品加载失败：${error.message}") }
                }
        }
    }

    private fun send(query: String) {
        if (state.value.isStreaming) return

        val userMessage = ChatMessageUi(role = ChatRole.User, blocks = listOf(MessageBlock.Text(query)))
        val assistantMessage = ChatMessageUi(role = ChatRole.Assistant, blocks = emptyList(), isStreaming = true)
        parser = StreamMarkerParser()

        _state.update {
            it.copy(
                messages = it.messages + userMessage + assistantMessage,
                isStreaming = true,
                errorMessage = null,
            )
        }

        viewModelScope.launch {
            runCatching {
                chatRepository.streamChat(
                    query = query,
                    sessionId = sessionId,
                    history = historyItems(excludingId = assistantMessage.id),
                ).collect { event ->
                    handleStreamEvent(event, assistantMessage.id)
                }
            }.onFailure { error ->
                appendBlocks(
                    assistantMessage.id,
                    listOf(MessageBlock.Text("请求失败：${error.message ?: "网络不可用"}")),
                )
                _state.update { it.copy(errorMessage = error.message) }
            }

            appendBlocks(assistantMessage.id, parser.finish())
            finishAssistantMessage(assistantMessage.id)
        }
    }

    private fun handleStreamEvent(event: ChatStreamEvent, assistantId: String) {
        when (event) {
            is ChatStreamEvent.Token -> appendBlocks(assistantId, parser.append(event.token))
            is ChatStreamEvent.Error -> appendBlocks(assistantId, listOf(MessageBlock.Text(event.message)))
            is ChatStreamEvent.Done,
            is ChatStreamEvent.Meta -> Unit
        }
    }

    private fun appendBlocks(messageId: String, blocks: List<MessageBlock>) {
        if (blocks.isEmpty()) return
        _state.update { current ->
            current.copy(
                messages = current.messages.map { message ->
                    if (message.id == messageId) {
                        message.copy(blocks = message.blocks.appendMerged(blocks))
                    } else {
                        message
                    }
                }
            )
        }
    }

    private fun finishAssistantMessage(messageId: String) {
        _state.update { current ->
            current.copy(
                messages = current.messages.map { message ->
                    if (message.id == messageId) {
                        message.copy(isStreaming = false)
                    } else {
                        message
                    }
                },
                isStreaming = false,
            )
        }
    }

    private fun historyItems(excludingId: String): List<ChatHistoryItemDto> {
        return state.value.messages
            .filter { it.id != excludingId }
            .mapNotNull { message ->
                val content = message.textContent
                if (content.isBlank()) {
                    null
                } else {
                    ChatHistoryItemDto(role = message.role.wireName, content = content)
                }
            }
    }
}
