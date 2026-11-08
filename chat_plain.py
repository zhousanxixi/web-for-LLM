import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

SYSTEM_PROMPT = "你是一个普通的聊天助手。用中文回答用户的各种问题。"


def answer(llm, messages, question: str) -> str:
    messages.append({"role": "user", "content": question})
    response = llm.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
    )
    #print(response)
    text = response.choices[0].message.content or ""
    #print(text)
    messages.append({"role": "assistant", "content": text})
    return text


def main() -> None:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("没有读到 DEEPSEEK_API_KEY。请把它写在项目目录的 .env 里。")

    llm = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if len(sys.argv) > 1:
        print("助手:", answer(llm, messages, " ".join(sys.argv[1:])))
        return

    while True:
        question = input("你: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue
        print(messages)
        print("助手:", answer(llm, messages, question))


if __name__ == "__main__":
    main()
