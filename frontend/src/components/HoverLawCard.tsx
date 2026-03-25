'use client';

import React from 'react';
import type { LawItem } from '@/components/debate-types';

export default function HoverLawCard({
  lawId,
  law,
}: {
  lawId: string;
  law?: LawItem;
}) {
  const lawNumber = lawId.replace('law_', '');

  return (
    <span className="group relative mx-1 inline-block align-baseline">
      <span className="cursor-help border-b border-dashed border-gray-400 text-zinc-700 dark:text-zinc-300">
        [法条 {lawNumber}]
      </span>
      <span className="pointer-events-none invisible absolute left-0 top-[calc(100%+8px)] z-50 w-[360px] rounded-xl border border-zinc-200 bg-white p-3 text-left opacity-0 shadow-2xl transition-all duration-150 group-hover:visible group-hover:opacity-100 dark:border-zinc-700 dark:bg-zinc-900">
        <span className="mb-1 block text-xs font-semibold text-blue-700 dark:text-blue-300">{law?.title || lawId}</span>
        <span className="block max-h-48 overflow-y-auto text-xs leading-5 text-zinc-700 dark:text-zinc-200">
          {law?.content || '未找到对应法条内容'}
        </span>
        {law?.source && <span className="mt-2 block text-[11px] text-zinc-400">来源：{law.source}</span>}
      </span>
    </span>
  );
}
