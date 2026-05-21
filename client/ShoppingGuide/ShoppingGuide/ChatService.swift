import Foundation

final class ChatService {
    private let baseURL: URL
    private let session: URLSession
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    init(
        baseURL: URL = URL(string: "http://127.0.0.1:8000")!,
        session: URLSession = .shared
    ) {
        self.baseURL = baseURL
        self.session = session
    }

    func fetchProducts() async throws -> [Product] {
        let url = baseURL.appending(path: "products")
        let (data, response) = try await session.data(from: url)
        try validate(response)
        return try decoder.decode(ProductsResponse.self, from: data).products
    }

    func streamChat(
        query: String,
        sessionID: String,
        history: [ChatHistoryItem],
        onEvent: @escaping (SSEEvent) async -> Void
    ) async throws {
        var request = URLRequest(url: baseURL.appending(path: "chat"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(
            ChatRequestBody(query: query, sessionID: sessionID, history: history)
        )

        let (bytes, response) = try await session.bytes(for: request)
        try validate(response)

        var eventName = ""
        var dataLines: [String] = []

        for try await line in bytes.lines {
            if line.isEmpty {
                if let event = parseEvent(name: eventName, dataLines: dataLines) {
                    await onEvent(event)
                }
                eventName = ""
                dataLines = []
                continue
            }

            if line.hasPrefix("event: ") {
                eventName = String(line.dropFirst("event: ".count))
            } else if line.hasPrefix("data: ") {
                dataLines.append(String(line.dropFirst("data: ".count)))
            }
        }
    }

    func imageURL(for product: Product) -> URL? {
        URL(string: product.imageURL, relativeTo: baseURL)
    }

    private func validate(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else { return }
        guard (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
    }

    private func parseEvent(name: String, dataLines: [String]) -> SSEEvent? {
        guard !name.isEmpty else { return nil }
        let payload = dataLines.joined(separator: "\n")
        guard let data = payload.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return SSEEvent(event: name, data: [:])
        }

        let strings = json.reduce(into: [String: String]()) { partial, pair in
            if let value = pair.value as? String {
                partial[pair.key] = value
            } else if let array = pair.value as? [String] {
                partial[pair.key] = array.joined(separator: ",")
            } else {
                partial[pair.key] = String(describing: pair.value)
            }
        }
        return SSEEvent(event: name, data: strings)
    }
}
