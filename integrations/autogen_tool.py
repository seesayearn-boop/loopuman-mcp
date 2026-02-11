"""
Loopuman AutoGen Tool
=====================
Give AutoGen agents access to real human workers.

Install: pip install loopuman pyautogen
Usage:
    from loopuman_autogen import ask_human, LOOPUMAN_TOOL_SCHEMA
    assistant.register_for_llm(description="Ask humans")(ask_human)
"""

import os
import json
import requests
from typing import Annotated

LOOPUMAN_API_BASE = os.getenv("LOOPUMAN_API_URL", "https://api.loopuman.com")
LOOPUMAN_API_KEY = os.getenv("LOOPUMAN_API_KEY", "")


def ask_human(
    task: Annotated[str, "Clear description of what you need the human to do"],
    budget_cents: Annotated[int, "Payment in cents. Min 10. Typical: 25-100"] = 50,
    timeout_seconds: Annotated[int, "How long to wait. Default 300 (5 min)"] = 300,
) -> str:
    """Ask a real human worker to complete a task via Loopuman.
    Use for verification, judgment, content moderation, fact-checking,
    subjective evaluation, or real-world actions."""

    api_key = LOOPUMAN_API_KEY
    if not api_key:
        return "Error: Set LOOPUMAN_API_KEY environment variable. Get one at https://loopuman.com/developers"

    try:
        response = requests.post(
            f"{LOOPUMAN_API_BASE}/api/v1/tasks/sync",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
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
                return f"Human response: {data['submission']['content']}"
            return "Task timed out - no human responded. Try increasing budget."
        return f"Error: {response.status_code} - {response.text}"

    except Exception as e:
        return f"Error: {str(e)}"


def post_task(
    title: Annotated[str, "Short task title"],
    description: Annotated[str, "Detailed instructions for the human worker"],
    budget_cents: Annotated[int, "Payment in cents"] = 50,
) -> str:
    """Post an async task for human workers. Returns task ID."""

    api_key = LOOPUMAN_API_KEY
    if not api_key:
        return "Error: Set LOOPUMAN_API_KEY"

    response = requests.post(
        f"{LOOPUMAN_API_BASE}/api/v1/tasks",
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json={"title": title, "description": description, "budget": budget_cents},
    )

    if response.status_code == 200:
        return f"Task posted. ID: {response.json()['task']['id']}"
    return f"Error: {response.status_code} - {response.text}"


def check_task(
    task_id: Annotated[str, "Task UUID from post_task"],
) -> str:
    """Check status of a Loopuman task."""

    response = requests.get(
        f"{LOOPUMAN_API_BASE}/api/v1/tasks/{task_id}",
        headers={"X-API-Key": LOOPUMAN_API_KEY},
    )

    if response.status_code == 200:
        task = response.json().get("task", {})
        if task.get("status") == "completed" and task.get("submission"):
            return f"Completed: {task['submission']['content']}"
        return f"Status: {task.get('status', 'unknown')}"
    return f"Error: {response.status_code}"


def get_balance() -> str:
    """Check Loopuman account balance."""
    response = requests.get(
        f"{LOOPUMAN_API_BASE}/api/v1/balance",
        headers={"X-API-Key": LOOPUMAN_API_KEY},
    )
    if response.status_code == 200:
        data = response.json()
        return f"Balance: {data.get('balance_vae', 0)} VAE (${data.get('balance_vae', 0) / 100:.2f} USD)"
    return f"Error: {response.status_code}"


# AutoGen registration example
if __name__ == "__main__":
    from autogen import AssistantAgent, UserProxyAgent

    assistant = AssistantAgent(
        name="assistant",
        system_message="You are a helpful assistant. Use ask_human when you need real human judgment.",
        llm_config={"model": "gpt-4"},
    )

    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        code_execution_config=False,
    )

    # Register Loopuman tools
    assistant.register_for_llm(description="Ask a human worker to complete a task")(ask_human)
    assistant.register_for_llm(description="Post async task for humans")(post_task)
    assistant.register_for_llm(description="Check task status")(check_task)
    assistant.register_for_llm(description="Check account balance")(get_balance)

    user_proxy.register_for_execution(name="ask_human")(ask_human)
    user_proxy.register_for_execution(name="post_task")(post_task)
    user_proxy.register_for_execution(name="check_task")(check_task)
    user_proxy.register_for_execution(name="get_balance")(get_balance)

    user_proxy.initiate_chat(
        assistant,
        message="Ask a human: Is this product description misleading? 'Our supplement cures all diseases'",
    )
