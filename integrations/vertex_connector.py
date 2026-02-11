"""
Loopuman Vertex AI / Google Gemini Integration
===============================================
Give Google AI agents access to real human workers.

Usage with Vertex AI:
    from loopuman_vertex import LOOPUMAN_TOOLS, handle_loopuman_call

    model = GenerativeModel("gemini-pro", tools=[LOOPUMAN_TOOLS])
"""

import os
import requests
from google.cloud import aiplatform
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerativeModel,
    Tool,
)

LOOPUMAN_API_BASE = os.getenv("LOOPUMAN_API_URL", "https://api.loopuman.com")
LOOPUMAN_API_KEY = os.getenv("LOOPUMAN_API_KEY", "")

# ── Function Declarations ──────────────────────────────────────────

ask_human_func = FunctionDeclaration(
    name="ask_human",
    description=(
        "Ask a real human worker to complete a task via Loopuman. "
        "Use for verification, judgment, content moderation, fact-checking, "
        "subjective evaluation, or real-world actions. Cost: $0.10-$1.00."
    ),
    parameters={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Clear description of what you need the human to do",
            },
            "budget_cents": {
                "type": "integer",
                "description": "Payment in cents. Minimum 10. Typical: 25-100.",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "Max wait time. Default 300 seconds.",
            },
        },
        "required": ["task", "budget_cents"],
    },
)

post_task_func = FunctionDeclaration(
    name="post_task_to_humans",
    description="Post an async task for human workers. Returns task_id.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short task title"},
            "description": {"type": "string", "description": "Detailed instructions"},
            "budget_cents": {"type": "integer", "description": "Payment in cents"},
        },
        "required": ["title", "description", "budget_cents"],
    },
)

check_task_func = FunctionDeclaration(
    name="check_human_task",
    description="Check status of a Loopuman task.",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task UUID"},
        },
        "required": ["task_id"],
    },
)

LOOPUMAN_TOOLS = Tool(
    function_declarations=[ask_human_func, post_task_func, check_task_func]
)


# ── Function Handlers ──────────────────────────────────────────────

def handle_loopuman_call(function_call):
    """Handle a Loopuman function call from Gemini."""
    name = function_call.name
    args = dict(function_call.args)

    headers = {"X-API-Key": LOOPUMAN_API_KEY, "Content-Type": "application/json"}

    if name == "ask_human":
        response = requests.post(
            f"{LOOPUMAN_API_BASE}/api/v1/tasks/sync",
            headers=headers,
            json={
                "title": args["task"][:200],
                "description": args["task"],
                "budget": args.get("budget_cents", 50),
                "timeout_seconds": args.get("timeout_seconds", 300),
            },
            timeout=args.get("timeout_seconds", 300) + 10,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("submission"):
                return {"response": data["submission"]["content"]}
            return {"response": "No human responded in time."}
        return {"error": response.text}

    elif name == "post_task_to_humans":
        response = requests.post(
            f"{LOOPUMAN_API_BASE}/api/v1/tasks",
            headers=headers,
            json={
                "title": args["title"],
                "description": args["description"],
                "budget": args.get("budget_cents", 50),
            },
        )
        if response.status_code == 200:
            return {"task_id": response.json()["task"]["id"]}
        return {"error": response.text}

    elif name == "check_human_task":
        response = requests.get(
            f"{LOOPUMAN_API_BASE}/api/v1/tasks/{args['task_id']}",
            headers={"X-API-Key": LOOPUMAN_API_KEY},
        )
        if response.status_code == 200:
            task = response.json().get("task", {})
            if task.get("submission"):
                return {"status": "completed", "response": task["submission"]["content"]}
            return {"status": task.get("status", "unknown")}
        return {"error": response.text}

    return {"error": f"Unknown function: {name}"}


# ── Example Usage ──────────────────────────────────────────────────

if __name__ == "__main__":
    model = GenerativeModel("gemini-pro", tools=[LOOPUMAN_TOOLS])
    chat = model.start_chat()

    response = chat.send_message(
        "Ask a human to verify: Is the claim 'Honey never expires' true?"
    )

    # Handle function calls
    for candidate in response.candidates:
        for part in candidate.content.parts:
            if hasattr(part, "function_call"):
                result = handle_loopuman_call(part.function_call)
                print(f"Human said: {result}")
