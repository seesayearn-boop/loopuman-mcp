declare module 'loopuman-mcp' {
  export interface Task {
    id: string;
    title: string;
    description: string;
    category: string;
    budget: number;
    currency: string;
    status: string;
  }
  export interface TaskResult {
    taskId: string;
    response: string;
    quality: number;
    workerId: string;
    completedAt: string;
  }
  export function createTask(options: Partial<Task>): Promise<Task>;
  export function getTask(taskId: string): Promise<Task>;
  export function listTasks(): Promise<Task[]>;
}
