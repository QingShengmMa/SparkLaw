/**
 * SparkLaw Chat History Store
 * 使用 Zustand + Persist 中间件实现聊天历史的持久化
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// 五大人格类型
export type PersonalityType = 
  | 'machine'      // 冰冷机器
  | 'empathy'      // 共情守护
  | 'cost_expert'  // 成本专家
  | 'aggressive'   // 激进斗士
  | 'educator';    // 普法导师

export interface ChatSession {
  id: string;
  originalTitle: string;
  customTitle?: string;
  isPinned: boolean;
  createdAt: number;
  updatedAt: number;
  messages: Array<{
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
  }>;
}

interface ChatStore {
  sessions: ChatSession[];
  currentSessionId: string | null;
  personality: PersonalityType;
  
  // Actions
  createSession: (title: string) => string;
  deleteSession: (id: string) => void;
  renameSession: (id: string, customTitle: string) => void;
  togglePin: (id: string) => void;
  setCurrentSession: (id: string) => void;
  addMessage: (sessionId: string, role: 'user' | 'assistant', content: string) => void;
  getSortedSessions: () => ChatSession[];
  setPersonality: (personality: PersonalityType) => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      personality: 'empathy', // 默认：共情守护

      createSession: (title: string) => {
        const newSession: ChatSession = {
          id: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          originalTitle: title,
          isPinned: false,
          createdAt: Date.now(),
          updatedAt: Date.now(),
          messages: [],
        };

        set((state) => ({
          sessions: [...state.sessions, newSession],
          currentSessionId: newSession.id,
        }));

        return newSession.id;
      },

      deleteSession: (id: string) => {
        set((state) => ({
          sessions: state.sessions.filter((s) => s.id !== id),
          currentSessionId: state.currentSessionId === id ? null : state.currentSessionId,
        }));
      },

      renameSession: (id: string, customTitle: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === id
              ? { ...s, customTitle, updatedAt: Date.now() }
              : s
          ),
        }));
      },

      togglePin: (id: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === id
              ? { ...s, isPinned: !s.isPinned, updatedAt: Date.now() }
              : s
          ),
        }));
      },

      setCurrentSession: (id: string) => {
        set({ currentSessionId: id });
      },

      addMessage: (sessionId: string, role: 'user' | 'assistant', content: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: [
                    ...s.messages,
                    { role, content, timestamp: Date.now() },
                  ],
                  updatedAt: Date.now(),
                }
              : s
          ),
        }));
      },

      getSortedSessions: () => {
        const { sessions } = get();
        
        // 分离置顶和非置顶会话
        const pinned = sessions.filter((s) => s.isPinned);
        const unpinned = sessions.filter((s) => !s.isPinned);
        
        // 按更新时间排序
        const sortByUpdated = (a: ChatSession, b: ChatSession) => b.updatedAt - a.updatedAt;
        
        return [
          ...pinned.sort(sortByUpdated),
          ...unpinned.sort(sortByUpdated),
        ];
      },

      setPersonality: (personality: PersonalityType) => {
        set({ personality });
      },
    }),
    {
      name: 'sparklaw-chat-storage',
      version: 3,
      migrate: (persistedState: any, version: number) => {
        if (version < 3 && persistedState?.personality === 'cost') {
          return {
            ...persistedState,
            personality: 'cost_expert',
          };
        }
        return persistedState;
      },
    }
  )
);
