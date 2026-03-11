# Loopuman Python SDK

Connect AI agents to real humans via Loopuman — The Human Layer for AI.

## Install
```
pip install loopuman
```

## Usage
```python
from loopuman import Loopuman

client = Loopuman(api_key="your_key")
result = client.ask("Is this image appropriate?")
print(result.response)
```

More info: https://loopuman.com/developers
