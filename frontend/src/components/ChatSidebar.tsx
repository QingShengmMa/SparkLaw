'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { MessageSquare, MoreHorizontal, Pencil, Pin, Plus, Scale, Trash2, Wrench, PanelLeftClose, PanelLeftOpen, Settings, type LucideIcon } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import ScaleIcon from './ScaleIcon';
import { useChatStore } from '@/store/chatStore';

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
}

const navigation: NavItem[] = [
  { name: '普法问答', href: '/chat', icon: MessageSquare },
  { name: '法律工具', href: '/tools', icon: Wrench },
  { name: '模拟法庭', href: '/debate', icon: Scale },
];

export default function ChatSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const renameInputRef = useRef<HTMLInputElement>(null);
  const menuRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const [hoverSessionId, setHoverSessionId] = useState<string | null>(null);
  const [menuSessionId, setMenuSessionId] = useState<string | null>(null);
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [renamingValue, setRenamingValue] = useState('');
  const [deleteTargetSessionId, setDeleteTargetSessionId] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  const { createDraftSession, setCurrentSession, deleteSession, renameSession, togglePin, getSortedSessions, currentSessionId } = useChatStore();
  const sessions = getSortedSessions();
  const deletingSession = sessions.find((s) => s.id === deleteTargetSessionId);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (renamingSessionId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [renamingSessionId]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!menuSessionId) return;
      const target = menuRefs.current[menuSessionId];
      if (!target) return;
      if (!target.contains(event.target as Node)) setMenuSessionId(null);
    };

    window.addEventListener('mousedown', handleClickOutside);
    return () => window.removeEventListener('mousedown', handleClickOutside);
  }, [menuSessionId]);

  const isActiveRoute = (href: string) => {
    if (href === '/chat') return pathname === '/chat';
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const handleCreateSession = () => {
    const id = createDraftSession();
    setCurrentSession(id);
    router.push('/chat');
  };

  const startRename = (id: string, title: string) => {
    setMenuSessionId(null);
    setRenamingSessionId(id);
    setRenamingValue(title);
  };

  const submitRename = (id: string, fallback: string) => {
    renameSession(id, renamingValue.trim() || fallback);
    setRenamingSessionId(null);
    setRenamingValue('');
  };

  const cancelRename = () => {
    setRenamingSessionId(null);
    setRenamingValue('');
  };

  const visibleSessions = mounted ? sessions : [];

  const formatCreatedAt = (timestamp: number) => {
    const d = new Date(timestamp);
    const pad = (v: number) => String(v).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  };

  return (
    <>
      <aside className={`flex h-screen ${collapsed ? 'w-20' : 'w-72'} flex-col border-r border-gray-200 dark:border-white/10 bg-white dark:bg-[#0B0D14] transition-all duration-300 ease-in-out`}>
        <div className="border-b border-gray-100 dark:border-white/10 px-3 py-4 transition-colors duration-300 ease-in-out">
          <div className={`mb-4 flex items-center ${collapsed ? 'justify-center' : 'justify-between'}`}>
            <Link href="/" className={`flex items-center ${collapsed ? 'justify-center' : 'gap-2'}`}>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-legal shadow-sm">
                <ScaleIcon size={20} className="text-white" withFire={true} />
              </div>
              {!collapsed && <span className="font-serif text-xl font-bold text-slate-900 dark:text-gray-100 transition-colors duration-300 ease-in-out">SparkLaw</span>}
            </Link>
            {!collapsed && (
              <button type="button" onClick={() => setCollapsed(true)} className="p-1.5 rounded-md text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition" title="收起侧边栏">
                <PanelLeftClose size={16} />
              </button>
            )}
          </div>

          {collapsed ? (
            <div className="space-y-2">
              <button type="button" onClick={() => setCollapsed(false)} className="mx-auto flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-50 hover:text-blue-600 dark:text-gray-400 dark:hover:bg-white/10" title="展开侧边栏">
                <PanelLeftOpen size={18} />
              </button>
              <button type="button" onClick={handleCreateSession} className="mx-auto flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-white shadow-sm hover:bg-blue-700" title="新建对话">
                <Plus size={16} />
              </button>
              <nav className="mt-2 space-y-1">
                {navigation.map((item) => {
                  const isActive = isActiveRoute(item.href);
                  return (
                    <Link key={item.href} href={item.href} className={`mx-auto flex h-9 w-9 items-center justify-center rounded-lg transition-colors duration-300 ease-in-out ${isActive ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-300' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/10 hover:text-gray-700 dark:hover:text-gray-100'}`} title={item.name}>
                      <item.icon size={18} className="shrink-0" />
                    </Link>
                  );
                })}
              </nav>
            </div>
          ) : (
            <>
              <button type="button" onClick={handleCreateSession} className="mb-5 flex w-full items-center justify-center gap-2 rounded-full bg-blue-600 py-2.5 font-medium text-white shadow-sm transition-all hover:bg-blue-700">
                <Plus size={16} />
                <span>新建对话</span>
              </button>

              <p className="mb-3 px-1 text-xs font-semibold uppercase tracking-wide text-gray-400">导航</p>
              <nav className="space-y-2">
                {navigation.map((item) => {
                  const isActive = isActiveRoute(item.href);
                  return (
                    <Link key={item.href} href={item.href} className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-300 ease-in-out ${isActive ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-300' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/10 hover:text-gray-700 dark:hover:text-gray-100'}`}>
                      <item.icon size={18} className="shrink-0" />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </nav>
            </>
          )}
        </div>

        {collapsed ? (
          <div className="mt-auto border-t border-gray-100 p-3 dark:border-slate-800">
            <Link
              href="/settings"
              className={`mx-auto mb-2 flex h-9 w-9 items-center justify-center rounded-lg transition-colors duration-300 ease-in-out ${isActiveRoute('/settings') ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-300' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/10 hover:text-gray-700 dark:hover:text-gray-100'}`}
              title="设置"
            >
              <Settings size={18} className="shrink-0" />
            </Link>
            <ThemeToggle compact />
          </div>
        ) : (
          <>
            <div className="mx-4 my-3 h-px bg-gray-200 dark:bg-white/10 transition-colors duration-300 ease-in-out" />

            <div className="flex min-h-0 flex-1 flex-col px-3 pb-3">
              <p className="mb-3 px-2 text-xs font-semibold uppercase tracking-wide text-gray-400">历史对话</p>
              <div className="flex-1 space-y-2 overflow-y-auto pr-1">
                {visibleSessions.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-[#151822] px-3 py-4 text-xs text-gray-400 dark:text-white/50 transition-colors duration-300 ease-in-out">暂无历史对话</div>
                ) : (
                  visibleSessions.map((session) => {
                    const title = session.customTitle || session.originalTitle;
                    const isCurrent = session.id === currentSessionId;
                    const isRenaming = renamingSessionId === session.id;
                    const showActions = hoverSessionId === session.id || menuSessionId === session.id;

                    return (
                      <div key={session.id} onMouseEnter={() => setHoverSessionId(session.id)} onMouseLeave={() => setHoverSessionId((prev) => (prev === session.id ? null : prev))} className={`group rounded-xl border px-3 py-2.5 transition-all ${isCurrent ? 'border-blue-200 bg-blue-50/70 dark:border-blue-800/70 dark:bg-blue-900/20' : 'border-gray-100 bg-white hover:border-gray-200 hover:bg-gray-50 dark:border-slate-800 dark:bg-slate-950 dark:hover:border-slate-700 dark:hover:bg-slate-900'}`}>
                        <div className="flex items-start gap-2">
                          <button type="button" onClick={() => { setCurrentSession(session.id); router.push('/chat'); }} onDoubleClick={(e) => { e.preventDefault(); startRename(session.id, title); }} className="min-w-0 flex-1 text-left">
                            {isRenaming ? (
                              <input
                                ref={renameInputRef}
                                value={renamingValue}
                                onChange={(e) => setRenamingValue(e.target.value)}
                                onClick={(e) => e.stopPropagation()}
                                onBlur={() => submitRename(session.id, title)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') { e.preventDefault(); submitRename(session.id, title); }
                                  if (e.key === 'Escape') { e.preventDefault(); cancelRename(); }
                                }}
                                className="w-full rounded-md border border-blue-300 bg-white px-2 py-1 text-sm font-medium text-gray-700 outline-none transition-all focus:border-blue-400 focus:ring-2 focus:ring-blue-100 dark:border-blue-700 dark:bg-slate-900 dark:text-slate-100"
                              />
                            ) : (
                              <p className="truncate text-sm font-medium text-gray-700 dark:text-slate-200">{title}</p>
                            )}
                            <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">{formatCreatedAt(session.createdAt)}</p>
                          </button>

                          <div ref={(node) => { menuRefs.current[session.id] = node; }} className={`relative transition-opacity ${showActions ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                            <button type="button" onClick={(e) => { e.stopPropagation(); setMenuSessionId((prev) => (prev === session.id ? null : session.id)); }} className={`rounded-md p-1.5 transition-all ${menuSessionId === session.id ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300' : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-300'}`}>
                              <MoreHorizontal size={14} />
                            </button>

                            {menuSessionId === session.id && (
                              <div className="absolute right-0 top-9 z-20 w-36 rounded-lg border border-gray-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                                <button type="button" onClick={(e) => { e.stopPropagation(); startRename(session.id, title); }} className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 dark:text-slate-200 dark:hover:bg-slate-800"><Pencil size={14} />重命名</button>
                                <button type="button" onClick={(e) => { e.stopPropagation(); togglePin(session.id); setMenuSessionId(null); }} className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 dark:text-slate-200 dark:hover:bg-slate-800"><Pin size={14} />{session.isPinned ? '取消置顶' : '置顶'}</button>
                                <button type="button" onClick={(e) => { e.stopPropagation(); setDeleteTargetSessionId(session.id); setMenuSessionId(null); }} className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"><Trash2 size={14} />删除</button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            <div className="border-t border-gray-100 p-3 dark:border-slate-800">
              <Link
                href="/settings"
                className={`mb-2 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-300 ease-in-out ${isActiveRoute('/settings') ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-300' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/10 hover:text-gray-700 dark:hover:text-gray-100'}`}
              >
                <Settings size={18} className="shrink-0" />
                <span>设置</span>
              </Link>
              <ThemeToggle />
            </div>
          </>
        )}
      </aside>

      {deleteTargetSessionId && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-sm rounded-2xl border border-gray-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900">
            <h3 className="text-base font-semibold text-gray-900 dark:text-slate-100">删除会话</h3>
            <p className="mt-2 text-sm text-gray-600 dark:text-slate-300">确定要删除该会话吗？此操作不可恢复。</p>
            {deletingSession && <p className="mt-2 truncate text-xs text-gray-400 dark:text-slate-500">{deletingSession.customTitle || deletingSession.originalTitle}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setDeleteTargetSessionId(null)} className="rounded-lg border border-gray-200 px-3.5 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">取消</button>
              <button type="button" onClick={() => { deleteSession(deleteTargetSessionId); setDeleteTargetSessionId(null); }} className="rounded-lg bg-red-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-red-700">确认删除</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
