# Loopuman MCP Server & SDKs

**The Human Layer for AI** — Connect AI agents to real humans for verification, judgment, and tasks that require human intelligence.

Loopuman provides an MCP server and SDKs that let AI agents request human help via a global workforce on Telegram and WhatsApp, with instant cryptocurrency payments on Celo.

## Quick Start

### MCP Server (for Claude, Cursor, etc.)
```bash
cd mcp-server
npm install
LOOPUMAN_API_KEY=your_key node index.js
```

### Node.js SDK
```bash
npm install loopuman
```
```javascript
const Loopuman = require('loopuman');
const client = new Loopuman({ apiKey: 'your_key' });

// Ask a human a question
const result = await client.ask('Is this image appropriate for children?');
console.log(result.response);

// Post a task with budget
const task = await client.createTask({
  title: 'Verify this business address',
  description: 'Visit and confirm this address exists: 123 Main St',
  budget: 500, // 500 VAE = $5
  estimatedSeconds: 1800
});
```

### Python SDK
```bash
pip install loopuman
```
```python
from loopuman import Loopuman

client = Loopuman(api_key="your_key")

result = client.ask("Is this image appropriate for children?")
print(result.response)
```

## Integrations

- **LangChain** — `from loopuman import get_langchain_tool`
- **CrewAI** — `integrations/crewai_tool.py`
- **AutoGen** — `integrations/autogen_tool.py`
- **LangGraph** — `integrations/langgraph_tool.py`
- **Google Vertex** — `integrations/vertex_connector.py`

## API Features

- Human-in-the-loop for AI agents
- Task posting with budget and time estimates
- Approve/reject submissions
- Bulk task creation
- Balance checking
- $6/hr minimum worker pay enforcement

## Pricing

- 20% platform fee on deposits
- Workers paid instantly in USDC, USDT, or cUSD on Celo
- Minimum task budget: 25 VAE ($0.25)

## Links

- **Website:** https://loopuman.com
- **API Docs:** https://loopuman.com/developers
- **Telegram Bot:** https://t.me/LoopumanBot
- **Get API Key:** https://loopuman.com/developers

## License

MIT
