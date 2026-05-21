import Foundation

@MainActor
final class ProductStore: ObservableObject {
    @Published private(set) var productsByID: [String: Product] = [:]
    @Published private(set) var isLoaded = false

    private let service: ChatService

    init(service: ChatService = ChatService()) {
        self.service = service
    }

    func load() async {
        guard !isLoaded else { return }
        do {
            let products = try await service.fetchProducts()
            productsByID = Dictionary(uniqueKeysWithValues: products.map { ($0.id, $0) })
            isLoaded = true
        } catch {
            isLoaded = false
        }
    }

    func product(for id: String) -> Product? {
        productsByID[id]
    }

    func imageURL(for product: Product) -> URL? {
        service.imageURL(for: product)
    }
}
