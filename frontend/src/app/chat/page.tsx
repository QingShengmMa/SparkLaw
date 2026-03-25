'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getApiBaseUrl } from '@/lib/api';
import { useChatStore, generateSmartSessionTitle } from '@/store/chatStore';
import html2canvas from 'html2canvas';
import ScaleIcon from '@/components/ScaleIcon';

const QUICK_PROMPTS = [
  '同案犯退赃，能否减轻处罚？',
  '劳动仲裁 N+1 补偿如何计算？',
  '竞业限制协议无效的判定标准？',
  '公司单方调岗降薪是否合法？',
];

interface ToolCall {
  name: string;
  input: any;
  status: 'running' | 'success';
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  isError?: boolean;
  statusText?: string;
  tool_calls?: ToolCall[];
}

interface ChatSseEvent {
  event?: string;
  type?: string;
  role?: string;
  message?: string;
  answer?: string;
  content?: string;
  tool_name?: string;
  input?: any;
}

export default function ChatPage() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [enableWebSearch, setEnableWebSearch] = useState(false);
  const [enableDeepThink, setEnableDeepThink] = useState(false);
  const [enableKnowledgeRetrieve, setEnableKnowledgeRetrieve] = useState(false);
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const {
    currentSessionId,
    currentThreadId,
    sessions,
    addMessage,
    createDraftSession,
    setCurrentSession,
    personality,
    updateSessionTitle,
    ensureCurrentThreadId,
    setCurrentThreadId,
    isDraftSession,
  } = useChatStore();

  // 修复"僵尸对话"Bug：检查当前会话是否还存在
  useEffect(() => {
    if (currentSessionId) {
      const currentSession = sessions.find((s) => s.id === currentSessionId);
      const isCurrentDraft = isDraftSession(currentSessionId);

      if (!currentSession && !isCurrentDraft) {
        // 会话已被删除，重置为空状态
        setLocalMessages([]);
        setCurrentSession('');
      } else if (currentSession) {
        // 加载会话消息
        setLocalMessages(currentSession.messages.map((m) => ({
          role: m.role,
          content: m.content,
        })));
        if (!currentThreadId || currentThreadId !== currentSession.threadId) {
          setCurrentThreadId(currentSession.threadId);
        }
      } else {
        // 草稿会话：仅保留空态，不写入历史列表
        setLocalMessages([]);
      }
    } else {
      // 没有当前会话，显示空状态
      setLocalMessages([]);
      if (currentThreadId) {
        setCurrentThreadId(null);
      }
    }
  }, [currentSessionId, sessions, currentThreadId, setCurrentSession, setCurrentThreadId, isDraftSession]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [localMessages, loading]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const updateStreamingAssistant = (
    prev: Message[],
    updater: (current: Message) => Message
  ): Message[] => {
    const copy = [...prev];
    const last = copy[copy.length - 1];

    if (!last || last.role !== 'assistant') {
      copy.push({ role: 'assistant', content: '', tool_calls: [] });
    }

    const current = copy[copy.length - 1];
    copy[copy.length - 1] = updater({
      role: 'assistant',
      content: current.content || '',
      isError: current.isError,
      statusText: current.statusText,
      tool_calls: current.tool_calls || [],
    });

    return copy;
  };

  const getFriendlyErrorMessage = (status?: number): string => {
    if (status === 404) return '请求的服务地址不存在，请检查后端 API 路径配置。';
    if (status === 500) return '服务器暂时开小差了，请稍后重试。';
    if (status === 502 || status === 503 || status === 504) return '服务暂时不可用，请稍后再试。';
    if (status) return `请求失败（${status}），请稍后重试。`;
    return '请求失败，请检查网络或后端服务状态。';
  };

  const handleSend = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || loading) return;

    let sessionId = currentSessionId;
    if (!sessionId) {
      sessionId = createDraftSession();
    }

    const currentSession = sessions.find((s) => s.id === sessionId);
    const shouldCreateTitle = !currentSession || currentSession.messages.length === 0 || isDraftSession(sessionId);
    const autoTitle = generateSmartSessionTitle(messageText);

    if (shouldCreateTitle) {
      updateSessionTitle(sessionId, autoTitle);
    }

    // 确保当前会话绑定一个 thread_id（用于 LangGraph Checkpointer）
    const threadId = ensureCurrentThreadId(sessionId);
    if (!currentThreadId || currentThreadId !== threadId) {
      setCurrentThreadId(threadId);
    }

    const userMessage: Message = { role: 'user', content: messageText };
    setLocalMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    addMessage(sessionId, 'user', messageText, autoTitle);

    // Optimistically add streaming placeholder
    setLocalMessages((prev) => [...prev, { role: 'assistant', content: '', statusText: '思考中...', tool_calls: [] }]);

    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
    let finalAnswer = '';
    let isError = false;
    let errorContent = '';

    try {
      const apiKey = localStorage.getItem('sparklaw_api_key');
      const baseUrl = localStorage.getItem('sparklaw_base_url');
      const model = localStorage.getItem('sparklaw_model');
      const temperature = localStorage.getItem('sparklaw_temperature');
      const maxTokens = localStorage.getItem('sparklaw_max_tokens');

      const headers: HeadersInit = { 'Content-Type': 'application/json' };
      if (apiKey) headers['X-API-Key'] = apiKey;
      if (baseUrl) headers['X-API-Base-URL'] = baseUrl;
      if (model) headers['X-API-Model'] = model;
      if (temperature) headers['X-API-Temperature'] = temperature;
      if (maxTokens) headers['X-API-Max-Tokens'] = maxTokens;

      const resolvedBase = getApiBaseUrl();

      const resp = await fetch(`${resolvedBase}/api/legal/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          question: messageText,
          session_id: sessionId,
          thread_id: threadId,
          personality,
        }),
        signal: AbortSignal.timeout(120_000),
      });

      if (!resp.ok) {
        const userMessage = getFriendlyErrorMessage(resp.status);
        setToast(userMessage);
        throw new Error(userMessage);
      }

      reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (line === 'data: [DONE]') break;
          if (!line.startsWith('data: ')) continue;
          let data: ChatSseEvent;
          try { data = JSON.parse(line.slice(6)) as ChatSseEvent; } catch { continue; }

          const evType: string = data.event || data.type || '';

          if (evType === 'text_chunk') {
            const chunk = data.content || '';
            if (!chunk) continue;
            finalAnswer += chunk;
            setLocalMessages((prev) =>
              updateStreamingAssistant(prev, (current) => ({
                ...current,
                role: 'assistant',
                content: finalAnswer,
                statusText: undefined,
                tool_calls: current.tool_calls || [],
              }))
            );
          } else if (evType === 'tool_start') {
            const toolName = data.tool_name || 'unknown_tool';
            const toolInput = data.input ?? {};
            setLocalMessages((prev) =>
              updateStreamingAssistant(prev, (current) => ({
                ...current,
                role: 'assistant',
                content: current.content || '',
                statusText: `正在调用 ${toolName}...`,
                tool_calls: [
                  ...(current.tool_calls || []),
                  { name: toolName, input: toolInput, status: 'running' as const },
                ],
              }))
            );
          } else if (evType === 'tool_end') {
            const toolName = data.tool_name || 'unknown_tool';
            setLocalMessages((prev) =>
              updateStreamingAssistant(prev, (current) => ({
                ...current,
                role: 'assistant',
                content: current.content || '',
                statusText: undefined,
                tool_calls: (current.tool_calls || []).map((tc) =>
                  tc.name === toolName && tc.status === 'running'
                    ? { ...tc, status: 'success' as const }
                    : tc
                ),
              }))
            );
          } else if (evType === 'tool_call') {
            const toolName = data.tool_name || 'unknown_tool';
            const toolInput = data.input ?? {};
            setLocalMessages((prev) =>
              updateStreamingAssistant(prev, (current) => ({
                ...current,
                role: 'assistant',
                content: current.content || '',
                statusText: `正在调用 ${toolName}...`,
                tool_calls: [
                  ...(current.tool_calls || []),
                  { name: toolName, input: toolInput, status: 'running' as const },
                ],
              }))
            );
          } else if (evType === 'tool_result') {
            const toolName = data.tool_name || 'unknown_tool';
            setLocalMessages((prev) =>
              updateStreamingAssistant(prev, (current) => ({
                ...current,
                role: 'assistant',
                content: current.content || '',
                statusText: undefined,
                tool_calls: (current.tool_calls || []).map((tc) =>
                  tc.name === toolName && tc.status === 'running'
                    ? { ...tc, status: 'success' as const }
                    : tc
                ),
              }))
            );
          } else if (evType === 'final') {
            finalAnswer = data.answer || data.content || finalAnswer;
            setLocalMessages((prev) =>
              updateStreamingAssistant(prev, (current) => ({
                ...current,
                role: 'assistant',
                content: finalAnswer,
                statusText: undefined,
                tool_calls: current.tool_calls || [],
              }))
            );
          } else if (evType === 'error' || data.role === 'error') {
            isError = true;
            errorContent = data.content || data.message || '未知错误';
            setLocalMessages((prev) =>
              updateStreamingAssistant(prev, (current) => ({
                ...current,
                role: 'assistant',
                content: errorContent,
                isError: true,
                statusText: undefined,
                tool_calls: (current.tool_calls || []).map((tc) =>
                  tc.status === 'running' ? { ...tc, status: 'success' as const } : tc
                ),
              }))
            );
          }
        }
      }
    } catch (err: unknown) {
      isError = true;
      const error = err instanceof Error ? err : new Error('未知错误');
      const name = error.name;

      if (name === 'AbortError' || name === 'TimeoutError') {
        errorContent = '请求超时，请检查网络或稍后重试。';
      } else if (error.message.includes('Failed to fetch')) {
        errorContent = '无法连接到服务器，请确认后端已启动。';
      } else {
        errorContent = error.message || '请求失败，请稍后重试。';
      }

      setToast(errorContent);

      setLocalMessages((prev) =>
        updateStreamingAssistant(prev, (current) => ({
          ...current,
          role: 'assistant',
          content: '抱歉，当前服务暂时不可用，请稍后重试。',
          isError: true,
          statusText: undefined,
          tool_calls: (current.tool_calls || []).map((tc) =>
            tc.status === 'running' ? { ...tc, status: 'success' as const } : tc
          ),
        }))
      );
    } finally {
      try { await reader?.cancel(); } catch {}
      setLoading(false);
      const savedContent = isError ? errorContent : finalAnswer;
      addMessage(sessionId, 'assistant', savedContent);
    }
  };

  const handleQuickPrompt = (prompt: string) => {
    handleSend(prompt);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleShareAsImage = async () => {
    if (!chatContainerRef.current || localMessages.length === 0) return;

    try {
      const canvas = await html2canvas(chatContainerRef.current, {
        backgroundColor: '#ffffff',
        scale: 2,
        logging: false,
        useCORS: true,
        allowTaint: true,
      });

      const link = document.createElement('a');
      link.download = `SparkLaw_对话_${new Date().toLocaleDateString()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '生成长图失败，请重试';
      setLocalMessages((prev) => [
        ...prev,
        { role: 'assistant', content: message, isError: true },
      ]);
    }
  };

  return (
    <div className="flex h-screen flex-col items-center overflow-hidden bg-[#FDFDFF] dark:bg-[#0B0D14] text-[#1F1F1F] dark:text-gray-100 transition-colors duration-300 ease-in-out">
      {toast && (
        <div className="fixed right-4 top-4 z-50 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-lg dark:border-amber-900/40 dark:bg-amber-950/60 dark:text-amber-200">
          {toast}
        </div>
      )}
      {/* 主聊天区域 - 水平居中、单列布局 */}
      <div className="flex flex-1 w-full flex-col items-center overflow-y-auto">
        <div className="w-full max-w-4xl px-4 py-8">
          {localMessages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 animate-fadeIn">
              <div className="mb-8 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-legal shadow-lg">
                <ScaleIcon size={40} className="text-white" withFire={true} />
              </div>
              <h2 className="mb-3 text-center font-serif text-3xl font-semibold text-foreground md:text-4xl">
                您好，我是 SparkLaw 法务助手
              </h2>
              <p className="mb-8 text-center text-sm text-muted-foreground md:text-base">
                我可以协助您进行法律问答、案例理解与条款风险识别。
              </p>

              <div className="grid w-full max-w-3xl grid-cols-2 gap-3">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleQuickPrompt(prompt)}
                    className="rounded-xl border border-border bg-card px-5 py-4 text-left transition-all hover:border-blue-500 hover:shadow-md"
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10 dark:bg-primary/20">
                        <ScaleIcon size={16} className="text-primary" />
                      </div>
                      <span className="text-sm font-medium leading-relaxed text-foreground md:text-base">{prompt}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            // Messages - 对话气泡流
            <div ref={chatContainerRef} className="space-y-6">
              {/* Share Button */}
              <div className="mb-4 flex justify-end no-print">
                <button
                  onClick={handleShareAsImage}
                  className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium transition-smooth hover:bg-accent"
                >
                  <Download size={16} />
                  生成长图
                </button>
              </div>

              {localMessages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
                >
                  {/* AI Avatar */}
                  {message.role === 'assistant' && (
                    <div className="mr-3 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gradient-legal">
                      <ScaleIcon size={16} className="text-white" />
                    </div>
                  )}

                  {/* Message Bubble */}
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-muted text-foreground'
                        : message.isError
                        ? 'border border-red-200 bg-red-50 text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400'
                        : 'bg-card border border-border'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                    ) : (
                      <div>
                        {message.tool_calls && message.tool_calls.length > 0 && (
                          <details className="mb-3 rounded-md border border-gray-200 bg-gray-50 px-2 py-2 text-xs text-gray-600" open>
                            <summary className="cursor-pointer select-none font-medium text-gray-600">工具调用轨迹</summary>
                            <div className="mt-2 space-y-2">
                              {message.tool_calls.map((tool, toolIndex) => (
                                <div key={`${tool.name}-${toolIndex}`} className="rounded-md bg-white px-2 py-1">
                                  <div className="flex items-center gap-2">
                                    {tool.status === 'running' ? (
                                      <>
                                        <span className="inline-block h-3 w-3 animate-spin rounded-full border border-gray-400 border-t-transparent" />
                                        <span className="text-gray-500">⚙️ 正在调用 [{tool.name}]...</span>
                                      </>
                                    ) : (
                                      <span className="text-green-600">✅ 完成 [{tool.name}]</span>
                                    )}
                                  </div>
                                  <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-all rounded bg-gray-100 p-2 text-[11px] text-gray-600">
                                    {JSON.stringify(tool.input ?? {}, null, 2)}
                                  </pre>
                                </div>
                              ))}
                            </div>
                          </details>
                        )}

                        {message.statusText && !message.content && (
                          <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
                            <div className="h-2 w-2 animate-pulse rounded-full bg-muted-foreground" />
                            <div className="h-2 w-2 animate-pulse rounded-full bg-muted-foreground" style={{ animationDelay: '0.2s' }} />
                            <div className="h-2 w-2 animate-pulse rounded-full bg-muted-foreground" style={{ animationDelay: '0.4s' }} />
                            <span className="ml-1">{message.statusText}</span>
                          </div>
                        )}

                        {message.isError ? (
                          <div>
                            <p className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-70">系统错误</p>
                            <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed">{message.content}</pre>
                          </div>
                        ) : (
                          <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {message.content}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* User Avatar (optional) */}
                  {message.role === 'user' && (
                    <div className="ml-3 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                      <span className="text-sm font-medium">你</span>
                    </div>
                  )}
                </div>
              ))}

              {/* Loading dots now rendered inside the streaming placeholder bubble */}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="w-full border-t border-border dark:border-white/10 bg-background/80 dark:bg-[#0B0D14]/80 backdrop-blur-md no-print transition-colors duration-300 ease-in-out">
        <div className="mx-auto w-full max-w-4xl px-4 py-4">
          <div className="rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-[#151822] p-3 shadow-sm transition-colors duration-300 ease-in-out focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的法律问题..."
              rows={3}
              className="w-full resize-none bg-transparent px-2 py-1 text-sm text-[#1F1F1F] dark:text-white outline-none placeholder:text-muted-foreground dark:placeholder:text-white/50 transition-colors duration-300 ease-in-out"
              style={{ maxHeight: '220px' }}
            />

            <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => setEnableWebSearch((v) => !v)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-300 ${
                    enableWebSearch
                      ? 'border-blue-200 bg-blue-50 text-blue-600'
                      : 'border-gray-200 bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <span>🔍</span>
                  <span>联网搜索</span>
                </button>

                <button
                  type="button"
                  onClick={() => setEnableDeepThink((v) => !v)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-300 ${
                    enableDeepThink
                      ? 'border-blue-200 bg-blue-50 text-blue-600'
                      : 'border-gray-200 bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <span>🧠</span>
                  <span>深度思考</span>
                </button>

                <button
                  type="button"
                  onClick={() => setEnableKnowledgeRetrieve((v) => !v)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-300 ${
                    enableKnowledgeRetrieve
                      ? 'border-blue-200 bg-blue-50 text-blue-600'
                      : 'border-gray-200 bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <span>📚</span>
                  <span>知识库检索</span>
                </button>
              </div>

              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || loading}
                className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white transition-all hover:bg-blue-700 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send size={16} />
                <span>发送</span>
              </button>
            </div>
          </div>

          <p className="mt-2 text-center text-xs text-muted-foreground">
            内容由 AI 生成，仅供参考，不构成专业法律建议。请谨慎核实。
          </p>
        </div>
      </div>
    </div>
  );
}
