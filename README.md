# RAGShopGuide

RAGShopGuide 是一个基于 FastAPI、Chroma、豆包 API 和 Android 原生 Kotlin 的多模态电商智能导购 demo。当前目标是完成 PRD Week 2 的差异化演示闭环：三源标注、反选/排除、多轮约束、结构化对比和跨品类场景推荐。

## 当前进展

- 后端已完成商品数据加载、三源 chunk、Chroma 检索、RAG Prompt、`/chat` SSE。
- 后端已补齐 `GET /products`、`/static/images/...` 和 `POST /eval/run` 规则评测入口。
- 后端已加入 Week 2 `QueryPlan`：价格上限、排除品牌/关键词、多轮约束、对比商品和健身入门场景识别。
- 后端已对真实豆包输出做协议兜底：模型漏掉来源、商品或对比标记时，会基于检索结果补齐客户端渲染所需 marker。
- 后端已为主 demo 增加快速本地召回：健身入门场景、iPhone 17 Pro、华为 Pura 90 不再依赖外部 embedding 检索，降低现场等待风险。
- Android 原生客户端为正式主线：Kotlin + Jetpack Compose，支持聊天页、6 个预设瓷砖、SSE 接收、商品卡片缓存、三源来源块、商品卡片和对比卡片。
- 原 SwiftUI 客户端保留为参考实现，不作为比赛交付主线。
- 项目已初始化 git，`.env`、缓存和本地 Chroma 索引已排除入库。
- 2026-05-21 已用真实豆包链路验证四步 Week 2 demo：健身入门、排除 Nike+预算、iPhone 续航、iPhone/华为对比。
- 2026-05-22 真实链路复测：四步 demo 的 retrieval 耗时为 53-192ms；首 token 仍主要受豆包生成影响，约 8-26s。

## Backend

```powershell
cd server
python -m pip install -r requirements.txt
python -m pytest tests -q
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Required local config: copy `server/.env.example` to `server/.env` and set `ARK_API_KEY`.

Useful endpoints:

- `GET /health`
- `GET /products`
- `POST /chat`
- `POST /eval/run`
- `GET /static/images/{dataset-relative-image-path}`

Week 2 marker protocol:

- `[[SOURCE:official|内容]]`
- `[[SOURCE:review|内容]]`
- `[[SOURCE:marketing|内容]]`
- `[[SOURCE:summary|内容]]`
- `[[PRODUCT:p_xxx]]`
- `[[COMPARE:p_xxx,p_yyy]]`

`/chat` SSE 还会返回非破坏性耗时字段：

- `meta.timings_ms.retrieval`
- `done.timings_ms.first_token`
- `done.timings_ms.total`

The current `.env.example` points `CHROMA_PERSIST_DIR` to `C:/tmp/ecommerce_agent_chroma`, matching the existing local index.

## Android Client

Open `client-android` with Android Studio on Windows, then run the `app` configuration on an Android emulator or Android device.

Backend address:

- Android emulator default: `http://10.0.2.2:8000`
- Android physical device: enter `http://<Windows WLAN IPv4>:8000` in the app's `服务地址` field and tap `应用`

For emulator/device access, start the backend with:

```powershell
cd server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On the current Windows machine, the WLAN IPv4 observed during setup was `172.24.7.60`, so a real Android phone on the same Wi-Fi can use `http://172.24.7.60:8000` while that IP remains assigned. If products do not load on the phone, check Windows Firewall inbound access for TCP port `8000`.

Core parser tests can run without Android SDK:

```powershell
cd client-android
gradlew.bat :core:test
```

If Gradle test discovery fails under a Chinese path on Windows, move the repo to an ASCII-only path or run the tests from Android Studio.

## Demo Path

1. Tap `健身入门装备怎么配`.
2. Ask `不要 Nike，预算压到 1000`.
3. Ask `iPhone 17 Pro 续航好不好`.
4. Ask `iPhone 17 Pro 和华为 Pura 90 对比一下`.

## Security

An Ark API key had appeared in the startup prompt. It has been removed from repo files, but the key should still be rotated in the Volcengine Ark console because it was exposed in plaintext before cleanup.

## License

This project is released under the MIT License. See [LICENSE](LICENSE).
