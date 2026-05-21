import SwiftUI

struct ChatView: View {
    @StateObject private var viewModel = ChatViewModel()
    @StateObject private var productStore = ProductStore()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 16) {
                            if viewModel.messages.isEmpty {
                                promptGrid
                            }

                            ForEach(viewModel.messages) { message in
                                MessageRow(
                                    message: message,
                                    productStore: productStore
                                )
                                .id(message.id)
                            }
                        }
                        .padding(16)
                    }
                    .onChange(of: viewModel.messages) { _, messages in
                        guard let last = messages.last else { return }
                        withAnimation(.easeOut(duration: 0.2)) {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        }
                    }
                }

                inputBar
            }
            .navigationTitle("AI 导购参谋")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                await productStore.load()
            }
        }
    }

    private var promptGrid: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("你想买什么？")
                .font(.title2.weight(.bold))
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: 10)], spacing: 10) {
                ForEach(viewModel.promptTiles, id: \.self) { prompt in
                    Button {
                        viewModel.sendTile(prompt)
                    } label: {
                        Text(prompt)
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(.primary)
                            .multilineTextAlignment(.leading)
                            .frame(maxWidth: .infinity, minHeight: 54, alignment: .leading)
                            .padding(12)
                            .background(Color(.secondarySystemBackground))
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 12)
    }

    private var inputBar: some View {
        HStack(spacing: 10) {
            TextField("描述你的需求", text: $viewModel.inputText, axis: .vertical)
                .lineLimit(1...4)
                .textFieldStyle(.roundedBorder)

            Button {
                viewModel.sendCurrentInput()
            } label: {
                Image(systemName: "paperplane.fill")
                    .frame(width: 34, height: 34)
            }
            .disabled(viewModel.isStreaming || viewModel.inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
        .padding(12)
        .background(.bar)
    }
}

private struct MessageRow: View {
    let message: ChatMessage
    @ObservedObject var productStore: ProductStore

    var body: some View {
        HStack {
            if message.role == .user {
                Spacer(minLength: 40)
            }

            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 10) {
                ForEach(message.blocks) { block in
                    blockView(block)
                }
                if message.isStreaming {
                    ProgressView()
                        .controlSize(.small)
                }
            }
            .padding(12)
            .background(message.role == .user ? Color(red: 0.34, green: 0.29, blue: 0.78) : Color(.secondarySystemBackground))
            .foregroundStyle(message.role == .user ? .white : .primary)
            .clipShape(RoundedRectangle(cornerRadius: 16))

            if message.role == .assistant {
                Spacer(minLength: 40)
            }
        }
    }

    @ViewBuilder
    private func blockView(_ block: MessageBlock) -> some View {
        switch block {
        case .text(let text):
            Text(text)
                .font(.body)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
        case .productCards(let ids):
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(ids, id: \.self) { id in
                        if let product = productStore.product(for: id) {
                            ProductCardView(
                                product: product,
                                imageURL: productStore.imageURL(for: product)
                            )
                        } else {
                            MissingProductView(productID: id)
                        }
                    }
                }
            }
        case .comparison(let ids):
            VStack(alignment: .leading, spacing: 6) {
                Text("对比商品")
                    .font(.headline)
                ForEach(ids, id: \.self) { id in
                    if let product = productStore.product(for: id) {
                        Text("\(product.title) · ¥\(product.basePrice, specifier: "%.0f")")
                            .font(.subheadline)
                    } else {
                        Text(id)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct MissingProductView: View {
    let productID: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Image(systemName: "shippingbox")
                .font(.system(size: 28))
                .foregroundStyle(.secondary)
            Text(productID)
                .font(.caption)
                .lineLimit(2)
        }
        .frame(width: 148, height: 190, alignment: .center)
        .background(Color(.systemGray6))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
