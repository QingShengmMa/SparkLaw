'use client';

import { useState, useEffect, useRef } from 'react';
import { Loader2, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ScaleIcon from '@/components/ScaleIcon';
import { getApiBaseUrl } from '@/lib/api';

interface Message {
  role: 'plaintiff' | 'defendant' | 'judge';
  content: string;
}

interface JudgeResult {
  plaintiff_win_rate: number;
  plaintiff_winning_factors: string[];
  defendant_winning_factors: string[];
  judge_summary: string;
}

export default function DebatePage() {
  const [caseDescription, setCaseDescription] = useState('');
  const [debating, setDebating] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [currentRole, setCurrentRole] = useState<'plaintiff' | 'defendant' | 'judge' | null>(null);
  const [judgeResult, setJudgeResult] = useState<JudgeResult | null>(null);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentMessage]);

  const exampleCases = [
    '员工张三因拒绝周末加班被公司以严重违反规章制度为由辞退。张三认为公司要求的加班不合理，且未支付加班费，公司辞退行为违法。公司则认为张三多次拒绝工作安排，严重影响工作进度，符合公司规章制度规定的辞退条件。',
    '租客李四租住房屋期间，因楼上漏水导致家具损坏。李四要求房东赔偿损失并减免租金，房东认为漏水是楼上住户责任，与自己无关，拒绝赔偿。李四认为房东有维修义务，应承担连带责任。',
    '外包程序员王五完成项目后，公司以代码质量不达标为由拒绝支付尾款。王五认为已按合同要求完成所有功能，公司应支付全款。公司则认为代码存在多处bug，需要返工，不符合验收标准。',
  ];

  const handleDebate = async () => {
    if (!caseDescription.trim() || caseDescription.length < 20) {
      setError('请输入至少20个字符的案情描述');
      return;
    }

    setDebating(true);
    setError('');
    setMessages([]);
    setCurrentMessage('');
    setCurrentRole(null);
    setJudgeResult(null);

    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
    let accumulatedMessage = ''; // 使用局部变量累积消息

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2分钟超时

      const apiBaseUrl = getApiBaseUrl();
      const apiKey = localStorage.getItem('sparklaw_api_key');
      const baseUrl = localStorage.getItem('sparklaw_base_url');
      const model = localStorage.getItem('sparklaw_model');
      const temperature = localStorage.getItem('sparklaw_temperature');
      const maxTokens = localStorage.getItem('sparklaw_max_tokens');

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (apiKey) headers['X-API-Key'] = apiKey;
      if (baseUrl) headers['X-API-Base-URL'] = baseUrl;
      if (model) headers['X-API-Model'] = model;
      if (temperature) headers['X-API-Temperature'] = temperature;
      if (maxTokens) headers['X-API-Max-Tokens'] = maxTokens;

      const response = await fetch(`${apiBaseUrl}/api/analysis/debate/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ case_description: caseDescription }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`服务器错误 (${response.status}): ${errorText || '请稍后重试'}`);
      }

      reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('无法读取响应流');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.event === 'start') {
                setCurrentRole(data.role);
                setCurrentMessage('');
                accumulatedMessage = ''; // 重置累积消息
              } else if (data.event === 'content') {
                accumulatedMessage += data.content;
                setCurrentMessage(accumulatedMessage);
              } else if (data.event === 'end') {
                if (accumulatedMessage && data.role) {
                  setMessages(prev => [...prev, {
                    role: data.role,
                    content: accumulatedMessage
                  }]);
                }
                setCurrentMessage('');
                setCurrentRole(null);
                accumulatedMessage = '';
              } else if (data.event === 'result') {
                setJudgeResult(data.result);
              } else if (data.event === 'error') {
                // 特殊处理速率限制错误
                if (data.message && data.message.includes('Rate limit')) {
                  throw new Error('API 速率限制：今日配额已用完。请等待约 10 分钟后重试，或升级到 Dev Tier。');
                }
                throw new Error(data.message || '辩论过程中出现错误');
              } else if (data.event === 'done') {
                // 辩论完成
                break;
              }
            } catch (parseError) {
              console.error('解析 SSE 数据失败:', parseError, 'Line:', line);
              // 继续处理其他行，不中断整个流程
            }
          }
        }
      }
    } catch (err: any) {
      console.error('辩论失败:', err);
      
      if (err.name === 'AbortError') {
        setError('请求超时（2分钟），请检查网络连接或稍后重试');
      } else if (err.message.includes('Failed to fetch')) {
        setError('无法连接到服务器，请确保后端服务已启动（http://localhost:8000）');
      } else {
        setError(err.message || '辩论模拟失败，请重试');
      }
    } finally {
      // 清理资源
      if (reader) {
        try {
          await reader.cancel();
        } catch (e) {
          console.error('关闭流失败:', e);
        }
      }
      setDebating(false);
      setCurrentMessage('');
      setCurrentRole(null);
    }
  };

  const getRoleStyle = (role: 'plaintiff' | 'defendant' | 'judge') => {
    switch (role) {
      case 'plaintiff':
        return {
          container: 'justify-start',
          bubble: 'bg-red-50 border-red-200 dark:bg-red-950/20 dark:border-red-900/50',
          label: 'text-red-700 dark:text-red-400',
          icon: '👨‍⚖️',
          name: '原告律师'
        };
      case 'defendant':
        return {
          container: 'justify-end',
          bubble: 'bg-blue-50 border-blue-200 dark:bg-blue-950/20 dark:border-blue-900/50',
          label: 'text-blue-700 dark:text-blue-400',
          icon: '👨‍💼',
          name: '被告律师'
        };
      case 'judge':
        return {
          container: 'justify-center',
          bubble: 'bg-amber-50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-900/50',
          label: 'text-amber-700 dark:text-amber-400',
          icon: '⚖️',
          name: '法官'
        };
    }
  };

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="mb-8">
        <h1 className="mb-2 font-serif text-4xl font-bold">AI 模拟法庭</h1>
        <p className="text-muted-foreground">多维抗辩推演，预判争议焦点与裁判逻辑。</p>
      </div>

      {/* 输入区域 */}
      {!debating && messages.length === 0 && (
        <div className="card mb-6 p-6">
          <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold">
            <ScaleIcon size={20} />
            案情描述
          </h2>

          <textarea
            value={caseDescription}
            onChange={(e) => setCaseDescription(e.target.value)}
            placeholder="请详细描述案件情况，包括双方争议焦点、关键事实和证据..."
            className="h-40 w-full resize-none rounded-lg border border-input bg-background p-4 text-foreground placeholder:text-muted-foreground transition-smooth focus-ring"
          />

          <div className="mt-4 flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              {caseDescription.length} / 建议至少 100 字符
            </span>
            <button
              onClick={handleDebate}
              disabled={caseDescription.length < 20}
              className="rounded-lg bg-gradient-legal px-6 py-3 font-medium shadow-lg transition-smooth hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-50 focus-ring"
            >
              <span className="text-foreground dark:text-white">🎭 开始模拟庭审</span>
            </button>
          </div>

          {/* 示例案例 */}
          <div className="mt-6 border-t border-border pt-6">
            <p className="mb-3 text-sm text-muted-foreground">快速填充示例案例：</p>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {exampleCases.map((example, index) => (
                <button
                  key={index}
                  onClick={() => setCaseDescription(example)}
                  className="card-hover p-3 text-left text-sm transition-smooth"
                >
                  <span className="font-medium">案例 {index + 1}</span>
                  <p className="mt-1 line-clamp-2 text-muted-foreground">{example.substring(0, 50)}...</p>
                </button>
              ))}
            </div>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900/50 dark:bg-red-950/20">
              <AlertCircle size={20} className="mt-0.5 flex-shrink-0 text-red-600 dark:text-red-400" />
              <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
            </div>
          )}
        </div>
      )}

      {/* 对抗时间轴 (Versus Timeline) */}
      {(debating || messages.length > 0) && (
        <div className="space-y-6">
          {/* 辩论进行中提示 */}
          {debating && (
            <div className="card flex items-center gap-4 p-4">
              <Loader2 size={24} className="animate-spin text-primary" />
              <div>
                <p className="font-medium">AI 法庭正在模拟辩论...</p>
                <p className="text-sm text-muted-foreground">原告律师、被告律师、法官正在发表意见</p>
              </div>
            </div>
          )}

          {/* 消息气泡流 */}
          <div className="space-y-4">
            {messages.map((message, index) => {
              const style = getRoleStyle(message.role);
              return (
                <div key={index} className={`flex ${style.container} animate-fadeIn`}>
                  <div className={`max-w-[80%] rounded-lg border p-4 ${style.bubble}`}>
                    <div className="mb-2 flex items-center gap-2">
                      <span className="text-2xl">{style.icon}</span>
                      <span className={`font-semibold ${style.label}`}>{style.name}</span>
                    </div>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* 当前正在输入的消息（打字机效果） */}
            {currentRole && currentMessage && (
              <div className={`flex ${getRoleStyle(currentRole).container} animate-fadeIn`}>
                <div className={`max-w-[80%] rounded-lg border p-4 ${getRoleStyle(currentRole).bubble}`}>
                  <div className="mb-2 flex items-center gap-2">
                    <span className="text-2xl">{getRoleStyle(currentRole).icon}</span>
                    <span className={`font-semibold ${getRoleStyle(currentRole).label}`}>
                      {getRoleStyle(currentRole).name}
                    </span>
                  </div>
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {currentMessage}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* 终审判决书 */}
          {judgeResult && !debating && (
            <div className="card border-amber-200 p-6 dark:border-amber-900/50 animate-fadeIn">
              <div className="mb-6 text-center">
                <h2 className="mb-2 font-serif text-2xl font-bold">⚖️ 终审判决书</h2>
                <p className="text-sm text-muted-foreground">AI 法庭综合评议结果</p>
              </div>

              {/* 胜诉概率 */}
              <div className="mb-6 grid grid-cols-2 gap-6">
                <div className="text-center">
                  <div className="mb-2 text-5xl font-bold text-red-500">
                    {judgeResult.plaintiff_win_rate}%
                  </div>
                  <div className="mb-4 text-sm text-muted-foreground">原告胜诉概率</div>
                  <div className="h-3 w-full rounded-full bg-muted">
                    <div
                      className="h-3 rounded-full bg-gradient-to-r from-red-500 to-red-600 transition-all duration-1000"
                      style={{ width: `${judgeResult.plaintiff_win_rate}%` }}
                    />
                  </div>
                </div>

                <div className="text-center">
                  <div className="mb-2 text-5xl font-bold text-blue-500">
                    {100 - judgeResult.plaintiff_win_rate}%
                  </div>
                  <div className="mb-4 text-sm text-muted-foreground">被告胜诉概率</div>
                  <div className="h-3 w-full rounded-full bg-muted">
                    <div
                      className="h-3 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-1000"
                      style={{ width: `${100 - judgeResult.plaintiff_win_rate}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* 深度分析 */}
              <div className="mb-6 grid grid-cols-1 gap-6 md:grid-cols-2">
                {/* 原告有利点 */}
                <div>
                  <h3 className="mb-3 flex items-center gap-2 font-semibold text-red-600 dark:text-red-400">
                    <CheckCircle size={20} />
                    原告有利点
                  </h3>
                  <ul className="space-y-2">
                    {judgeResult.plaintiff_winning_factors.map((factor, index) => (
                      <li key={index} className="flex items-start gap-2 text-sm">
                        <CheckCircle size={16} className="mt-0.5 flex-shrink-0 text-green-500" />
                        <span>{factor}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* 被告有利点 */}
                <div>
                  <h3 className="mb-3 flex items-center gap-2 font-semibold text-blue-600 dark:text-blue-400">
                    <XCircle size={20} />
                    被告有利点（原告败诉点）
                  </h3>
                  <ul className="space-y-2">
                    {judgeResult.defendant_winning_factors.map((factor, index) => (
                      <li key={index} className="flex items-start gap-2 text-sm">
                        <XCircle size={16} className="mt-0.5 flex-shrink-0 text-red-500" />
                        <span>{factor}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* 法官总结 */}
              <div className="border-t border-border pt-6">
                <h3 className="mb-3 font-semibold">法官综合意见</h3>
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {judgeResult.judge_summary}
                  </ReactMarkdown>
                </div>
              </div>

              {/* 重新辩论按钮 */}
              <div className="mt-6 flex justify-center">
                <button
                  onClick={() => {
                    setMessages([]);
                    setJudgeResult(null);
                    setCaseDescription('');
                  }}
                  className="rounded-lg border border-border bg-card px-6 py-2 font-medium transition-smooth hover:bg-accent"
                >
                  重新辩论
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 空状态 */}
      {!debating && messages.length === 0 && !caseDescription && (
        <div className="card p-12 text-center">
          <ScaleIcon size={64} className="mx-auto mb-4 text-muted-foreground/30" />
          <p className="text-muted-foreground">输入案情描述并开始模拟后，辩论结果将显示在这里</p>
        </div>
      )}
    </div>
  );
}
