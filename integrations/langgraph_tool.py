"""
Loopuman LangChain/LangGraph Tool
==================================
Give LangChain and LangGraph agents access to real human workers.

Install: pip install loopuman langchain-core
Usage:
    from loopuman_langchain import AskHumanTool
    agent = create_react_agent(llm, [AskHumanTool(api_key="your_key")])
"""

import os
import requests
from typing import Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


LOOPUMAN_API_BASE = os.getenv("LOOPUMAN_API_URL", "https://api.loopuman.com")


class AskHumanInput(BaseModel):
    task: str = Field(description="Clear description of what you need the human to do")
    budget_cents: int = Field(default=50, description="Payment in cents. Minimum 10.", ge=10)
    timeout_seconds: int = Field(default=300, description="Max wait time in seconds", ge=30, le=3600)


class AskHumanTool(BaseTool):
    """Ask a real human worker to complete a task via Loopuman."""

    name: str = "ask_human"
    description: str = (
        "Ask a real human worker to complete a task. Use for verification, "
        "judgment, content moderation, fact-checking, subjective evaluation, "
        "or real-world observation. Returns the human's response. "
        "Cost: $0.10-$1.00. Response time: 30-120 seconds."
    )
    args_schema: Type[BaseModel] = AskHumanInput
    api_key: str = ""

    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("LOOPUMAN_API_KEY", "")

    def _run(self, task: str, budget_cents: int = 50, timeout_seconds: int = 300) -> str:
        if not self.api_key:
            return "Error: LOOPUMAN_API_KEY not set. Get one free at https://loopuman.com/developers"

        try:
            response = requests.post(
                f"{LOOPUMAN_API_BASE}/api/v1/tasks/sync",
                headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
                json={
                    "title": task[:200],
                    "description": task,
                    "budget": budget_cents,
                    "timeout_seconds": timeout_seconds,
                },
                timeout=timeout_seconds + 10,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("submission"):
                    return data["submission"]["content"]
                return "No human responded in time. Try increasing budget or timeout."
            return f"API error {response.status_code}: {response.text}"

        except requests.Timeout:
            return "Timed out waiting for human response."
        except Exception as e:
            return f"Error: {str(e)}"

    async def _arun(self, task: str, budget_cents: int = 50, timeout_seconds: int = 300) -> str:
        return self._run(task, budget_cents, timeout_seconds)


class PostTaskInput(BaseModel):
    title: str = Field(description="Short title for the task")
    description: str = Field(description="Detailed instructions")
    budget_cents: int = Field(default=50, ge=10)
    category: str = Field(default="general")


class PostTaskTool(BaseTool):
    """Post an async task for human workers on Loopuman."""

    name: str = "post_task_to_humans"
    description: str = "Post async task for humans. Returns task_id to check later."
    args_schema: Type[BaseModel] = PostTaskInput
    api_key: str = ""

    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("LOOPUMAN_API_KEY", "")

    def _run(self, title: str, description: str, budget_cents: int = 50, category: str = "general") -> str:
        response = requests.post(
            f"{LOOPUMAN_API_BASE}/api/v1/tasks",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json={"title": title, "description": description, "budget": budget_cents, "category": category},
        )
        if response.status_code == 200:
            return f"Task created: {response.json()['task']['id']}"
        return f"Error: {response.status_code}"


class CheckTaskInput(BaseModel):
    task_id: str = Field(description="Task UUID")


class CheckTaskTool(BaseTool):
    """Check status of a Loopuman task."""

    name: str = "check_human_task"
    description: str = "Check if a human has completed a Loopuman task."
    args_schema: Type[BaseModel] = CheckTaskInput
    api_key: str = ""

    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("LOOPUMAN_API_KEY", "")

    def _run(self, task_id: str) -> str:
        response = requests.get(
            f"{LOOPUMAN_API_BASE}/api/v1/tasks/{task_id}",
            headers={"X-API-Key": self.api_key},
        )
        if response.status_code == 200:
            task = response.json().get("task", {})
            if task.get("status") == "completed" and task.get("submission"):
                return task["submission"]["content"]
            return f"Status: {task.get('status')}"
        return f"Error: {response.status_code}"


# ── LangGraph example ──────────────────────────────────────────────

if __name__ == "__main__":
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent

    llm = ChatOpenAI(model="gpt-4")
    api_key = os.getenv("LOOPUMAN_API_KEY")

    tools = [
        AskHumanTool(api_key=api_key),
        PostTaskTool(api_key=api_key),
        CheckTaskTool(api_key=api_key),
    ]

    agent = create_react_agent(llm, tools)

    result = agent.invoke({
        "messages": [
            ("user", "Ask a human if this headline is clickbait: 'You won't BELIEVE what happened next!'")
        ]
    })

    print(result["messages"][-1].content)
