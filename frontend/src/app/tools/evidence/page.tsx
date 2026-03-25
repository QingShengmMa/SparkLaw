'use client';

import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';

export default function EvidencePage() {
  const router = useRouter();

  return (
    <main className="flex-1 flex flex-col overflow-y-auto transition-colors duration-300 ease-in-out">
      <div className="flex-1 flex flex-col w-full px-6 pt-4 pb-2 lg:px-8 h-full">

        <header className="mb-5 flex items-center justify-between shrink-0 relative z-20">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/tools')}
              className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-white/10 text-gray-500 dark:text-gray-400 transition-colors active:scale-95"
            >
              <ArrowLeft size={18} />
            </button>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100 flex items-center gap-2 transition-colors">
                证据评估 📸
              </h1>
            </div>
          </div>
        </header>

        <div className="flex-1 flex items-center justify-center">
          <div className="text-center rounded-[20px] bg-gray-50 dark:bg-[#151822] px-8 py-10 border border-transparent dark:border-white/5 transition-colors duration-300 ease-in-out">
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-100 transition-colors duration-300 ease-in-out">该功能正在开发中......</p>
          </div>
        </div>

        <footer className="mt-auto pt-4 pb-2 text-center shrink-0">
          <p className="text-xs text-gray-400 dark:text-gray-500 font-normal tracking-wide transition-colors">
            AI 生成内容仅供参考，不构成正式法律意见
          </p>
        </footer>

      </div>
    </main>
  );
}
