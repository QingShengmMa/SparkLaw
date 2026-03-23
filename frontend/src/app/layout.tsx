'use client';

import type { Metadata } from 'next';
import './globals.css';
import ChatSidebar from '@/components/ChatSidebar';
import { usePathname } from 'next/navigation';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isHomePage = pathname === '/';

  return (
    <html lang="zh-CN">
      <body className="font-sans">
        {/* 全局 Dashboard 布局 */}
        <div className="flex h-screen w-full overflow-hidden bg-background">
          {/* 全局侧边栏 - 首页不显示 */}
          {!isHomePage && <ChatSidebar />}
          
          {/* 主内容区域 */}
          <main className={`flex flex-1 flex-col ${isHomePage ? '' : 'overflow-y-auto'}`}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
