'use client';

import { useEffect, useState } from 'react';
import { checkHealth, HealthResponse } from '@/lib/api';
import { Activity, Cloud, HardDrive } from 'lucide-react';

export default function StatusBar() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await checkHealth();
        setHealth(data);
      } catch (error) {
        console.error('Failed to fetch health:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    // 每30秒刷新一次
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-card border border-border px-4 py-2">
        <Activity size={16} className="animate-pulse text-muted-foreground" />
        <span className="text-sm text-muted-foreground">连接中...</span>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 dark:border-red-900/50 dark:bg-red-950/20">
        <Activity size={16} className="text-red-600 dark:text-red-400" />
        <span className="text-sm text-red-700 dark:text-red-400">后端离线</span>
      </div>
    );
  }

  const isLocal = health.llm_mode === 'local';

  return (
    <div className="flex items-center gap-4">
      {/* 状态指示器 */}
      <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-2 dark:border-green-900/50 dark:bg-green-950/20">
        <div className="h-2 w-2 animate-pulse rounded-full bg-green-600 dark:bg-green-400" />
        <span className="text-sm text-green-700 dark:text-green-400">在线</span>
      </div>

      {/* LLM 模式 */}
      <div className="flex items-center gap-2 rounded-lg bg-card border border-border px-4 py-2">
        {isLocal ? (
          <HardDrive size={16} className="text-blue-600 dark:text-blue-400" />
        ) : (
          <Cloud size={16} className="text-purple-600 dark:text-purple-400" />
        )}
        <div className="text-sm">
          <span className="text-muted-foreground">模式: </span>
          <span className={isLocal ? 'text-blue-600 dark:text-blue-400' : 'text-purple-600 dark:text-purple-400'}>
            {isLocal ? 'Local' : 'Cloud'}
          </span>
        </div>
      </div>

      {/* 模型信息 */}
      <div className="text-sm text-muted-foreground">
        <span>模型: </span>
        <span className="text-foreground">{health.llm_model}</span>
      </div>
    </div>
  );
}
