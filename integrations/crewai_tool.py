"""
Loopuman CrewAI Tool
====================
Give CrewAI agents access to real human workers.

Install: pip install loopuman crewai
Usage:
    from loopuman_crewai import AskHumanTool
    agent = Agent(tools=[AskHumanTool(api_key="your_key")])
"""

import os
import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional


LOOPUMAN_API_BASE = os.getenv("LOOPUMAN_API_URL", "https://api.loopuman.com")


class AskHumanInput(BaseModel):
    task: str = Field(description="Clear description of what you need the human to do")
    budget_cents: int = Field(default=50, description="Payment in cents. Minimum 10.", ge=10)
    timeout_seconds: int = Field(default=300, description="How long to wait for response", ge=30, le=3600)


class AskHumanTool(BaseTool):
    name: str = "ask_human"
    description: str = (
        "Ask a real human worker to complete a task via Loopuman. "
        "Use for verification, judgment, content moderation, fact-checking, "
        "subjective evaluation, or real-world observation. "
        "Returns the human's response. Cost: $0.10-$1.00 per task."
    )
    args_schema: type[BaseModel] = AskHumanInput
    api_key: str = ""

    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("LOOPUMAN_API_KEY", "")

    def _run(self, task: str, budget_cents: int = 50, timeout_seconds: int = 300) -> str:
        if not self.api_key:
            return "Error: LOOPUMAN_API_KEY not set. Get one at https://loopuman.com/developers"

        try:
            response = requests.post(
                f"{LOOPUMAN_API_BASE}/api/v1/tasks/sync",
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "title": task[:200],
                    "description": task,
                    "budget": budget_cents,
                    "estimated_seconds": timeout_seconds,
                    "timeout_seconds": timeout_seconds
                },
                timeout=timeout_seconds + 10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("submission"):
                    return f"Human response: {data['submission']['content']}"
                else:
                    return "Task timed out - no human responded in time. Try increasing budget or timeout."
            else:
                return f"Error: {response.status_code} - {response.text}"

        except requests.Timeout:
            return "Request timed out waiting for human response."
        except Exception as e:
            return f"Error contacting Loopuman: {str(e)}"


class PostTaskTool(BaseTool):
    name: str = "post_task_to_humans"
    description: str = (
        "Post an async task for human workers. Returns task ID - "
        "use check_human_task to get results later."
    )
    api_key: str = ""

    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("LOOPUMAN_API_KEY", "")

    def _run(self, title: str, description: str, budget_cents: int = 50, category: str = "general") -> str:
        if not self.api_key:
            return "Error: LOOPUMAN_API_KEY not set."

        response = requests.post(
            f"{LOOPUMAN_API_BASE}/api/v1/tasks",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json={"title": title, "description": description, "budget": budget_cents, "category": category}
                    "estimated_seconds": timeout_seconds,
        )

        if response.status_code == 200:
            data = response.json()
            return f"Task posted. ID: {data['task']['id']}. Use check_human_task to get results."
        return f"Error: {response.status_code} - {response.text}"


class CheckTaskTool(BaseTool):
    name: str = "check_human_task"
    description: str = "Check status and result of a Loopuman task."
    api_key: str = ""

    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("LOOPUMAN_API_KEY", "")

    def _run(self, task_id: str) -> str:
        response = requests.get(
            f"{LOOPUMAN_API_BASE}/api/v1/tasks/{task_id}",
            headers={"X-API-Key": self.api_key}
        )

        if response.status_code == 200:
            data = response.json()
            task = data.get("task", {})
            status = task.get("status", "unknown")
            if status == "completed" and task.get("submission"):
                return f"Completed. Human response: {task['submission']['content']}"
            return f"Status: {status}"
        return f"Error: {response.status_code}"


# Quick usage example
if __name__ == "__main__":
    from crewai import Agent, Task, Crew

    human_tool = AskHumanTool(api_key=os.getenv("LOOPUMAN_API_KEY"))

    reviewer = Agent(
        role="Content Reviewer",
        goal="Review content using human judgment",
        backstory="You leverage human workers for subjective evaluations.",
        tools=[human_tool]
    )

    review_task = Task(
        description="Ask a human to evaluate if this review is genuine: 'Best product ever, 5 stars!'",
        expected_output="Human evaluation of the review",
        agent=reviewer
    )

    crew = Crew(agents=[reviewer], tasks=[review_task])
    result = crew.kickoff()
    print(result)
