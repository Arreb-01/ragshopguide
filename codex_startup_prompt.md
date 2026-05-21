# Codex 启动 Prompt — RAG 多模态电商智能导购 AI Agent

> 字节 AI 全栈挑战赛项目启动文档
> 用法:把下方"启动 Prompt"部分整段复制喂给 Codex 作为首条消息

---

## 启动 Prompt(复制以下全部内容给 Codex)

````markdown
# 项目:基于 RAG 的多模态电商智能导购 AI Agent

## 项目背景

我在参加字节 AI 全栈挑战赛,题目是构建一个基于 RAG 的多模态电商智能导购 Agent。
我是单人参赛,3 周周期,后端用 Python,客户端用 Android 原生(Kotlin + Jetpack Compose)。

### 技术栈
- **后端**: Python + FastAPI + Chroma(向量库)+ 豆包 API
- **客户端**: Android 原生,Kotlin + Jetpack Compose
- **大模型**: Doubao-Seed-2.0-lite,通过火山方舟 API 调用
  - BaseAPI: https://ark.cn-beijing.volces.com/api/v3/
  - Model: ep-20260514111645-lmgt2
  - APIKey: 请在 `server/.env` 中通过 `ARK_API_KEY` 配置，禁止写入仓库文档
  - 兼容 OpenAI SDK,可以用 openai 库直接调
- **Embedding 模型**: Doubao-embedding(同一套 API,模型名 doubao-embedding-text-240715 或类似,需要确认)
- **多模态**: Doubao VLM(同一套 API),用于截图理解

### 数据集
赛方提供 100 条电商商品数据,放在 `dataset/ecommerce_agent_dataset/` 下,4 个品类目录:
- `1_美妆护肤/` - 25 条,子品类:精华/化妆水/防晒/面霜/洁面/眼霜/卸妆等
- `2_数码电子/` - 25 条,子品类:智能手机/笔记本电脑/平板电脑/真无线耳机
- `3_服饰运动/` - 25 条,子品类:跑步鞋/篮球鞋/徒步鞋/T恤/卫衣/运动裤/背包/帽子
- `4_食品生活/` - 25 条,子品类:咖啡/茶饮/碳酸饮料/功能饮料/牛奶/酸奶/坚果/方便食品/调味品

每个品类目录下:
- `data/p_xxx_NNN.json` - 商品 JSON 数据
- `images/p_xxx_NNN_live.jpg` - 商品实拍图

### 商品 JSON 结构(关键)
每个 JSON 文件包含以下字段:
```json
{
  "product_id": "p_digital_001",
  "title": "商品标题",
  "brand": "品牌",
  "category": "数码电子",
  "sub_category": "智能手机",
  "base_price": 8999.0,
  "image_path": "2_数码电子/images/p_digital_001_live.jpg",
  "skus": [
    {
      "sku_id": "s_xxx",
      "properties": {"存储": "256GB", "颜色": "宇宙橙"},
      "price": 8999.0
    }
    // ... 多个 SKU
  ],
  "rag_knowledge": {
    "marketing_description": "营销话术,500 字左右,商家自述卖点",
    "official_faq": [
      {"question": "...", "answer": "..."}
      // 3-6 条官方问答
    ],
    "user_reviews": [
      {"nickname": "用户昵称", "rating": 1-5, "content": "评价内容"}
      // 3-5 条用户评价,有好评有差评
    ]
  }
}
```

### 核心差异化设计:三源知识分离

普通团队会把所有文本混在一起做 embedding。我的设计是把每个商品的知识源拆成三类,
检索时显式分离,生成回复时按来源标注:

- **marketing_description**(商家话术)→ 适合回答"这是什么、有什么卖点"
- **official_faq**(官方问答)→ 适合回答"参数细节、使用方法"
- **user_reviews**(真实评价)→ 适合回答"真的好用吗、值不值买"

回复时引用要标明来源,例如:"📘 官方说续航 1 天,👥 但用户实测重度使用一天要充 2 次"
这样既反幻觉,又比纯营销话术更可信。

### Chunk 切分策略
每个商品切成多个 chunk,每个 chunk 带元数据,便于后续过滤检索:
- `chunk_basic`: 商品基础信息(标题 + 品类 + 品牌 + 价格 + SKU 概览)
- `chunk_marketing`: 营销描述(整段)
- `chunk_faq_N`: 每条 FAQ 一个 chunk(question + answer 拼接)
- `chunk_review_N`: 每条评论一个 chunk

每个 chunk 的 metadata 必须包含:
- `product_id`: 商品 ID(用于回溯)
- `source_type`: basic / marketing / faq / review
- `category`: 一级品类
- `sub_category`: 子品类
- `brand`: 品牌
- `base_price`: 基础价(float)
- `rating`: 仅 review 类型有,1-5

### 项目目录约定
```
/server          # Python 后端
  /app
    /api         # FastAPI 路由
    /rag         # RAG 链路核心
    /llm         # 豆包 API 封装
    /data        # 数据加载与处理
  /scripts       # 数据导入等脚本
  requirements.txt
/client-android  # Android 原生客户端
  /...
/docs            # 技术文档
/dataset         # 赛方数据(已存在,只读)
```

---

## 当前任务:Week 1 Day 1-2,后端 MVP

请按以下顺序完成,**每完成一步先告诉我结果再继续下一步**,不要一次性把所有代码生成完。

