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

const SMART_FALLBACK_TITLE = '新的法律咨询';

function truncateByLength(input: string, maxLength: number): string {
  const chars = Array.from(input);
  if (chars.length <= maxLength) return input;
  return `${chars.slice(0, maxLength).join('')}...`;
}

export function generateSmartSessionTitle(seedText?: string): string {
  const text = (seedText || '').replace(/\s+/g, ' ').trim();

  if (!text) {
    return SMART_FALLBACK_TITLE;
  }

  // 更精确的场景命名（先匹配更具体的意图，再匹配泛化意图）
  if (/劳动合同|合同效力|法律效力|是否有效|效力认定/i.test(text)) {
    return '劳动合同效力法律咨询';
  }
  if (/劳动仲裁|仲裁申请|N\+1|2N|经济补偿|赔偿金/i.test(text)) {
    return '劳动仲裁补偿计算咨询';
  }
  if (/竞业|保密协议|限制协议/i.test(text)) {
    return '竞业限制协议效力讨论';
  }
  if (/同案犯|退赃|减轻处罚/i.test(text)) {
    return '关于同案犯退赃的咨询';
  }
  if (/违约|违约金|合同解除|管辖/i.test(text)) {
    return '合同风险与违约责任咨询';
  }
  if (/借款|欠款|逾期|利息|LPR/i.test(text)) {
    return '借贷纠纷与利息计算咨询';
  }

  const firstSentence = text.split(/[。！？!?\n]/)[0]?.trim() || text;
  const normalized = firstSentence
    .replace(/^(请问|我想咨询|我想问|请帮我|帮我|麻烦问下|想问下|关于)/, '')
    .replace(/^[，,\s]+/, '')
    .trim();

  if (!normalized) {
    return SMART_FALLBACK_TITLE;
  }

  if (/[\u4e00-\u9fa5]/.test(normalized)) {
    return truncateByLength(normalized, 16);
  }

  return truncateByLength(normalized, 28);
}

const AUTO_TEMPLATE_TITLES = [
  '劳动合同效力法律咨询',
  '劳动仲裁补偿计算咨询',
  '竞业限制协议效力讨论',
  '关于同案犯退赃的咨询',
  '合同风险与违约责任咨询',
  '借贷纠纷与利息计算咨询',
  SMART_FALLBACK_TITLE,
];

