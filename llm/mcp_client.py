# File: llm/mcp_client.py
# Purpose: LangChain MCP client for loading MCP tools and creating a LangGraph ReAct agent

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT_DIR / ".env")


DEFAULT_MCP_SERVER_URL = "http://localhost:8001/mcp"
DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"

TEST_PROMPT = (
    "Use the sepsis retrieval tool to find relevant evidence about early "
    "identification of sepsis and the role of lactate levels. Summarize the "
    "key findings based only on the retrieved context."
)

DEFAULT_AGENT_PROMPT = """
You are a clinical data analysis assistant.

Use the available MCP retrieval tool whenever the user asks about sepsis data,
clinical evidence, papers, studies, extracted chunks, or source-backed analysis.

Base your answer on retrieved context when available.
"""


class MCPClient:
    def __init__(
        self,
        server_url: str = DEFAULT_MCP_SERVER_URL,
        model_name: str = DEFAULT_MODEL,
        prompt: str = DEFAULT_AGENT_PROMPT,
    ):
        self.server_url = server_url
        self.model_name = model_name
        self.prompt = prompt

        self.client = MultiServerMCPClient(
            {
                "sepsis_data_analysis": {
                    "transport": "http",
                    "url": self.server_url,
                }
            }
        )

        self.tools = []
        self.agent = None

    async def load_tools(self):
        self.tools = await self.client.get_tools()
        return self.tools

    async def create_agent(self):
        if not self.tools:
            await self.load_tools()

        model = ChatOpenAI(
            model=self.model_name,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

        self.agent = create_react_agent(
            model=model,
            tools=self.tools,
            prompt=self.prompt,
        )

        return self.agent

    async def initialize(self):
        await self.load_tools()
        await self.create_agent()
        return self

    async def ainvoke(self, prompt: str) -> dict[str, Any]:
        if self.agent is None:
            await self.initialize()

        return await self.agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            }
        )

    async def ask(self, prompt: str) -> str:
        result = await self.ainvoke(prompt)
        messages = result.get("messages", [])

        if not messages:
            return ""

        final_message = messages[-1]
        return getattr(final_message, "content", str(final_message))

    def get_tool_names(self) -> list[str]:
        return [tool.name for tool in self.tools]


async def invoke(prompt: str) -> dict[str, Any]:
    client = MCPClient()
    await client.initialize()
    return await client.ainvoke(prompt)


async def run(prompt: str) -> str:
    client = MCPClient()
    await client.initialize()
    return await client.ask(prompt)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Prompt string to send to the agent.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run the built-in sepsis test prompt.",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    if args.test:
        prompt = TEST_PROMPT
    else:
        prompt = " ".join(args.prompt).strip()

    if not prompt:
        raise SystemExit('Provide a prompt, for example: python llm/mcp_client.py "What does the sepsis data say?"')

    response = await run(prompt)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())