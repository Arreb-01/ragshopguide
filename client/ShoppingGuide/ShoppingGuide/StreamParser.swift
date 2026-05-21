import Foundation

struct StreamParser {
    private var buffer = ""

    mutating func append(_ token: String) -> [MessageBlock] {
        buffer += token
        return consume(allowIncompleteFlush: false)
    }

    mutating func finish() -> [MessageBlock] {
        consume(allowIncompleteFlush: true)
    }

    private mutating func consume(allowIncompleteFlush: Bool) -> [MessageBlock] {
        var blocks: [MessageBlock] = []

        while !buffer.isEmpty {
            guard let markerStart = buffer.range(of: "[[") else {
                flushTextWithoutMarkerStart(allowIncompleteFlush: allowIncompleteFlush, into: &blocks)
                break
            }

            if markerStart.lowerBound > buffer.startIndex {
                let prefix = String(buffer[..<markerStart.lowerBound])
                appendText(prefix, into: &blocks)
                buffer.removeSubrange(..<markerStart.lowerBound)
                continue
            }

            guard let markerEnd = buffer.range(of: "]]") else {
                if allowIncompleteFlush {
                    appendText(buffer, into: &blocks)
                    buffer.removeAll()
                }
                break
            }

            let marker = String(buffer[buffer.startIndex..<markerEnd.upperBound])
            if let block = parseMarker(marker) {
                blocks.append(block)
            } else {
                appendText(marker, into: &blocks)
            }
            buffer.removeSubrange(buffer.startIndex..<markerEnd.upperBound)
        }

        return blocks
    }

    private mutating func flushTextWithoutMarkerStart(
        allowIncompleteFlush: Bool,
        into blocks: inout [MessageBlock]
    ) {
        if !allowIncompleteFlush, buffer.last == "[" {
            let text = String(buffer.dropLast())
            appendText(text, into: &blocks)
            buffer = "["
            return
        }

        appendText(buffer, into: &blocks)
        buffer.removeAll()
    }

    private func parseMarker(_ marker: String) -> MessageBlock? {
        if marker.hasPrefix("[[PRODUCT:"), marker.hasSuffix("]]") {
            let id = marker
                .dropFirst("[[PRODUCT:".count)
                .dropLast(2)
                .trimmingCharacters(in: .whitespacesAndNewlines)
            return id.isEmpty ? nil : .productCards([String(id)])
        }

        if marker.hasPrefix("[[COMPARE:"), marker.hasSuffix("]]") {
            let ids = marker
                .dropFirst("[[COMPARE:".count)
                .dropLast(2)
                .split(separator: ",")
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty }
            return ids.isEmpty ? nil : .comparison(ids)
        }

        return nil
    }

    private func appendText(_ text: String, into blocks: inout [MessageBlock]) {
        guard !text.isEmpty else { return }
        if case .text(let existing) = blocks.last {
            blocks[blocks.count - 1] = .text(existing + text)
        } else {
            blocks.append(.text(text))
        }
    }
}
