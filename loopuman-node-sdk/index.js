'use strict';
const https = require('https');
const http = require('http');
const { URL } = require('url');

class LoopumanError extends Error {
  constructor(message, statusCode, body) {
    super(message);
    this.name = 'LoopumanError';
    this.statusCode = statusCode || null;
    this.body = body || null;
  }

class LoopumanTimeoutError extends LoopumanError {
  constructor(taskId, timeoutSeconds) {
    super(`No human responded within ${timeoutSeconds}s. Task ID: ${taskId}`);
    this.name = 'LoopumanTimeoutError';
    this.taskId = taskId;
    this.timeoutSeconds = timeoutSeconds;
  }

class TaskResult {
  constructor(data) {
    this.taskId = data.task_id || data.id || null;
    this.status = data.status || null;
    this.response = data.response || data.content || null;
    this.workerId = data.worker_id || null;
    this.completedAt = data.completed_at || null;
    this.raw = data;
}

class Loopuman {
  constructor(options = {}) {
    this.apiKey = options.apiKey || process.env.LOOPUMAN_API_KEY;
    if (!this.apiKey) {
      throw new LoopumanError('API key required. Pass { apiKey: "lp_..." } or set LOOPUMAN_API_KEY environment variable.');
    }
    this.baseUrl = (options.baseUrl || process.env.LOOPUMAN_API_URL || 'https://api.loopuman.com').replace(/\/+$/, '');
    this.timeout = options.timeout || 30000;
  }

  _request(method, path, body) {
    return new Promise((resolve, reject) => {
      const url = new URL(path, this.baseUrl);
      const isHttps = url.protocol === 'https:';
      const lib = isHttps ? https : http;
      const payload = body ? JSON.stringify(body) : null;
      const reqOptions = {
        hostname: url.hostname,
        port: url.port || (isHttps ? 443 : 80),
        path: url.pathname + url.search,
        method,
        headers: {
          'X-API-Key': this.apiKey,
          'Content-Type': 'application/json',
          'User-Agent': 'loopuman-node/1.0.2',
          ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
        },
        timeout: this.timeout,
      };
      const req = lib.request(reqOptions, (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          let parsed;
          try { parsed = JSON.parse(data); } catch { parsed = { raw: data }; }
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(parsed);
          } else {
            const msg = parsed.error || parsed.message || `HTTP ${res.statusCode}`;
            reject(new LoopumanError(msg, res.statusCode, parsed));
          }
        });
      });
      req.on('error', (err) => reject(new LoopumanError(`Network error: ${err.message}`)));
      req.on('timeout', () => { req.destroy(); reject(new LoopumanError('Request timed out')); });
      if (payload) req.write(payload);
      req.end();
    });
  }

  async health() { return this._request('GET', '/health'); }

  async ask(question, options = {}) {
    const { context, budget = 50, timeoutSeconds = 300, category = 'micro' } = options;
    const body = {
      title: question,
      description: context ? `${question}\n\nContext: ${context}` : question,
      budget, category, timeout_seconds: timeoutSeconds, estimated_seconds: timeoutSeconds,
    };
    const data = await this._request('POST', '/api/v1/tasks/sync', body);
    return new TaskResult(data);
  }

  async createTask(task) {
    return this._request('POST', '/api/v1/tasks/bulk', {
      tasks: [{
        title: task.title, description: task.description,
        budget: task.budget || 50, category: task.category || 'micro', estimated_seconds: task.estimatedSeconds || 300,
        max_workers: task.maxWorkers || 1,
      }],
      webhook_url: task.webhookUrl || undefined,
    });
  }

  async bulkCreate(tasks, options = {}) {
    return this._request('POST', '/api/v1/tasks/bulk', {
      tasks: tasks.map((t) => ({
        title: t.title, description: t.description,
        budget: t.budget || 50, category: t.category || 'micro', estimated_seconds: t.estimatedSeconds || t.estimated_seconds || 300,
        max_workers: t.maxWorkers || t.max_workers || 1,
      })),
      webhook_url: options.webhookUrl || undefined,
    });
  }

  async getBatch(batchId) { return this._request('GET', `/api/v1/batches/${batchId}`); }
  async getResults(batchId) { return this._request('GET', `/api/v1/batches/${batchId}/results`); }

  async waitForBatch(batchId, options = {}) {
    const { intervalMs = 5000, timeoutMs = 600000, onProgress } = options;
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const status = await this.getBatch(batchId);
      if (onProgress) onProgress(status);
      const total = status.total || 0;
      const completed = (status.completed || 0) + (status.approved || 0);
      if (completed >= total && total > 0) return this.getResults(batchId);
      await new Promise((r) => setTimeout(r, intervalMs));
    }
    throw new LoopumanTimeoutError(batchId, Math.round(timeoutMs / 1000));
  }
  async approve(submissionId) {
    return this._request('POST', `/api/v1/submissions/${submissionId}/approve`);
  }
  async reject(submissionId, reason) {
    return this._request('POST', `/api/v1/submissions/${submissionId}/reject`,
      reason ? { reason } : undefined);
  }
}

module.exports = Loopuman;
module.exports.Loopuman = Loopuman;
module.exports.LoopumanError = LoopumanError;
module.exports.LoopumanTimeoutError = LoopumanTimeoutError;
module.exports.TaskResult = TaskResult;