function generateThreadId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `thread_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

interface DraftSession {
  id: string;
  threadId: string;
  createdAt: number;
}

export interface ChatSession {
  id: string;
  threadId: string;
  originalTitle: string;
  customTitle?: string;
  isPinned: boolean;
  pinnedAt?: number | null;
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
  currentThreadId: string | null;
  draftSession: DraftSession | null;
  personality: PersonalityType;

  // Actions
  createSession: (title: string) => string;
  createDraftSession: () => string;
  materializeSessionIfNeeded: (sessionId: string, title?: string) => void;
  isDraftSession: (sessionId?: string | null) => boolean;
  deleteSession: (id: string) => void;
  renameSession: (id: string, customTitle: string) => void;
  updateSessionTitle: (id: string, title: string) => void;
  togglePin: (id: string) => void;
  setCurrentSession: (id: string) => void;
  setCurrentThreadId: (threadId: string | null) => void;
  ensureCurrentThreadId: (sessionId?: string | null) => string;
  addMessage: (sessionId: string, role: 'user' | 'assistant', content: string, sessionTitle?: string) => void;
  getSortedSessions: () => ChatSession[];
  setPersonality: (personality: PersonalityType) => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      currentThreadId: null,
      draftSession: null,
      personality: 'empathy',

      createSession: (title: string) => {
        const threadId = generateThreadId();
        const now = Date.now();
        const newSession: ChatSession = {
          id: `session_${now}_${Math.random().toString(36).substr(2, 9)}`,
          threadId,
          originalTitle: title,
          isPinned: false,
          pinnedAt: null,
          createdAt: now,
          updatedAt: now,
          messages: [],
        };

        set((state) => ({
          sessions: [...state.sessions, newSession],
          currentSessionId: newSession.id,
          currentThreadId: threadId,
          draftSession: null,
        }));

        return newSession.id;
      },

      createDraftSession: () => {
        const now = Date.now();
        const draft: DraftSession = {
          id: `session_${now}_${Math.random().toString(36).substr(2, 9)}`,
          threadId: generateThreadId(),
          createdAt: now,
        };

        set({
          draftSession: draft,
          currentSessionId: draft.id,
          currentThreadId: draft.threadId,
        });

        return draft.id;
      },

      materializeSessionIfNeeded: (sessionId: string, title?: string) => {
        set((state) => {
          const exists = state.sessions.some((s) => s.id === sessionId);
          if (exists) return {};

          const isDraft = state.draftSession?.id === sessionId;
          const threadId = isDraft ? state.draftSession!.threadId : state.currentThreadId || generateThreadId();
          const createdAt = isDraft ? state.draftSession!.createdAt : Date.now();

          const newSession: ChatSession = {
            id: sessionId,
            threadId,
            originalTitle: title || generateSmartSessionTitle(),
            customTitle: title || generateSmartSessionTitle(),
            isPinned: false,
            pinnedAt: null,
            createdAt,
            updatedAt: Date.now(),
            messages: [],
          };

          return {
            sessions: [...state.sessions, newSession],
            draftSession: isDraft ? null : state.draftSession,
            currentThreadId: threadId,
          };
        });
      },

      isDraftSession: (sessionId?: string | null) => {
        const state = get();
        const target = sessionId ?? state.currentSessionId;
        return !!target && state.draftSession?.id === target;
      },

      deleteSession: (id: string) => {
        set((state) => {
          const nextSessions = state.sessions.filter((s) => s.id !== id);
          const isDeletingCurrent = state.currentSessionId === id;
          const isDeletingDraft = state.draftSession?.id === id;

          if (!isDeletingCurrent && !isDeletingDraft) {
            return { sessions: nextSessions };
          }

          return {
            sessions: nextSessions,
            draftSession: isDeletingDraft ? null : state.draftSession,
            currentSessionId: null,
            currentThreadId: null,
          };
        });
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

      updateSessionTitle: (id: string, title: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === id
              ? { ...s, originalTitle: title, customTitle: title, updatedAt: Date.now() }
              : s
          ),
        }));
      },

      togglePin: (id: string) => {
        set((state) => ({
          sessions: state.sessions.map((s) => {
            if (s.id !== id) return s;
            const nextPinned = !s.isPinned;
            return {
              ...s,
              isPinned: nextPinned,
              pinnedAt: nextPinned ? Date.now() : null,
              updatedAt: Date.now(),
            };
          }),
        }));
      },

      setCurrentSession: (id: string) => {
        set((state) => {
          const target = state.sessions.find((s) => s.id === id);
          const draftThreadId = state.draftSession?.id === id ? state.draftSession.threadId : null;
          return {
            currentSessionId: id,
            currentThreadId: target?.threadId || draftThreadId || null,
          };
        });
      },

      setCurrentThreadId: (threadId: string | null) => {
        set({ currentThreadId: threadId });
      },

      ensureCurrentThreadId: (sessionId?: string | null) => {
        const state = get();
        const targetSessionId = sessionId ?? state.currentSessionId;

        if (targetSessionId) {
          const target = state.sessions.find((s) => s.id === targetSessionId);
          if (target?.threadId) {
            if (state.currentThreadId !== target.threadId) set({ currentThreadId: target.threadId });
            return target.threadId;
          }

          if (state.draftSession?.id === targetSessionId) {
            if (state.currentThreadId !== state.draftSession.threadId) {
              set({ currentThreadId: state.draftSession.threadId });
            }
            return state.draftSession.threadId;
          }

          const created = generateThreadId();
          set({ currentThreadId: created });
          return created;
        }

        if (state.currentThreadId) return state.currentThreadId;

        const fallback = generateThreadId();
        set({ currentThreadId: fallback });
        return fallback;
      },

      addMessage: (sessionId: string, role: 'user' | 'assistant', content: string, sessionTitle?: string) => {
        const state = get();
        const exists = state.sessions.some((s) => s.id === sessionId);

        if (!exists) {
          get().materializeSessionIfNeeded(sessionId, sessionTitle || generateSmartSessionTitle(content));
        }

        set((nextState) => ({
          sessions: nextState.sessions.map((s) =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: [...s.messages, { role, content, timestamp: Date.now() }],
                  updatedAt: Date.now(),
                }
              : s
          ),
        }));
      },

      getSortedSessions: () => {
        const { sessions } = get();

        const pinned = sessions
          .filter((s) => s.isPinned)
          .sort((a, b) => (b.pinnedAt || 0) - (a.pinnedAt || 0));

        const unpinned = sessions
          .filter((s) => !s.isPinned)
          .sort((a, b) => b.createdAt - a.createdAt);

        return [...pinned, ...unpinned];
      },

      setPersonality: (personality: PersonalityType) => {
        set({ personality });
      },
    }),
    {
      name: 'sparklaw-chat-storage',
      version: 6,
      migrate: (persistedState: any, version: number) => {
        let next = persistedState || {};

        if (version < 3 && next?.personality === 'cost') {
          next = { ...next, personality: 'cost_expert' };
        }

        if (version < 4 && Array.isArray(next?.sessions)) {
          next = {
            ...next,
            sessions: next.sessions.map((s: any) => ({
              ...s,
              threadId: s?.threadId || generateThreadId(),
            })),
            currentThreadId: next.currentThreadId || null,
          };
        }

        if (version < 6 && Array.isArray(next?.sessions)) {
          next = {
            ...next,
            sessions: next.sessions.map((s: any) => {
              const customTitle = typeof s?.customTitle === 'string' ? s.customTitle : '';
              const originalTitle = typeof s?.originalTitle === 'string' ? s.originalTitle : '';
              const firstUserMessage = Array.isArray(s?.messages)
                ? s.messages.find((m: any) => m?.role === 'user' && typeof m?.content === 'string' && m.content.trim())?.content
                : '';

              const shouldRegenerate =
                !!customTitle &&
                AUTO_TEMPLATE_TITLES.includes(customTitle) &&
                !!firstUserMessage;

              if (!shouldRegenerate) {
                return s;
              }

              const regenerated = generateSmartSessionTitle(firstUserMessage);
              return {
                ...s,
                originalTitle: regenerated,
                customTitle: regenerated,
              };
            }),
          };
        }

        return next;
      },
    }
  )
);
