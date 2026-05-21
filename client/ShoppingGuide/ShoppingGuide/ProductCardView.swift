import SwiftUI

struct ProductCardView: View {
    let product: Product
    let imageURL: URL?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            AsyncImage(url: imageURL) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .scaledToFill()
                case .failure:
                    Image(systemName: "photo")
                        .font(.system(size: 28))
                        .foregroundStyle(.secondary)
                default:
                    ProgressView()
                }
            }
            .frame(width: 124, height: 124)
            .background(Color(.systemGray6))
            .clipShape(RoundedRectangle(cornerRadius: 10))

            Text(product.title)
                .font(.subheadline.weight(.semibold))
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)

            Text(product.brand)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)

            Text("¥\(product.basePrice, specifier: "%.0f")")
                .font(.headline.weight(.bold))
                .foregroundStyle(Color(red: 0.34, green: 0.29, blue: 0.78))
        }
        .frame(width: 148, alignment: .leading)
        .padding(12)
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color(.systemGray5), lineWidth: 1)
        )
    }
}
