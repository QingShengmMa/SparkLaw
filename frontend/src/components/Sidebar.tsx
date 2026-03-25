'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageSquare, Wrench, Scale, Home, Settings } from 'lucide-react';
import SparkLawLogo from './SparkLawLogo';

const menuItems = [
  { name: '首页',     path: '/',        icon: Home },
  { name: '普法问答', path: '/chat',    icon: MessageSquare },
  { name: '法律工具', path: '/tools',   icon: Wrench },
  { name: '模拟法庭', path: '/court',   icon: Scale },
  { name: '设置',     path: '/settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-secondary text-primary flex flex-col h-screen fixed left-0 top-0 border-r border-primary">
      <div className="p-6 border-b border-primary">
        <div className="flex items-center gap-3 mb-2">
          <SparkLawLogo size={32} />
          <h1 className="text-2xl font-bold gradient-text">SparkLaw</h1>
        </div>
        <p className="text-sm text-tertiary font-medium">法自人民来，理为群众讲</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          // 法律工具：/tools 及其所有子路由高亮
          const isActive =
            item.path === '/tools'
              ? pathname === '/tools' || pathname.startsWith('/tools/')
              : pathname === item.path;

          return (
            <Link
              key={item.path}
              href={item.path}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-lg transition-all font-medium text-sm
                ${
                  isActive
                    ? 'bg-gradient-to-r from-orange-600 to-red-600 text-white shadow-lg'
                    : 'text-secondary hover:bg-tertiary hover:text-primary'
                }
              `}
            >
              <Icon size={18} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-primary">
        <p className="text-xs text-tertiary">© 2026 SparkLaw</p>
      </div>
    </aside>
  );
}
