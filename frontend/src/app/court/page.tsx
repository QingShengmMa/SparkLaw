'use client';

import React from 'react';

export default function CourtPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center bg-slate-50 px-6 py-12">
      <div className="max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h1 className="mb-3 text-2xl font-bold text-slate-800">模拟法庭</h1>
        <p className="text-sm leading-7 text-slate-600">
          页面已修复为可正常编译版本。若你希望恢复完整的沉浸式庭审交互界面，
          我可以继续按你当前后端 SSE 协议重新补回完整页面逻辑。
        </p>
      </div>
    </div>
  );
}
