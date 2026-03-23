'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { sendChatMessage } from '@/lib/api';
import { useChatStore } from '@/store/chatStore';
import html2canvas from 'html2canvas';
import ScaleIcon from '@/components/ScaleIcon';

const QUICK_PROMPTS = [
  '解析劳动合同风险',
  '计算法定解除赔偿金',
  '试用期权益保护',
  '竞业限制条款审查',
];

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatPage() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const { currentSessionId, sessions, addMessage, createSession, setCurrentSession, personality } = useChatStore();

  // 修复"僵尸对话"Bug：检查当前会话是否还存在
  useEffect(() => {
    if (currentSessionId) {
      const currentSession = sessions.find(s => s.id === currentSessionId);
      if (!currentSession) {
        // 会话已被删除，重置为空状态
        setLocalMessages([]);
        setCurrentSession('');
      } else {
        // 加载会话消息
        setLocalMessages(currentSession.messages.map(m => ({
          role: m.role,
          content: m.content
        })));
      }
    } else {
      // 没有当前会话，显示空状态
      setLocalMessages([]);
    }
  }, [currentSessionId, sessions, setCurrentSession]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [localMessages, loading]);

  const handleSend = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || loading) return;

    // 如果没有当前会话，创建一个
    let sessionId = currentSessionId;
    if (!sessionId) {
      sessionId = createSession(messageText.slice(0, 30));
    }

    const userMessage: Message = { role: 'user', content: messageText };
    setLocalMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    // 保存到 store
    addMessage(sessionId, 'user', messageText);

    try {
      const response = await sendChatMessage({
        question: messageText,
        session_id: sessionId,
        personality,
      });
      const assistantMessage: Message = { role: 'assistant', content: response.answer };
      setLocalMessages((prev) => [...prev, assistantMessage]);
      
      // 保存到 store
      addMessage(sessionId, 'assistant', response.answer);
    } catch (error: any) {
      let errorMsg = error.message || '处理您的问题时出现错误';
      
      // 特殊处理速率限制错误
      if (errorMsg.includes('Rate limit') || errorMsg.includes('rate_limit_exceeded')) {
        errorMsg = '⚠️ API 速率限制：今日配额已用完\n\n请等待约 10 分钟后重试，或前往设置页面更换 API Key。\n\n提示：Groq 免费版每天有 100,000 tokens 限制。';
      } else if (errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
        errorMsg = '⚠️ 网络连接失败\n\n请检查：\n1. 后端服务是否已启动（http://localhost:8000）\n2. 网络连接是否正常';
      }
      
      const errorMessage: Message = { 
        role: 'assistant', 
        content: `抱歉，${errorMsg}` 
      };
      setLocalMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
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
    } catch (error) {
      console.error('生成长图失败:', error);
      alert('生成长图失败，请重试');
    }
  };

  return (
    <div className="flex h-screen flex-col items-center overflow-hidden">
      {/* 主聊天区域 - 水平居中、单列布局 */}
      <div className="flex flex-1 w-full flex-col items-center overflow-y-auto">
        <div className="w-full max-w-4xl px-4 py-8">
          {localMessages.length === 0 ? (
            // Empty State - 优雅的初始状态
            <div className="flex flex-col items-center justify-center py-12 animate-fadeIn">
              <div className="mb-8 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-legal shadow-lg">
                <ScaleIcon size={40} className="text-white" withFire={true} />
              </div>
              <h2 className="mb-2 font-serif text-2xl font-semibold text-foreground">洞察法理，捍卫权益</h2>
              <p className="mb-8 text-center text-muted-foreground">
                选择下方快捷指令，或直接输入您的问题
              </p>

              {/* Quick Prompts */}
              <div className="grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-2">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleQuickPrompt(prompt)}
                    className="card-hover px-6 py-4 text-left transition-smooth"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10 dark:bg-primary/20">
                        <ScaleIcon size={20} className="text-primary" />
                      </div>
                      <span className="font-medium text-foreground">{prompt}</span>
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
                        : 'bg-card border border-border'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                    ) : (
                      <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
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

              {/* Loading State */}
              {loading && (
                <div className="flex justify-start animate-fadeIn">
                  <div className="mr-3 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gradient-legal">
                    <ScaleIcon size={16} className="text-white" />
                  </div>
                  <div className="card max-w-[80%] border border-border px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 animate-pulse rounded-full bg-muted-foreground"></div>
                      <div className="h-2 w-2 animate-pulse rounded-full bg-muted-foreground" style={{ animationDelay: '0.2s' }}></div>
                      <div className="h-2 w-2 animate-pulse rounded-full bg-muted-foreground" style={{ animationDelay: '0.4s' }}></div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input Area - 吸底 + 毛玻璃效果 */}
      <div className="w-full border-t border-border backdrop-blur-md bg-background/80 no-print">
        <div className="mx-auto w-full max-w-4xl px-4 py-4">
          <div className="flex items-end gap-2 rounded-lg border border-border bg-card p-2 shadow-sm">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的法律问题..."
              rows={1}
              className="flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground"
              style={{ maxHeight: '200px' }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              className="rounded-lg bg-gradient-legal p-2 text-white transition-smooth hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed focus-ring"
            >
              <Send size={20} />
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-muted-foreground">
            内容由 AI 生成，仅供参考，不构成专业法律建议。请谨慎核实。
          </p>
        </div>
      </div>
    </div>
  );
}
