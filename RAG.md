# 多语言向量 RAG

原来的314条Wikivoyage记录按地理距离取前几条；现在全部类别参与检索，另补入5条有来源的官方背景摘要，共431个片段。

流程：JSONL → 480字符切块（80字符重叠）→ 本地多语言MiniLM Embedding（384维）→ SQLite持久化向量 → 向量余弦 + BM25关键词倒排统计 + 可选距离过滤 → 加权倒数排名融合 → 去重Top K → 带片段编号和来源的上下文。不是仅把全文塞进提示词。

默认模型：sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2，通过FastEmbed/ONNX在本机运行，首次下载约230 MB。无需额外Embedding API密钥。SQLite适合当前几百片段规模，不声称是大规模向量数据库服务。

```sh
python vector_rag.py build
python vector_rag.py status
python vector_rag.py search "雨天带老人去博物馆，轮椅设施"
```

`.cache/travel_vectors.sqlite3` 保存文本元数据及归一化float32向量；`.cache/models/`保存模型。网页请求不会下载模型/重建索引。资料或模型变化后运行build。索引指纹不匹配、离线模型不可用、维度不匹配时降级关键词检索，结果method与notes明确显示，不伪称已做向量检索。

可选远程Embedding：在.env设置RAG_EMBEDDING_BACKEND=api及EMBEDDING_BASE_URL、EMBEDDING_API_KEY、EMBEDDING_MODEL，再建库。服务需要兼容embeddings接口。DeepSeek聊天接口不等于Embedding接口；远程服务可能收费，实际调用由你自行配置后触发。

新增资料：knowledge/guides*.jsonl，一行一个JSON，必需id/name/text/source/source_date，可选kind/tags/latitude/longitude。source必须是HTTPS。修改后重建索引。不要上传私人资料到未确认的Embedding服务。

来源：知识库原文来自同学提供的Wikivoyage 2026-09导出，按原Markdown地区链接保留来源；部分具体营业时间和票价在原文中早于2026年。使用原文需要注明Wikivoyage contributors、CC BY-SA 4.0并保留来源。官方摘要保留2026-11-03/04的核查日期，不声称今天重新核查。静态资料不能证明当前营业、价格、天气、班次。检索分数不是置信概率。

网页新增「出行指南」独立查询。聊天在回答前检索，并提供search_travel_knowledge MCP工具进一步检索；返回引用。无相关证据时说明未知，不补造。真实模型引用是否正确仍需另做人工核对。

## 对比与评估

`python scripts/evaluate_retrieval.py` 对6个手写中英文案例输出Hit@5、MRR@5、检索耗时及实际召回条目。不调用付费模型；这些示例不代表泛化准确率。

同样问题分别用 `python chat_mcp_only.py`（MCP，无RAG）和 `python chat.py`（MCP + RAG）比较。两者使用相同分类、工具执行和系统提示；前者不注入检索上下文也不暴露知识检索工具。原chat_plain.py保留同学的普通无工具聊天基线；其系统提示不同，不能单独据此声称RAG提升。
