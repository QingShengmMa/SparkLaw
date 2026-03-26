'use client';

import './globals.css';
import ChatSidebar from '@/components/ChatSidebar';
import { usePathname } from 'next/navigation';

// 通过 link 标签引入 Noto Serif SC（高端中文衬线字体）
const notoSerifSCLink = 'https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600;700;900&display=swap';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isHomePage = pathname === '/';

  return (
    <html lang="zh-CN">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href={notoSerifSCLink} rel="stylesheet" />
        <style dangerouslySetInnerHTML={{ __html: `
          html, body { overflow: hidden; height: 100%; }
          .landing-hero-h1 { font-size: 3rem !important; line-height: 1.1 !important; }
          @media (min-width: 768px) { .landing-hero-h1 { font-size: 4.5rem !important; } }
        ` }} />
      </head>
      <body className="font-sans bg-[#FDFDFF] text-[#1F1F1F] dark:bg-[#0B0D14] dark:text-gray-100 transition-colors duration-300 ease-in-out">
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
