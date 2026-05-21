package com.ragshoppingguide.app.core

import org.junit.Assert.assertEquals
import org.junit.Test

class StreamMarkerParserTest {
    @Test
    fun plainTextPassesThrough() {
        val parser = StreamMarkerParser()

        assertEquals(listOf(MessageBlock.Text("推荐你看这款洁面。")), parser.append("推荐你看这款洁面。"))
        assertEquals(emptyList<MessageBlock>(), parser.finish())
    }

    @Test
    fun productMarkerBecomesProductCardBlock() {
        val parser = StreamMarkerParser()

        assertEquals(
            listOf(MessageBlock.ProductCards(listOf("p_beauty_001"))),
            parser.append("[[PRODUCT:p_beauty_001]]")
        )
    }

    @Test
    fun commaSeparatedProductMarkerBecomesProductCardBlock() {
        val parser = StreamMarkerParser()

        assertEquals(
            listOf(MessageBlock.ProductCards(listOf("p_clothes_020", "p_clothes_002", "p_food_005"))),
            parser.append("[[PRODUCT:p_clothes_020,p_clothes_002,p_food_005]]")
        )
    }

    @Test
    fun productMarkerSplitAcrossTokensIsBuffered() {
        val parser = StreamMarkerParser()

        assertEquals(listOf(MessageBlock.Text("推荐 ")), parser.append("推荐 [[PRO"))
        assertEquals(
            listOf(MessageBlock.ProductCards(listOf("p_beauty_001"))),
            parser.append("DUCT:p_beauty_001]]")
        )
    }

    @Test
    fun compareMarkerBecomesCompareBlock() {
        val parser = StreamMarkerParser()

        assertEquals(
            listOf(MessageBlock.Compare(listOf("p_digital_001", "p_digital_002"))),
            parser.append("[[COMPARE:p_digital_001,p_digital_002]]")
        )
    }

    @Test
    fun sourceMarkerBecomesSourceTextBlock() {
        val parser = StreamMarkerParser()

        assertEquals(
            listOf(MessageBlock.SourceText("review", "用户反馈重度使用需要补电")),
            parser.append("[[SOURCE:review|用户反馈重度使用需要补电]]")
        )
    }

    @Test
    fun sourceMarkerSplitAcrossTokensIsBuffered() {
        val parser = StreamMarkerParser()

        assertEquals(listOf(MessageBlock.Text("续航 ")), parser.append("续航 [[SOUR"))
        assertEquals(
            listOf(MessageBlock.SourceText("official", "官方标称轻度 1.5 天")),
            parser.append("CE:official|官方标称轻度 1.5 天]]")
        )
    }

    @Test
    fun mixedSourceCompareAndTextPreserveOrder() {
        val parser = StreamMarkerParser()

        assertEquals(
            listOf(
                MessageBlock.SourceText("official", "官方信息"),
                MessageBlock.Text(" 中间 "),
                MessageBlock.Compare(listOf("p_digital_001", "p_digital_002")),
            ),
            parser.append(
                "[[SOURCE:official|官方信息]] 中间 [[COMPARE:p_digital_001,p_digital_002]]"
            )
        )
    }

    @Test
    fun unfinishedMarkerFlushesAsTextOnFinish() {
        val parser = StreamMarkerParser()

        assertEquals(listOf(MessageBlock.Text("推荐 ")), parser.append("推荐 [[PRODUCT:p_"))
        assertEquals(listOf(MessageBlock.Text("[[PRODUCT:p_")), parser.finish())
    }

    @Test
    fun unfinishedSourceMarkerFlushesAsTextOnFinish() {
        val parser = StreamMarkerParser()

        assertEquals(listOf(MessageBlock.Text("来源 ")), parser.append("来源 [[SOURCE:review|用户"))
        assertEquals(listOf(MessageBlock.Text("[[SOURCE:review|用户")), parser.finish())
    }
}
