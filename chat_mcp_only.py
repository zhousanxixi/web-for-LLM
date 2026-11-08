"""Same chat/tool path without RAG, for an ablation comparison."""

import asyncio
import os

os.environ["ENABLE_RAG"] = "0"
from chat import main

if __name__ == "__main__":
    asyncio.run(main())
