'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';

export default function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { resolvedTheme, setTheme } = useTheme();

  const toggleTheme = () => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  };

  return (
    <button
      onClick={toggleTheme}
      className={`flex items-center rounded-lg text-sm font-medium text-muted-foreground transition-smooth hover:bg-accent hover:text-accent-foreground ${compact ? 'w-auto justify-center px-2 py-2 mx-auto' : 'w-full gap-3 px-3 py-2'}`}
      title={compact ? (resolvedTheme === 'dark' ? '切换为浅色模式' : '切换为深色模式') : undefined}
      aria-label={compact ? (resolvedTheme === 'dark' ? '切换为浅色模式' : '切换为深色模式') : undefined}
    >
      {resolvedTheme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      {!compact && (resolvedTheme === 'dark' ? '浅色模式' : '深色模式')}
    </button>
  );
}