### Step 1: 项目脚手架
- 在 `/server` 下建立 Python 项目结构
- 创建 `requirements.txt`,包含:fastapi, uvicorn, chromadb, openai, python-dotenv, pydantic
- 创建 `.env.example`,把豆包 API key 等配置放进去(实际 .env 我自己填)
- 创建 `app/llm/doubao_client.py`,封装豆包的 chat 和 embedding 调用(使用 openai SDK 的 base_url 参数指向方舟)

### Step 2: 数据加载与切 chunk
- 在 `app/data/loader.py` 写一个函数,扫描 `dataset/ecommerce_agent_dataset/` 下所有 JSON
- 按上面定义的策略切 chunk,返回 `List[Dict]`,每个 dict 包含:`id`, `text`, `metadata`
- 在 `scripts/build_index.py` 写一个一次性脚本:
  - 加载所有 chunk
  - 调用豆包 embedding API 批量生成向量(注意 batch_size,避免触发限流)
  - 写入本地 Chroma collection,持久化到 `server/data/chroma/`
- 打印一些 stats:总商品数、总 chunk 数、各 source_type 的 chunk 数

### Step 3: 检索能力测试
- 写一个 `app/rag/retriever.py`,提供 `retrieve(query: str, top_k: int = 5, filters: dict = None)` 方法
- 写一个简单的 CLI 测试脚本 `scripts/test_retrieve.py`,接受命令行查询,打印 top-k 结果(含 source_type 和 product_id)
- 用这些 query 测试一下:
  - "推荐一款适合油皮的洗面奶"
  - "200 元以下的耳机"
  - "iPhone 续航好不好"
  - "用户对小米手机评价怎么样"

### Step 4: 基础 RAG 链路(非流式版,先验证质量)
- 在 `app/rag/pipeline.py` 写 `chat(query: str, history: list = None) -> dict` 方法
- 流程:用户 query → retrieve → 拼接 prompt → 调豆包 chat → 返回 `{"reply": str, "product_ids": [str]}`
- Prompt 设计要求:
  - 明确告诉模型库内有哪些商品(注入检索到的 chunk)
  - 严禁编造库外商品/价格/优惠信息
  - 引用信息要标明来源类型(官方 vs 用户)
  - 回复格式:先文字解释,再用特殊标记列出推荐商品 ID,例如 `[[PRODUCT:p_digital_001]]`
- 写一个 `scripts/test_chat.py`,跑几个 query 看回复质量

### Step 5: SSE 流式接口
- 在 `app/api/chat.py` 写 `POST /chat` 接口,接受 `{query, session_id, history}`,返回 SSE 流
- 流式返回每个 token,前端可以边接收边渲染
- 在主入口 `app/main.py` 起 FastAPI
- 提供 curl 测试命令,我自己跑一下验证

### 我会用到的关键约束
- **代码要有注释**,尤其 RAG 链路和 Prompt 构造部分,我答辩要解释原理
- **Prompt 单独成文件**(放在 `app/rag/prompts.py`),不要硬编码在业务逻辑里
- **配置走环境变量**,API key 等敏感信息不要写死
- **错误处理要有**,豆包 API 调用要加超时和重试
- **不要过度工程化**,这是 3 周的比赛项目,不需要 Kubernetes / Celery / Redis 等

请确认你理解了项目背景,然后从 Step 1 开始执行。
````

---

## 使用说明

1. **直接复制上方代码块整段喂给 Codex** 作为第一条消息
2. **后续每个阶段**(比如 Day 3-7 做 Android,Week 2 做差异化),只需要保留"项目背景"部分,替换"当前任务"部分
3. **如果 Codex 跳步**(比如一上来就把 5 步代码全写完),打断它:"按 Step 1 开始,完成后告诉我结果再继续"

## Prompt 中特意设计的小细节

- **`source_type` 元数据**:虽然 MVP 阶段不一定用上,但提前打好桩,Week 2 做三源分离时直接能用,不用重新切 chunk
- **回复格式约定 `[[PRODUCT:xxx]]`**:这个约定让 Android 端可以用正则解析出商品 ID,然后在对应位置插入卡片组件,是流式渲染商品卡的关键技巧
- **Prompt 单独成文件**:Week 2 会反复调 Prompt,放业务代码里改一次都得找半天
- **每步停一下汇报**:Codex 容易一把梭写一堆,review 不动就埋雷,强制它分步走

## 可能会遇到的坑

1. **豆包 embedding 模型名**: Prompt 里写的 `doubao-embedding-text-240715` 是猜的,实际名字让 Codex 查方舟控制台或文档。如果找不到也可以用本地 embedding(`bge-small-zh` 之类),只要把这个决策记下来答辩能讲清楚。
2. **Chroma 中文 embedding 维度匹配**:豆包 embedding 输出维度要和 Chroma collection 创建时一致,第一次入库前确认一下。
3. **方舟 API 流式调用细节**:`openai` SDK 调火山方舟的流式接口大部分情况可用,但偶有兼容性问题,如果报错让 Codex 改成直接用 `requests` 调 REST。

---

## 后续阶段预告

跑通 Day 1-2 后,后续阶段的 Prompt 会按以下节奏给出:

- **Day 3-7**: Android 端聊天 UI + SSE 接收 + 商品卡片 + 前后端串通
- **Week 2**: 三源知识分离 + 多轮上下文 + 反选语义 + 对比决策 + 健身套装场景
- **Week 3**: 截屏识别多模态 + 评测体系 + 性能优化 + Demo 视频 + 文档
