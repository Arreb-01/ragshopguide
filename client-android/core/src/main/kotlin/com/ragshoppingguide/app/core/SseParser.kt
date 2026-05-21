package com.ragshoppingguide.app.core

data class SseEvent(
    val event: String,
    val data: String,
)

class SseParser {
    private var eventName = ""
    private val dataLines = mutableListOf<String>()

    fun accept(line: String): SseEvent? {
        if (line.isEmpty()) {
            return emit()
        }

        when {
            line.startsWith("event: ") -> eventName = line.removePrefix("event: ")
            line.startsWith("data: ") -> dataLines += line.removePrefix("data: ")
        }

        return null
    }

    private fun emit(): SseEvent? {
        if (eventName.isEmpty()) {
            dataLines.clear()
            return null
        }

        val event = SseEvent(event = eventName, data = dataLines.joinToString("\n"))
        eventName = ""
        dataLines.clear()
        return event
    }
}
