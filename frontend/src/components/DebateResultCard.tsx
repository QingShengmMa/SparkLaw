'use client';

import React from 'react';
import type { CourtResult } from '@/components/debate-types';

export default function DebateResultCard({ result }: { result: CourtResult }) {
  return (
    <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 p-6 shadow-sm dark:border-amber-900/40 dark:from-amber-950/30 dark:to-orange-950/20">
      <div className="mb-4 text-center">
        <h2 className="font-serif text-2xl font-bold">⚖️ 法官综合评估</h2>
        <p className="mt-1 text-sm text-muted-foreground">AI 法庭综合评议结果（仅供参考）</p>
      </div>
      <div className="mb-5 grid grid-cols-2 gap-6 text-center">
        <div>
          <div className="text-4xl font-bold text-red-500">{result.plaintiff_win_rate}%</div>
          <div className="mt-1 text-sm text-muted-foreground">原告胜诉概率</div>
          <div className="mt-2 h-2.5 w-full rounded-full bg-zinc-200 dark:bg-zinc-700">
            <div className="h-2.5 rounded-full bg-gradient-to-r from-red-400 to-red-600 transition-all duration-1000 ease-out" style={{ width: `${result.plaintiff_win_rate}%` }} />
          </div>
        </div>
        <div>
          <div className="text-4xl font-bold text-blue-500">{result.defendant_win_rate}%</div>
          <div className="mt-1 text-sm text-muted-foreground">被告胜诉概率</div>
          <div className="mt-2 h-2.5 w-full rounded-full bg-zinc-200 dark:bg-zinc-700">
            <div className="h-2.5 rounded-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-1000 ease-out" style={{ width: `${result.defendant_win_rate}%` }} />
          </div>
        </div>
      </div>
      {result.legal_basis.length > 0 && (
        <div className="mt-4 rounded-xl border border-amber-200 bg-white/70 p-4 dark:border-amber-800 dark:bg-zinc-900/40">
          <h3 className="mb-2 text-sm font-semibold text-amber-800 dark:text-amber-300">📚 本案参考法条</h3>
          <ul className="space-y-1">
            {result.legal_basis.map((lb, i) => (
              <li key={i} className="text-xs leading-5 text-zinc-600 dark:text-zinc-300">{lb}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
