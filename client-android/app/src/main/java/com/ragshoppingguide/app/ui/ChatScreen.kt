package com.ragshoppingguide.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.ragshoppingguide.app.core.MessageBlock
import com.ragshoppingguide.app.data.ApiConfig
import com.ragshoppingguide.app.data.Product

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(viewModel: ChatViewModel = viewModel()) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("RAGShopGuide") })
        },
        bottomBar = {
            ChatInputBar(
                input = state.input,
                isStreaming = state.isStreaming,
                onInputChange = viewModel::updateInput,
                onSend = viewModel::sendCurrentInput,
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                if (state.messages.isEmpty()) {
                    PromptTiles(
                        prompts = state.promptTiles,
                        serverBaseUrl = state.serverBaseUrl,
                        serverInput = state.serverInput,
                        errorMessage = state.errorMessage,
                        isStreaming = state.isStreaming,
                        onServerInputChange = viewModel::updateServerInput,
                        onApplyServer = viewModel::applyServerBaseUrl,
                        onPromptClick = viewModel::sendPrompt,
                    )
                }
            }

            items(state.messages, key = { it.id }) { message ->
                MessageBubble(
                    message = message,
                    productsById = state.productsById,
                )
            }

            item {
                Spacer(modifier = Modifier.height(8.dp))
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PromptTiles(
    prompts: List<String>,
    serverBaseUrl: String,
    serverInput: String,
    errorMessage: String?,
    isStreaming: Boolean,
    onServerInputChange: (String) -> Unit,
    onApplyServer: () -> Unit,
    onPromptClick: (String) -> Unit,
) {
    Column(
        modifier = Modifier.padding(vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(
            text = "你想买什么？",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
        )
        ServerEndpointEditor(
            serverBaseUrl = serverBaseUrl,
            serverInput = serverInput,
            errorMessage = errorMessage,
            isStreaming = isStreaming,
            onServerInputChange = onServerInputChange,
            onApplyServer = onApplyServer,
        )
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            prompts.forEach { prompt ->
                Button(
                    onClick = { onPromptClick(prompt) },
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant,
                        contentColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    ),
                    modifier = Modifier.widthIn(min = 150.dp, max = 220.dp),
                ) {
                    Text(
                        text = prompt,
                        style = MaterialTheme.typography.bodyMedium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
private fun ServerEndpointEditor(
    serverBaseUrl: String,
    serverInput: String,
    errorMessage: String?,
    isStreaming: Boolean,
    onServerInputChange: (String) -> Unit,
    onApplyServer: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedTextField(
                value = serverInput,
                onValueChange = onServerInputChange,
                label = { Text("服务地址") },
                modifier = Modifier.weight(1f),
                singleLine = true,
                enabled = !isStreaming,
            )
            Button(
                onClick = onApplyServer,
                enabled = !isStreaming && serverInput.isNotBlank(),
                shape = RoundedCornerShape(12.dp),
            ) {
                Text("应用")
            }
        }
        Text(
            text = "当前：$serverBaseUrl",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        if (errorMessage != null) {
            Text(
                text = errorMessage,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.error,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun MessageBubble(
    message: ChatMessageUi,
    productsById: Map<String, Product>,
) {
    val isUser = message.role == ChatRole.User
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        Surface(
            color = if (isUser) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant,
            contentColor = if (isUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant,
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.widthIn(max = 340.dp),
        ) {
            Column(
                modifier = Modifier.padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                message.blocks.forEach { block ->
                    MessageBlockView(
                        block = block,
                        productsById = productsById,
                    )
                }
                if (message.isStreaming) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        strokeWidth = 2.dp,
                    )
                }
            }
        }
    }
}

@Composable
private fun MessageBlockView(
    block: MessageBlock,
    productsById: Map<String, Product>,
) {
    when (block) {
        is MessageBlock.Text -> Text(
            text = block.value,
            style = MaterialTheme.typography.bodyLarge,
        )
        is MessageBlock.SourceText -> SourceTextBlock(block = block)
        is MessageBlock.ProductCards -> ProductCardRow(
            productIds = block.productIds,
            productsById = productsById,
        )
        is MessageBlock.Compare -> CompareBlock(
            productIds = block.productIds,
            productsById = productsById,
        )
    }
}

@Composable
private fun SourceTextBlock(block: MessageBlock.SourceText) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(
            modifier = Modifier
                .width(4.dp)
                .height(54.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(sourceColor(block.sourceType)),
        )
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = sourceTitle(block.sourceType),
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = sourceColor(block.sourceType),
            )
            Text(
                text = block.value,
                style = MaterialTheme.typography.bodyLarge,
            )
        }
    }
}

private fun sourceTitle(sourceType: String): String {
    return when (sourceType) {
        "official" -> "官方信息"
        "review" -> "用户评价"
        "marketing" -> "商家话术"
        "summary" -> "综合建议"
        else -> "来源信息"
    }
}

private fun sourceColor(sourceType: String): Color {
    return when (sourceType) {
        "official" -> Color(0xFF2F6FED)
        "review" -> Color(0xFFE07A2D)
        "marketing" -> Color(0xFF6F7280)
        "summary" -> Color(0xFF6750D8)
        else -> Color(0xFF6F7280)
    }
}

@Composable
private fun ProductCardRow(
    productIds: List<String>,
    productsById: Map<String, Product>,
) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        items(productIds) { productId ->
            val product = productsById[productId]
            if (product == null) {
                MissingProductCard(productId = productId)
            } else {
                ProductCard(product = product)
            }
        }
    }
}

@Composable
private fun ProductCard(product: Product) {
    Card(
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        modifier = Modifier.widthIn(min = 150.dp, max = 150.dp),
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            AsyncImage(
                model = ApiConfig.resolve(product.imageUrl),
                contentDescription = product.title,
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f)
                    .clip(RoundedCornerShape(10.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                contentScale = ContentScale.Crop,
            )
            Text(
                text = product.title,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = product.brand,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = "¥%.0f".format(product.basePrice),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
            )
        }
    }
}

@Composable
private fun MissingProductCard(productId: String) {
    Box(
        modifier = Modifier
            .size(width = 150.dp, height = 190.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(12.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = productId,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun CompareBlock(
    productIds: List<String>,
    productsById: Map<String, Product>,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = "对比商品",
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.Bold,
        )
        productIds.forEach { productId ->
            val product = productsById[productId]
            CompareProductCard(productId = productId, product = product)
        }
    }
}

@Composable
private fun CompareProductCard(
    productId: String,
    product: Product?,
) {
    Surface(
        color = Color.White,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                text = product?.title ?: productId,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            if (product != null) {
                Text(
                    text = "${product.brand} · ${product.category}/${product.subCategory}",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = "¥%.0f".format(product.basePrice),
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}

@Composable
private fun ChatInputBar(
    input: String,
    isStreaming: Boolean,
    onInputChange: (String) -> Unit,
    onSend: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .imePadding()
            .padding(12.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        OutlinedTextField(
            value = input,
            onValueChange = onInputChange,
            placeholder = { Text("描述你的购物需求") },
            modifier = Modifier.weight(1f),
            maxLines = 4,
            enabled = !isStreaming,
        )
        Button(
            onClick = onSend,
            enabled = input.isNotBlank() && !isStreaming,
            shape = RoundedCornerShape(12.dp),
        ) {
            Text("发送")
        }
    }
}
