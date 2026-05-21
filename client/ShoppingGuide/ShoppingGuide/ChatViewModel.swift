import Foundation

@MainActor
final class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var inputText = ""
    @Published var isStreaming = false
    @Published var errorMessage: String?

    let promptTiles = [
        "健身入门装备怎么配",
        "推荐一款适合油皮的洗面奶",
        "300 元以下的真无线耳机有哪些",
        "iPhone 17 Pro 续航好不好",
        "推荐跑鞋，要轻便",
        "防晒霜不要日系品牌"
    ]

    private let service: ChatService
    private let sessionID = UUID().uuidString
    private var parser = StreamParser()

    init(service: ChatService = ChatService()) {
        self.service = service
    }

    func sendCurrentInput() {
        let query = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return }
        inputText = ""
        Task { await send(query) }
    }

    func sendTile(_ query: String) {
        inputText = ""
        Task { await send(query) }
    }

    func send(_ query: String) async {
        guard !isStreaming else { return }

        parser = StreamParser()
        errorMessage = nil
        isStreaming = true

        messages.append(ChatMessage(role: .user, blocks: [.text(query)]))
        let assistantID = UUID()
        messages.append(ChatMessage(id: assistantID, role: .assistant, blocks: [], isStreaming: true))

        do {
            try await service.streamChat(
                query: query,
                sessionID: sessionID,
                history: historyItems(excluding: assistantID)
            ) { [weak self] event in
                await self?.handle(event, assistantID: assistantID)
            }

            appendBlocks(parser.finish(), to: assistantID)
        } catch {
            appendBlocks([.text("请求失败：\(error.localizedDescription)")], to: assistantID)
            errorMessage = error.localizedDescription
        }

        finishStreaming(assistantID: assistantID)
    }

    private func handle(_ event: SSEEvent, assistantID: UUID) {
        switch event.event {
        case "token":
            guard let token = event.data["token"] else { return }
            appendBlocks(parser.append(token), to: assistantID)
        case "error":
            appendBlocks([.text(event.data["message"] ?? "服务暂时不可用")], to: assistantID)
        default:
            break
        }
    }

    private func appendBlocks(_ blocks: [MessageBlock], to messageID: UUID) {
        guard let index = messages.firstIndex(where: { $0.id == messageID }) else { return }
        messages[index].blocks.append(contentsOf: blocks)
    }

    private func finishStreaming(assistantID: UUID) {
        if let index = messages.firstIndex(where: { $0.id == assistantID }) {
            messages[index].isStreaming = false
        }
        isStreaming = false
    }

    private func historyItems(excluding streamingID: UUID) -> [ChatHistoryItem] {
        messages
            .filter { $0.id != streamingID }
            .map { ChatHistoryItem(role: $0.role.rawValue, content: $0.textContent) }
            .filter { !$0.content.isEmpty }
    }
}
