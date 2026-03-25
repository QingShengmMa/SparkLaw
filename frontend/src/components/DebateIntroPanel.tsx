'use client';

import React from 'react';
import { AlertCircle } from 'lucide-react';
import ScaleIcon from '@/components/ScaleIcon';
import { EXAMPLE_CASES, STRATEGY_OPTIONS } from '@/components/debate-constants';
import type { StrategyKey } from '@/components/debate-types';

export default function DebateIntroPanel({
  caseDescription,
  strategy,
  error,
  setCaseDescription,
  setStrategy,
  handleStart,
}: {
  caseDescription: string;
  strategy: StrategyKey;
  error: string;
  setCaseDescription: (value: string) => void;
  setStrategy: (value: StrategyKey) => void;
  handleStart: () => void;
}) {
  return (
    <div className="card mb-6 p-6">
      <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold"><ScaleIcon size={20} /> 案情描述</h2>
      <textarea
        value={caseDescription}
        onChange={(e) => setCaseDescription(e.target.value)}
        placeholder="请详细描述案件情况..."
        className="h-36 w-full resize-none rounded-lg border border-input bg-background p-4 text-foreground placeholder:text-muted-foreground transition focus-ring"
      />
      <div className="mt-5 rounded-2xl border border-zinc-200/80 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-900/50">
        <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-200">选择原告律师策略</h3>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          {STRATEGY_OPTIONS.map((opt) => (
            <button key={opt.key} type="button" data-active={strategy === opt.key}
              onClick={() => setStrategy(opt.key)}
              className={`rounded-xl border border-zinc-300/80 bg-white p-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-zinc-700 dark:bg-zinc-900/60 ${opt.ring}`}
            >
              <div className="mb-1 flex items-center gap-2"><span className="text-lg">{opt.icon}</span><span className="text-sm font-semibold">{opt.title}</span></div>
              <p className="text-xs text-zinc-500">{opt.subtitle}</p>
            </button>
          ))}
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{caseDescription.length} 字</span>
        <button onClick={handleStart} disabled={caseDescription.length < 20}
          className="rounded-lg bg-gradient-legal px-6 py-3 font-medium shadow-lg transition hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-50 focus-ring">
          <span className="text-foreground dark:text-white">🎭 开始模拟庭审</span>
        </button>
      </div>
      <div className="mt-6 border-t border-border pt-5">
        <p className="mb-3 text-sm text-muted-foreground">快速填充示例案例：</p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {EXAMPLE_CASES.map((ex, i) => (
            <button key={i} onClick={() => setCaseDescription(ex)} className="card-hover p-3 text-left text-sm transition">
              <span className="font-medium">案例 {i + 1}</span>
              <p className="mt-1 line-clamp-2 text-muted-foreground">{ex.substring(0, 50)}...</p>
            </button>
          ))}
        </div>
      </div>
      {error && (
        <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900/50 dark:bg-red-950/20">
          <AlertCircle size={18} className="mt-0.5 text-red-600" />
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      )}
    </div>
  );
}
