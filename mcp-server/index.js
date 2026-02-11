#!/usr/bin/env node
/**
 * Loopuman MCP Server v1.1.0
 * Gives AI agents native access to human workers
 *
 * Usage:
 * 1. npm install -g loopuman-mcp
 * 2. Add to Claude/Cursor/Copilot config:
 *    {
 *      "mcpServers": {
 *        "loopuman": {
 *          "command": "loopuman-mcp",
 *          "env": { "LOOPUMAN_API_KEY": "your_key" }
 *        }
 *      }
 *    }
 */

const API_BASE = process.env.LOOPUMAN_API_URL || 'https://api.loopuman.com';
const API_KEY = process.env.LOOPUMAN_API_KEY;
const fetch = globalThis.fetch || require('node-fetch');

if (!API_KEY) {
  process.stderr.write('ERROR: LOOPUMAN_API_KEY not set.\n');
  process.stderr.write('Get your free key:\n');
  process.stderr.write('  curl -X POST https://api.loopuman.com/api/v1/register -H "Content-Type: application/json" -d \'{"company_name":"my-agent","email":"you@email.com"}\'\n');
  process.stderr.write('Then set: export LOOPUMAN_API_KEY=your_key\n');
}

const tools = [
  {
    name: "ask_human",
    description: "Ask a human worker to complete a task. Use for verification, judgment, subjective evaluation, content moderation, fact-checking, or real-world actions. Returns the human's response. Typical response time: 30-120 seconds.",
    inputSchema: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "The question or task for the human"
        },
        context: {
          type: "string",
          description: "Additional context to help the human understand"
        },
        budget_cents: {
          type: "number",
          description: "Payment in cents (minimum 10, typical 25-100)",
          default: 50
        },
        timeout_seconds: {
          type: "number",
          description: "Max time to wait for response in seconds",
          default: 300
        }
      },
      required: ["question"]
    }
  },
  {
    name: "post_task",
    description: "Post an async task for human workers without waiting. Use check_task to get results later. Good for batch operations.",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string", description: "Short task title" },
        description: { type: "string", description: "Detailed instructions for the human" },
        budget_cents: { type: "number", description: "Payment in cents (min 10)", default: 50 },
        category: { type: "string", description: "Task category", default: "general" },
        estimated_seconds: { type: "number", description: "Estimated seconds for human to complete (default 300)", default: 300 }
      },
      required: ["title", "description"]
    }
  },
  {
    name: "check_task",
    description: "Check status and result of a previously posted task.",
    inputSchema: {
      type: "object",
      properties: {
        task_id: { type: "string", description: "Task UUID from post_task" }
      },
      required: ["task_id"]
    }
  },
  {
    name: "get_balance",
    description: "Check your Loopuman account balance.",
    inputSchema: { type: "object", properties: {} }
    {
      name: "approve_submission",
      description: "Approve a completed submission and pay the worker instantly.",
      inputSchema: {
        type: "object",
        properties: {
          submission_id: { type: "string", description: "Submission ID to approve" }
        },
        required: ["submission_id"]
      }
    }
  }
];

async function handleToolCall(name, args) {
  const headers = { 'Content-Type': 'application/json', 'X-API-Key': API_KEY };

  switch (name) {
    case 'ask_human': {
      const desc = args.context ? `${args.question}\n\nContext: ${args.context}` : args.question;
      const response = await fetch(`${API_BASE}/api/v1/tasks/sync`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          title: args.question.substring(0, 200),
          description: desc,
          budget: args.budget_cents || 50,
          estimated_seconds: args.timeout_seconds || 300,
          timeout_seconds: args.timeout_seconds || 300,
          auto_approve: true
        })
      });
      const data = await response.json();
      if (data.status === 'completed') {
        return { response: data.response, worker_id: data.worker_id };
      }
      return { status: data.status || 'timeout', message: 'No human responded in time. Try increasing budget or timeout.' };
    }

    case 'post_task': {
      const response = await fetch(`${API_BASE}/api/v1/tasks`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          title: args.title,
          description: args.description,
          budget: args.budget_cents || 50,
          estimated_seconds: args.estimated_seconds || 300,
          category: args.category || 'general'
        })
      });
      const data = await response.json();
      return { task_id: data.task?.id, status: 'posted' };
    }

    case 'check_task': {
      const response = await fetch(`${API_BASE}/api/v1/tasks/${args.task_id}`, { headers });
      const data = await response.json();
      const task = data.task || data;
      if (task.status === 'completed' && task.submission) {
        return { status: 'completed', response: task.submission.content };
      }
      return { status: task.status || 'unknown' };
    }

    case 'get_balance': {
      const response = await fetch(`${API_BASE}/api/v1/balance`, { headers });
      const data = await response.json();
      return { balance_vae: data.available_vae, balance_usd: data.available_usd };
    }
    case 'approve_submission': {
      const response = await fetch(`${API_BASE}/api/v1/submissions/${args.submission_id}/approve`, {
        method: 'POST', headers
      });
      const data = await response.json();
      return data;
    }

    default:
      return { error: `Unknown tool: ${name}` };
  }
}

// MCP stdio protocol - JSON-RPC 2.0
const readline = require('readline');
const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: false });

rl.on('line', async (line) => {
  try {
    const msg = JSON.parse(line);

    if (msg.method === 'initialize') {
      process.stdout.write(JSON.stringify({
        jsonrpc: '2.0',
        id: msg.id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: { tools: {} },
          serverInfo: { name: 'loopuman', version: '1.1.0' }
        }
      }) + '\n');
    }

    else if (msg.method === 'notifications/initialized') {
      // Client confirmed — no response needed
    }

    else if (msg.method === 'tools/list') {
      process.stdout.write(JSON.stringify({
        jsonrpc: '2.0',
        id: msg.id,
        result: { tools }
      }) + '\n');
    }

    else if (msg.method === 'tools/call') {
      try {
        const result = await handleToolCall(msg.params.name, msg.params.arguments);
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0',
          id: msg.id,
          result: { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] }
        }) + '\n');
      } catch (toolErr) {
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0',
          id: msg.id,
          result: { content: [{ type: 'text', text: JSON.stringify({ error: toolErr.message }) }] }
        }) + '\n');
      }
    }
  } catch (e) {
    process.stderr.write('Parse error: ' + e.message + '\n');
  }
});
