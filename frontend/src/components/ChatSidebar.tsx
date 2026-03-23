'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  MessageSquare, 
  FileText, 
  Settings, 
  Pin,
  Edit2,
  Trash2,
  Check,
  X
} from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import ThemeToggle from './ThemeToggle';
import ScaleIcon from './ScaleIcon';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

const navigation: NavItem[] = [
  { name: '普法问答', href: '/chat', icon: MessageSquare },
  { name: '合同审查', href: '/contract', icon: FileText },
  { name: '模拟法庭', href: '/debate', icon: () => <ScaleIcon size={18} /> },
  { name: '设置', href: '/settings', icon: Settings },
];

export default function ChatSidebar() {
  const pathname = usePathname();
  const [hoveredSessionId, setHoveredSessionId] = useState<string | null>(null);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  const { 
    sessions, 
    currentSessionId, 
    deleteSession, 
    renameSession, 
    togglePin,
    setCurrentSession,
    getSortedSessions 
  } = useChatStore();

  const sortedSessions = getSortedSessions();

  const handleStartEdit = (session: typeof sessions[0]) => {
    setEditingSessionId(session.id);
    setEditValue(session.customTitle || session.originalTitle);
  };

  const handleSaveEdit = (id: string) => {
    if (editValue.trim()) {
      renameSession(id, editValue.trim());
    }
    setEditingSessionId(null);
  };

  const handleCancelEdit = () => {
    setEditingSessionId(null);
    setEditValue('');
  };

  const handleDelete = (id: string) => {
    if (confirm('确定要删除这个对话吗？')) {
      deleteSession(id);
    }
  };

  const getDisplayTitle = (session: typeof sessions[0]) => {
    return session.customTitle || session.originalTitle;
  };

  const formatDate = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    const oneDay = 24 * 60 * 60 * 1000;

    if (diff < oneDay) {
      return '今天';
    } else if (diff < 2 * oneDay) {
      return '昨天';
    } else if (diff < 7 * oneDay) {
      return `${Math.floor(diff / oneDay)} 天前`;
    } else {
      return new Date(timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div className="flex h-screen w-64 flex-col border-r border-border bg-card">
      {/* Header */}
      <div className="flex h-16 items-center justify-between border-b border-border px-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-legal shadow-lg">
            <ScaleIcon size={20} className="text-white" withFire={true} />
          </div>
          <span className="font-serif text-xl font-bold text-foreground">SparkLaw</span>
        </Link>
      </div>

      {/* Navigation - 分为两个区域 */}
      <div className="flex-1 overflow-y-auto">
        {/* 普法问答功能区 */}
        {pathname === '/chat' && (
          <div className="border-b border-border px-3 py-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">普法问答</span>
            </div>
            
            {/* 新建对话按钮 */}
            <button
              onClick={() => {
                const title = `新对话 ${new Date().toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}`;
                const newSessionId = useChatStore.getState().createSession(title);
                useChatStore.getState().setCurrentSession(newSessionId);
              }}
              className="mb-3 w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-smooth hover:bg-primary/90 focus-ring"
            >
              + 新建对话
            </button>

            {/* 历史记录 */}
            <div className="mb-2 text-xs font-medium text-muted-foreground">
              历史记录
            </div>
            <div className="space-y-1">
              {sortedSessions.map((session) => (
                <div
                  key={session.id}
                  className="group relative"
                  onMouseEnter={() => setHoveredSessionId(session.id)}
                  onMouseLeave={() => setHoveredSessionId(null)}
                >
                  {editingSessionId === session.id ? (
                    // Editing Mode
                    <div className="flex items-center gap-1 rounded-lg bg-accent px-2 py-1.5">
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveEdit(session.id);
                          if (e.key === 'Escape') handleCancelEdit();
                        }}
                        className="flex-1 bg-transparent text-sm outline-none"
                        autoFocus
                      />
                      <button
                        onClick={() => handleSaveEdit(session.id)}
                        className="rounded p-1 hover:bg-accent-foreground/10 transition-smooth"
                      >
                        <Check size={14} className="text-green-500" />
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="rounded p-1 hover:bg-accent-foreground/10 transition-smooth"
                      >
                        <X size={14} className="text-red-500" />
                      </button>
                    </div>
                  ) : (
                    // Normal Mode
                    <button
                      onClick={() => setCurrentSession(session.id)}
                      className={`
                        w-full rounded-lg px-3 py-2 text-left text-sm transition-smooth
                        ${currentSessionId === session.id
                          ? 'bg-accent text-accent-foreground'
                          : 'text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground'
                        }
                      `}
                    >
                      <div className="flex items-center gap-2">
                        {session.isPinned && (
                          <Pin size={12} className="flex-shrink-0 text-amber-500 dark:text-amber-400" />
                        )}
                        <span className="flex-1 truncate">
                          {getDisplayTitle(session)}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {formatDate(session.updatedAt)}
                      </div>
                    </button>
                  )}

                  {/* Action Buttons (Show on Hover) */}
                  {hoveredSessionId === session.id && editingSessionId !== session.id && (
                    <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded-md bg-card p-1 shadow-md animate-fadeIn">
                      <button
                        onClick={() => togglePin(session.id)}
                        className="rounded p-1 hover:bg-accent transition-smooth"
                        title={session.isPinned ? '取消置顶' : '置顶'}
                      >
                        <Pin 
                          size={14} 
                          className={session.isPinned ? 'text-amber-500 dark:text-amber-400' : 'text-muted-foreground'}
                        />
                      </button>
                      <button
                        onClick={() => handleStartEdit(session)}
                        className="rounded p-1 hover:bg-accent transition-smooth"
                        title="重命名"
                      >
                        <Edit2 size={14} className="text-muted-foreground" />
                      </button>
                      <button
                        onClick={() => handleDelete(session.id)}
                        className="rounded p-1 hover:bg-destructive/10 transition-smooth"
                        title="删除"
                      >
                        <Trash2 size={14} className="text-destructive" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 其他功能导航 */}
        <nav className="space-y-1 px-3 py-3">
          <div className="mb-2 text-xs font-medium text-muted-foreground">功能</div>
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`
                  flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-smooth
                  ${isActive 
                    ? 'bg-accent text-accent-foreground' 
                    : 'text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground'
                  }
                `}
              >
                <item.icon size={18} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer */}
      <div className="border-t border-border p-3">
        <ThemeToggle />
      </div>
    </div>
  );
}
