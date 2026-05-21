import Foundation

struct Product: Identifiable, Decodable, Equatable {
    let productID: String
    let title: String
    let brand: String
    let category: String
    let subCategory: String
    let basePrice: Double
    let imagePath: String
    let imageURL: String
    let tags: [String]

    var id: String { productID }

    enum CodingKeys: String, CodingKey {
        case productID = "product_id"
        case title
        case brand
        case category
        case subCategory = "sub_category"
        case basePrice = "base_price"
        case imagePath = "image_path"
        case imageURL = "image_url"
        case tags
    }
}

struct ProductsResponse: Decodable {
    let products: [Product]
}

struct ChatHistoryItem: Encodable {
    let role: String
    let content: String
}

struct ChatRequestBody: Encodable {
    let query: String
    let sessionID: String
    let history: [ChatHistoryItem]

    enum CodingKeys: String, CodingKey {
        case query
        case sessionID = "session_id"
        case history
    }
}

struct SSEEvent: Equatable {
    let event: String
    let data: [String: String]
}

enum MessageRole: String, Equatable {
    case user
    case assistant
}

enum MessageBlock: Equatable, Identifiable {
    case text(String)
    case productCards([String])
    case comparison([String])

    var id: String {
        switch self {
        case .text(let value):
            return "text-\(value.hashValue)"
        case .productCards(let ids):
            return "products-\(ids.joined(separator: "-"))"
        case .comparison(let ids):
            return "comparison-\(ids.joined(separator: "-"))"
        }
    }
}

struct ChatMessage: Identifiable, Equatable {
    let id: UUID
    let role: MessageRole
    var blocks: [MessageBlock]
    var isStreaming: Bool
    let createdAt: Date

    init(
        id: UUID = UUID(),
        role: MessageRole,
        blocks: [MessageBlock],
        isStreaming: Bool = false,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.role = role
        self.blocks = blocks
        self.isStreaming = isStreaming
        self.createdAt = createdAt
    }

    var textContent: String {
        blocks.compactMap { block in
            if case .text(let text) = block {
                return text
            }
            return nil
        }.joined()
    }
}
