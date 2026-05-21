package com.ragshoppingguide.app.core

sealed interface MessageBlock {
    data class Text(val value: String) : MessageBlock
    data class SourceText(val sourceType: String, val value: String) : MessageBlock
    data class ProductCards(val productIds: List<String>) : MessageBlock
    data class Compare(val productIds: List<String>) : MessageBlock
}

fun List<MessageBlock>.appendMerged(incoming: List<MessageBlock>): List<MessageBlock> {
    if (incoming.isEmpty()) return this

    val merged = this.toMutableList()
    incoming.forEach { block ->
        val last = merged.lastOrNull()
        if (last is MessageBlock.Text && block is MessageBlock.Text) {
            merged[merged.lastIndex] = MessageBlock.Text(last.value + block.value)
        } else {
            merged += block
        }
    }
    return merged
}
