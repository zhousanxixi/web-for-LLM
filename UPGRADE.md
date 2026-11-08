# 本次改动（2026-11-09）

1. 本地Embedding + SQLite向量库，融合关键词和地理距离；来源引用与索引失效降级。见RAG.md。
2. 美食保持仅OpenStreetMap。查询由node扩展为nwr，覆盖点、建筑轮廓和关系；默认8条、最多15条，不再默认无限返回。没有调用食环署。
3. 分类改为本地轻量规则，省掉一次模型分类请求；模型同轮互不依赖工具并行执行。HTTP短缓存、重复Overpass请求合并、成功空列表立即返回、速率限制不绕过。公共Overpass总体等待预算12秒（网络栈实际时间可能略有出入）。
4. 流式回答、查询步骤和证据事件；进行中轻微闪烁，完成即停止，尊重系统减少动画设置。展示实际操作状态，不展示模型私有推理过程。客户端断开会取消任务；同步SDK/HTTP线程的终止仍取决于其超时。
5. 恢复出行概览，天气+勾选的美食/景点并行；不强制每个问题调用所有API。单项失败保留成功项。
6. 地图路线增加步行、驾车、骑行、徒步；OpenRouteService GeoJSON、距离、预计时间和逐步指引，Leaflet画真实路线。缺少路线密钥或接口失败提供相同交通方式的外部地图链接，不虚构折线/距离/时间。地铁换乘与到站功能保留。
7. 修复知识拆分脚本的knowledge/knowledge输出路径。新增独立知识MCP服务。原有weather/food/transport服务保留。

## 启动
Python 3.11+：
```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python vector_rag.py build
python web_app.py
```
Windows PowerShell用 `.\.venv\Scripts\python.exe` 执行pip、vector_rag.py和web_app.py，无需激活。
打开 http://127.0.0.1:8765 。端口占用可 `python web_app.py --port 8766`。

聊天需要在.env填写自己的DEEPSEEK_API_KEY；站内路线需OPENROUTESERVICE_API_KEY。这两个服务分别配置，密钥只保留后端。不要把.env或.venv打包给同学。没有密钥时仍可查指南、美食、天气、港铁及打开外部地图。

## 验证
```sh
python -m unittest discover -s tests -v
```
真实Embedding检索测试需先build，否则会跳过该项。接口单元测试中使用明确的模拟响应；它们不证明公共服务此刻可用，也不证明真实模型的回答质量。详见VALIDATION.md。

本机指定的VS Code项目已准备好.venv、模型缓存及向量库。分享用压缩包不包含.venv、.env和模型缓存；同学解压后需按上述步骤安装并运行vector_rag.py build。
