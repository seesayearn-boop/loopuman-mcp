"""
Loopuman Python SDK
The Human API for AI - Give your AI agents instant access to humans

Usage:
    from loopuman import Loopuman
    
    client = Loopuman(api_key="your_key")
    
    # Synchronous - waits for human response
    result = client.ask("Is this content appropriate?", budget_cents=50)
    print(result.response)
    
    # Async - returns immediately, check later
    task = client.create_task("Review this document", budget_cents=100)
    # ... later ...
    result = client.get_result(task.id)
"""

import requests
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

__version__ = "1.0.0"

@dataclass
class TaskResult:
    status: str  # "completed", "timeout", "pending"
    task_id: str
    response: Optional[str] = None
    worker_id: Optional[str] = None
    completed_in_seconds: Optional[int] = None

@dataclass
class Task:
    id: str
    title: str
    status: str
    budget: int

class LoopumanError(Exception):
    """Base exception for Loopuman errors"""
    pass

class Loopuman:
    """
    Loopuman client - The Human API for AI
    
    Args:
        api_key: Your Loopuman API key
        base_url: API base URL (default: https://api.loopuman.com)
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.loopuman.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        })
    
    def ask(
        self,
        question: str,
        context: str = "",
        budget_cents: int = 50,
        timeout_seconds: int = 300,
        auto_approve: bool = True
    ) -> TaskResult:
        """
        Ask a human a question and wait for the response.
        
        This is a synchronous call - it blocks until a human responds
        or the timeout is reached.
        
        Args:
            question: The question to ask
            context: Additional context for the human
            budget_cents: Payment in cents (min 10, typical 25-100)
            timeout_seconds: Max time to wait (default 5 minutes)
            auto_approve: Auto-approve the submission (default True)
        
        Returns:
            TaskResult with the human's response
        
        Example:
            result = client.ask("Is this image appropriate?")
            if result.status == "completed":
                print(f"Human said: {result.response}")
        """
        response = self._session.post(
            f"{self.base_url}/api/v1/tasks/sync",
            json={
                "title": question,
                "description": context,
                "budget": budget_cents,
                "estimated_seconds": timeout_seconds,
                "timeout_seconds": timeout_seconds,
                "auto_approve": auto_approve
            }
        )
        
        if response.status_code != 200:
            raise LoopumanError(f"API error: {response.text}")
        
        data = response.json()
        return TaskResult(
            status=data.get("status", "error"),
            task_id=data.get("task_id", ""),
            response=data.get("response"),
            worker_id=data.get("worker_id"),
            completed_in_seconds=data.get("completed_in_seconds")
        )
    
    def create_task(
        self,
        title: str,
        description: str = "",
        category: str = "ai_training",
        budget_cents: int = 50,
        webhook_url: Optional[str] = None,
        estimated_seconds: int = 300
    ) -> Task:
        """
        Create a task asynchronously.
        
        Use this when you don't need to wait for the response inline.
        You can check for results later or receive a webhook.
        
        Args:
            title: Task title
            description: Task description
            category: Task category (default: ai_training)
            budget_cents: Payment in cents
            webhook_url: URL to receive completion webhook
        
        Returns:
            Task object with the task ID
        """
        payload = {
            "tasks": [{
                "title": title,
                "description": description,
                "category": category,
                "budget": budget_cents,
                "estimated_seconds": estimated_seconds
            }]
        }
        if webhook_url:
            payload["webhook_url"] = webhook_url
        
        response = self._session.post(
            f"{self.base_url}/api/v1/tasks/bulk",
            json=payload
        )
        
        if response.status_code != 200:
            raise LoopumanError(f"API error: {response.text}")
        
        data = response.json()
        task_id = data.get("task_ids", [None])[0]
        
        return Task(
            id=task_id,
            title=title,
            status="active",
            budget=budget_cents
        )
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Check if a task has been completed.
        
        Args:
            task_id: The task ID to check
        
        Returns:
            TaskResult if completed, None if still pending
        """
        response = self._session.get(
            f"{self.base_url}/api/v1/tasks/{task_id}"
        )
        
        if response.status_code != 200:
            raise LoopumanError(f"API error: {response.text}")
        
        data = response.json()
        if data.get("submissions"):
            sub = data["submissions"][0]
            return TaskResult(
                status="completed",
                task_id=task_id,
                response=sub.get("content"),
                worker_id=sub.get("worker_id")
            )
        
        return None
    
    def bulk_create(
        self,
        tasks: List[Dict[str, Any]],
        webhook_url: Optional[str] = None,
        estimated_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Create multiple tasks at once.
        
        Args:
            tasks: List of task dicts with title, description, budget
            webhook_url: URL to receive completion webhooks
        
        Returns:
            Dict with batch_id and task_ids
        
        Example:
            result = client.bulk_create([
                {"title": "Review image 1", "budget": 25},
                {"title": "Review image 2", "budget": 25},
            ])
        """
        payload = {"tasks": tasks}
        if webhook_url:
            payload["webhook_url"] = webhook_url
        
        response = self._session.post(
            f"{self.base_url}/api/v1/tasks/bulk",
            json=payload
        )
        
        if response.status_code != 200:
            raise LoopumanError(f"API error: {response.text}")
        
        return response.json()


    def approve(self, submission_id: str) -> dict:
        """Approve a submission and pay the worker instantly."""
        response = self._session.post(
            f"{self.base_url}/api/v1/submissions/{submission_id}/approve"
        )
        if response.status_code != 200:
            raise LoopumanError(f"API error: {response.text}")
        return response.json()

    def reject(self, submission_id: str, reason: str = "") -> dict:
        """Reject a submission."""
        response = self._session.post(
            f"{self.base_url}/api/v1/submissions/{submission_id}/reject",
            json={"reason": reason} if reason else None
        )
        if response.status_code != 200:
            raise LoopumanError(f"API error: {response.text}")
        return response.json()

# LangChain Tool Integration
def get_langchain_tool():
    """
    Get a LangChain-compatible tool for human-in-the-loop.
    
    Usage:
        from loopuman import get_langchain_tool
        
        human_tool = get_langchain_tool()
        agent = initialize_agent([human_tool, ...], llm)
    """
    try:
        from langchain.tools import Tool
    except ImportError:
        raise ImportError("langchain is required: pip install langchain")
    
    import os
    client = Loopuman(api_key=os.environ.get("LOOPUMAN_API_KEY", ""))
    
    def ask_human(query: str) -> str:
        """Ask a human for help with verification or judgment."""
        result = client.ask(query, timeout_seconds=300)
        if result.status == "completed":
            return result.response
        return f"No human responded. Task ID: {result.task_id}"
    
    return Tool(
        name="AskHuman",
        func=ask_human,
        description="Ask a human for help with verification, judgment, or subjective evaluation. Use when AI is uncertain or needs human oversight."
    )
