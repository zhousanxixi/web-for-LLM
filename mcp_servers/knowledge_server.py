from mcp.server import MCPServer
from vector_rag import search

mcp = MCPServer("Hong Kong Travel Knowledge")


@mcp.tool()
def search_travel_knowledge(query: str, limit: int = 5) -> dict:
    """检索香港出行、景点、设施及地名背景。多语言向量+关键词检索，返回片段、来源和日期；不是实时营业/票价/天气查询。"""
    return search(query, limit)
