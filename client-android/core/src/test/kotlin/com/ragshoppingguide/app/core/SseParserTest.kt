package com.ragshoppingguide.app.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class SseParserTest {
    @Test
    fun tokenEventIsEmittedOnBlankLine() {
        val parser = SseParser()

        assertNull(parser.accept("event: token"))
        assertNull(parser.accept("""data: {"token":"好"}"""))
        assertEquals(SseEvent("token", """{"token":"好"}"""), parser.accept(""))
    }

    @Test
    fun doneEventCanCarryJsonPayload() {
        val parser = SseParser()

        parser.accept("event: done")
        parser.accept("""data: {"product_ids":["p_1"]}""")

        assertEquals(SseEvent("done", """{"product_ids":["p_1"]}"""), parser.accept(""))
    }

    @Test
    fun errorEventCanCarryJsonPayload() {
        val parser = SseParser()

        parser.accept("event: error")
        parser.accept("""data: {"message":"query must not be empty"}""")

        assertEquals(
            SseEvent("error", """{"message":"query must not be empty"}"""),
            parser.accept("")
        )
    }
}
