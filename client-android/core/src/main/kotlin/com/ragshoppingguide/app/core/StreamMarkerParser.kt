package com.ragshoppingguide.app.core

class StreamMarkerParser {
    private var buffer = ""

    fun append(token: String): List<MessageBlock> {
        buffer += token
        return consume(allowIncompleteFlush = false)
    }

    fun finish(): List<MessageBlock> = consume(allowIncompleteFlush = true)

    private fun consume(allowIncompleteFlush: Boolean): List<MessageBlock> {
        val blocks = mutableListOf<MessageBlock>()

        while (buffer.isNotEmpty()) {
            val markerStart = buffer.indexOf("[[")
            if (markerStart < 0) {
                flushTextWithoutMarkerStart(allowIncompleteFlush, blocks)
                break
            }

            if (markerStart > 0) {
                appendText(buffer.substring(0, markerStart), blocks)
                buffer = buffer.substring(markerStart)
                continue
            }

            val markerEnd = buffer.indexOf("]]")
            if (markerEnd < 0) {
                if (allowIncompleteFlush) {
                    appendText(buffer, blocks)
                    buffer = ""
                }
                break
            }

            val marker = buffer.substring(0, markerEnd + 2)
            blocks += parseMarker(marker) ?: MessageBlock.Text(marker)
            buffer = buffer.substring(markerEnd + 2)
        }

        return blocks
    }

    private fun flushTextWithoutMarkerStart(
        allowIncompleteFlush: Boolean,
        blocks: MutableList<MessageBlock>,
    ) {
        if (!allowIncompleteFlush && buffer.endsWith("[")) {
            appendText(buffer.dropLast(1), blocks)
            buffer = "["
            return
        }

        appendText(buffer, blocks)
        buffer = ""
    }

    private fun parseMarker(marker: String): MessageBlock? {
        if (marker.startsWith("[[SOURCE:") && marker.endsWith("]]")) {
            val body = marker
                .removePrefix("[[SOURCE:")
                .removeSuffix("]]")
            val separatorIndex = body.indexOf("|")
            if (separatorIndex <= 0) return null

            val sourceType = body.substring(0, separatorIndex).trim()
            val text = body.substring(separatorIndex + 1).trim()
            if (sourceType !in SOURCE_TYPES || text.isEmpty()) return null

            return MessageBlock.SourceText(sourceType, text)
        }

        if (marker.startsWith("[[PRODUCT:") && marker.endsWith("]]")) {
            val ids = marker
                .removePrefix("[[PRODUCT:")
                .removeSuffix("]]")
                .split(",")
                .map { it.trim() }
                .filter { it.isNotEmpty() }
            return if (ids.isEmpty()) null else MessageBlock.ProductCards(ids)
        }

        if (marker.startsWith("[[COMPARE:") && marker.endsWith("]]")) {
            val ids = marker
                .removePrefix("[[COMPARE:")
                .removeSuffix("]]")
                .split(",")
                .map { it.trim() }
                .filter { it.isNotEmpty() }
            return if (ids.isEmpty()) null else MessageBlock.Compare(ids)
        }

        return null
    }

    private fun appendText(text: String, blocks: MutableList<MessageBlock>) {
        if (text.isEmpty()) return

        val last = blocks.lastOrNull()
        if (last is MessageBlock.Text) {
            blocks[blocks.lastIndex] = MessageBlock.Text(last.value + text)
        } else {
            blocks += MessageBlock.Text(text)
        }
    }
}

private val SOURCE_TYPES = setOf("official", "review", "marketing", "summary")
