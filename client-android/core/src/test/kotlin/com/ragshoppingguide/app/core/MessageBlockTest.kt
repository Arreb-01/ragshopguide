package com.ragshoppingguide.app.core

import org.junit.Assert.assertEquals
import org.junit.Test

class MessageBlockTest {
    @Test
    fun adjacentTextBlocksAreMergedAcrossAppends() {
        val existing = listOf(MessageBlock.Text("健身"))
        val incoming = listOf(
            MessageBlock.Text("入门"),
            MessageBlock.ProductCards(listOf("p_clothes_003")),
            MessageBlock.Text("装备"),
        )

        assertEquals(
            listOf(
                MessageBlock.Text("健身入门"),
                MessageBlock.ProductCards(listOf("p_clothes_003")),
                MessageBlock.Text("装备"),
            ),
            existing.appendMerged(incoming),
        )
    }

    @Test
    fun sourceTextBlocksDoNotMergeWithPlainText() {
        val existing = listOf(MessageBlock.Text("前言"))
        val incoming = listOf(MessageBlock.SourceText("summary", "综合建议"))

        assertEquals(
            listOf(
                MessageBlock.Text("前言"),
                MessageBlock.SourceText("summary", "综合建议"),
            ),
            existing.appendMerged(incoming),
        )
    }
}
