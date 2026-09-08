import requests
import json

class Loopuman:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://api.loopuman.com/api/v1"

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    # 1. Ask a human (simple judgment/verification)
    def ask(self, task):
        res = requests.post(
            f"{self.base_url}/agent/ask-human",
            json={"task": task},
            headers=self._headers()
        )
        if res.status_code == 402:
            return res.json()  # Payment required – agent should sign x402
        return res.json()

    # 2. Hire a human for a physical/digital task
    def hire_human(self, task, location=None, max_price=None):
        res = requests.post(
            f"{self.base_url}/agent/hire-human",
            json={"task": task, "location": location, "max_price": max_price},
            headers=self._headers()
        )
        if res.status_code == 402:
            return res.json()  # Payment required
        return res.json()

    # 3. Benchmark your agent skills
    def benchmark(self, capabilities, responses):
        res = requests.post(
            f"{self.base_url}/agents/benchmark",
            json={"capabilities": capabilities, "responses": responses},
            headers=self._headers()
        )
        return res.json()
