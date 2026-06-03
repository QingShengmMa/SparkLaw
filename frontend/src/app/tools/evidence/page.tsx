'use client';

import React, { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  AlertCircle,
  ArrowLeft,
  Camera,
  CheckCircle2,
  FileCheck2,
  FilePlus2,
  Loader2,
  Plus,
  RotateCcw,
  Scale,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { runAiTool } from '@/lib/api';

type EvidenceType = '电子数据' | '书证' | '转账流水' | '录音录像' | '证人证言' | '鉴定/检测';
type ObtainWay = '自行保存' | '对方提供' | '第三方平台' | '公开渠道' | '司法调取' | '其他';

interface EvidenceItem {
  id: string;
  name: string;
  type: EvidenceType;
  obtainWay: ObtainWay;
  purpose: string;
  detail: string;
  hasOriginal: boolean;
  chainComplete: boolean;
  opponentRisk: '低' | '中' | '高';
}

const blankDraft: EvidenceItem = {
  id: '',
  name: '',
  type: '电子数据',
  obtainWay: '自行保存',
  purpose: '',
  detail: '',
  hasOriginal: false,
  chainComplete: false,
  opponentRisk: '中',
};

const examples: Array<{ title: string; goal: string; items: EvidenceItem[] }> = [
  {
    title: '劳动加班举证',
    goal: '证明公司安排周末及夜间加班，且未依法支付加班费。',
    items: [
      {
        id: 'sample-1',
        name: '微信群加班通知截图',
        type: '电子数据',
        obtainWay: '自行保存',
        purpose: '证明主管在休息日安排劳动者到岗处理上线问题。',
        detail: '截图包含群名、主管昵称、发送时间、加班任务和回复记录，尚未导出原始聊天记录。',
        hasOriginal: false,
        chainComplete: false,
        opponentRisk: '中',
      },
      {
        id: 'sample-2',
        name: '考勤系统导出表',
        type: '书证',
        obtainWay: '第三方平台',
        purpose: '证明实际打卡时间与标准工时不一致。',
        detail: '导出表覆盖近 6 个月，包含上下班打卡时间，但缺少公司盖章确认。',
        hasOriginal: true,
        chainComplete: true,
        opponentRisk: '低',
      },
    ],
  },
  {
    title: '租赁押金争议',
    goal: '证明房东单方要求提前搬离，并拒绝退还押金。',
    items: [
      {
        id: 'sample-3',
        name: '押金转账记录',
        type: '转账流水',
        obtainWay: '第三方平台',
        purpose: '证明承租人已向房东支付押金及租金。',
        detail: '银行流水显示付款时间、收款人姓名和备注“押金”。',
        hasOriginal: true,
        chainComplete: true,
        opponentRisk: '低',
      },
      {
        id: 'sample-4',
        name: '与房东通话录音',
        type: '录音录像',
        obtainWay: '自行保存',
        purpose: '证明房东承认要求提前退租，且表示押金暂不退还。',
        detail: '录音中能听清双方谈到房屋地址、押金金额和搬离时间，未做公证保全。',
        hasOriginal: true,
        chainComplete: false,
        opponentRisk: '中',
      },
    ],
  },
];

function newId() {
  return `${Date.now()}-${Math.round(Math.random() * 100000)}`;
}

function getEvidenceScore(item: EvidenceItem) {
  const originalBonus = item.hasOriginal ? 22 : 8;
  const chainBonus = item.chainComplete ? 20 : 8;
  const riskPenalty = item.opponentRisk === '高' ? 24 : item.opponentRisk === '中' ? 12 : 2;
  const typeBonus = item.type === '转账流水' || item.type === '鉴定/检测' ? 12 : item.type === '证人证言' ? 5 : 9;
  const relevance = Math.min(96, 48 + item.purpose.length * 2 + item.detail.length / 8);
  const authenticity = Math.max(20, Math.min(96, 38 + originalBonus + chainBonus + typeBonus - riskPenalty));
  const legality = Math.max(25, Math.min(96, item.obtainWay === '司法调取' ? 92 : 76 + (item.chainComplete ? 8 : 0) - (item.opponentRisk === '高' ? 18 : 0)));
  const total = Math.round(authenticity * 0.34 + legality * 0.26 + relevance * 0.4);
  const level = total >= 82 ? '核心证据' : total >= 68 ? '重要证据' : total >= 52 ? '辅助证据' : '待补强';
  return {
    authenticity: Math.round(authenticity),
    legality: Math.round(legality),
    relevance: Math.round(relevance),
    total,
    level,
  };
}

function normalizeMarkdown(raw: string) {
  return raw.replace(/\r\n/g, '\n').replace(/^(\d+[.、]\s*)?【([^】]+)】\s*/gm, '### $2\n').trim();
}

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="font-medium text-gray-500 dark:text-gray-400">{label}</span>
        <span className="font-bold text-gray-700 dark:text-gray-200">{value}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-gray-100 dark:bg-white/10">
        <div className="h-full rounded-full transition-all" style={{ width: `${value}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

export default function EvidencePage() {
  const router = useRouter();
  const [goal, setGoal] = useState('');
  const [draft, setDraft] = useState<EvidenceItem>(blankDraft);
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [activeId, setActiveId] = useState<string>('');
  const [status, setStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [report, setReport] = useState('');
  const [error, setError] = useState('');

  const scoredItems = useMemo(() => items.map(item => ({ item, score: getEvidenceScore(item) })), [items]);
  const active = scoredItems.find(entry => entry.item.id === activeId) || scoredItems[0];
  const averageScore = scoredItems.length
    ? Math.round(scoredItems.reduce((sum, entry) => sum + entry.score.total, 0) / scoredItems.length)
    : 0;
  const coreCount = scoredItems.filter(entry => entry.score.total >= 68).length;
  const weakCount = scoredItems.filter(entry => entry.score.total < 52).length;

  const addEvidence = () => {
    if (!draft.name.trim() || !draft.purpose.trim()) {
      setError('请至少填写证据名称和证明目的。');
      return;
    }
    const item = { ...draft, id: newId() };
    setItems(prev => [...prev, item]);
    setActiveId(item.id);
    setDraft(blankDraft);
    setError('');
  };

  const loadExample = (index: number) => {
    setGoal(examples[index].goal);
    setItems(examples[index].items);
    setActiveId(examples[index].items[0]?.id || '');
    setReport('');
    setError('');
    setStatus('idle');
  };

  const removeEvidence = (id: string) => {
    setItems(prev => prev.filter(item => item.id !== id));
    if (activeId === id) setActiveId('');
  };

  const buildPrompt = () => [
    '请按证据实务标准评估以下证据包，输出逐项证据表、三性判断、证明力排序、举证风险和补强动作。',
    `待证事实/证明目标：${goal || '未填写，请根据证据描述自行识别'}`,
    '',
    '证据清单：',
    ...items.map((item, index) => {
      const score = getEvidenceScore(item);
      return [
        `${index + 1}. ${item.name}`,
        `类型：${item.type}`,
        `取得方式：${item.obtainWay}`,
        `证明目的：${item.purpose}`,
        `材料描述：${item.detail || '未补充'}`,
        `原件/原始载体：${item.hasOriginal ? '有' : '暂无'}`,
        `形成与保管链条：${item.chainComplete ? '较完整' : '不完整'}`,
        `对方异议风险：${item.opponentRisk}`,
        `前端初评：真实性 ${score.authenticity}，合法性 ${score.legality}，关联性 ${score.relevance}，综合 ${score.total}，等级 ${score.level}`,
      ].join('\n');
    }),
  ].join('\n');

  const runAnalysis = async () => {
    if (!items.length) {
      setError('请先添加至少一项证据。');
      return;
    }
    setStatus('running');
    setError('');
    setReport('');
    try {
      const response = await runAiTool('evidence', buildPrompt());
      setReport(response.result || '未返回证据评估结果，请稍后重试。');
      setStatus('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : '证据评估失败，请稍后重试。');
      setStatus('idle');
    }
  };

  return (
    <main className="relative flex h-full flex-col overflow-hidden bg-[#FDFDFF] text-[#1F1F1F] transition-colors duration-300 dark:bg-[#0B0D14] dark:text-gray-100">
      <div className="pointer-events-none absolute left-1/2 top-0 h-[260px] w-[560px] -translate-x-1/2 rounded-full bg-amber-50/60 blur-[100px] dark:bg-amber-900/10" />

      {error && (
        <div className="fixed right-4 top-4 z-50 flex max-w-[420px] items-center gap-3 rounded-[16px] border border-red-100 bg-white px-5 py-3 text-[13px] text-red-600 shadow-lg dark:border-white/10 dark:bg-[#151822] dark:text-red-400">
          <AlertCircle size={15} />
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-gray-400 hover:text-gray-700">x</button>
        </div>
      )}

      <div className="relative z-10 flex h-full flex-col px-6 pb-2 pt-4 lg:px-8">
        <header className="mb-5 flex shrink-0 items-center justify-between">
          <div className="flex min-w-0 items-center gap-4">
            <button onClick={() => router.push('/tools')} className="rounded-full p-2 text-[#444746] transition-colors hover:bg-[#F0F4F9] active:scale-95 dark:text-gray-400 dark:hover:bg-white/10" aria-label="返回工具页">
              <ArrowLeft size={18} />
            </button>
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-300">
                <Camera size={20} strokeWidth={1.9} />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">证据评估</h1>
                <p className="mt-0.5 text-[12px] text-[#6B7280] dark:text-gray-400">证据清单、三性评分、证明力排序与补强动作</p>
              </div>
            </div>
          </div>
          <button
            onClick={runAnalysis}
            disabled={!items.length || status === 'running'}
            className="flex items-center gap-2 rounded-full bg-amber-500 px-5 py-2 text-[13px] font-bold text-white shadow-lg shadow-amber-100 transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:shadow-none dark:shadow-none dark:disabled:bg-gray-700"
          >
            {status === 'running' ? <Loader2 size={15} className="animate-spin" /> : <Scale size={15} />}
            生成证据意见
          </button>
        </header>

        <section className="grid min-h-0 flex-1 grid-cols-1 gap-5 xl:grid-cols-[380px_1fr_360px]">
          <aside className="flex min-h-0 flex-col gap-4 overflow-y-auto rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-[13px] font-bold text-gray-800 dark:text-gray-100">待证事实</h2>
                <button onClick={() => { setGoal(''); setItems([]); setReport(''); setActiveId(''); }} className="text-[11px] font-bold text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">清空</button>
              </div>
              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="例如：证明公司安排休息日加班且未支付加班费。"
                className="h-24 w-full resize-none rounded-[16px] border border-gray-100 bg-[#F8FAFC] p-3 text-[13px] leading-6 outline-none focus:border-amber-200 focus:bg-white focus:ring-2 focus:ring-amber-400/30 dark:border-white/10 dark:bg-[#0F1117] dark:text-gray-100"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              {examples.map((example, index) => (
                <button key={example.title} onClick={() => loadExample(index)} className="rounded-[14px] border border-amber-100 bg-amber-50/70 px-3 py-2 text-left text-[12px] font-bold text-amber-700 transition-colors hover:bg-amber-100 dark:border-amber-800/30 dark:bg-amber-900/10 dark:text-amber-300">
                  {example.title}
                </button>
              ))}
            </div>

            <div className="rounded-[20px] border border-gray-100 bg-[#F8FAFC] p-4 dark:border-white/10 dark:bg-white/5">
              <div className="mb-3 flex items-center gap-2">
                <FilePlus2 size={15} className="text-amber-600" />
                <h2 className="text-[13px] font-bold text-gray-800 dark:text-gray-100">新增证据</h2>
              </div>
              <div className="space-y-3">
                <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="证据名称" className="h-10 w-full rounded-[12px] border border-gray-100 bg-white px-3 text-[13px] outline-none focus:border-amber-300 dark:border-white/10 dark:bg-[#111827]" />
                <div className="grid grid-cols-2 gap-2">
                  <select value={draft.type} onChange={(e) => setDraft({ ...draft, type: e.target.value as EvidenceType })} className="h-10 rounded-[12px] border border-gray-100 bg-white px-3 text-[12px] outline-none dark:border-white/10 dark:bg-[#111827]">
                    {(['电子数据', '书证', '转账流水', '录音录像', '证人证言', '鉴定/检测'] as EvidenceType[]).map(type => <option key={type}>{type}</option>)}
                  </select>
                  <select value={draft.obtainWay} onChange={(e) => setDraft({ ...draft, obtainWay: e.target.value as ObtainWay })} className="h-10 rounded-[12px] border border-gray-100 bg-white px-3 text-[12px] outline-none dark:border-white/10 dark:bg-[#111827]">
                    {(['自行保存', '对方提供', '第三方平台', '公开渠道', '司法调取', '其他'] as ObtainWay[]).map(way => <option key={way}>{way}</option>)}
                  </select>
                </div>
                <textarea value={draft.purpose} onChange={(e) => setDraft({ ...draft, purpose: e.target.value })} placeholder="证明目的" className="h-16 w-full resize-none rounded-[12px] border border-gray-100 bg-white px-3 py-2 text-[13px] outline-none focus:border-amber-300 dark:border-white/10 dark:bg-[#111827]" />
                <textarea value={draft.detail} onChange={(e) => setDraft({ ...draft, detail: e.target.value })} placeholder="材料细节、来源、时间、对方可能异议" className="h-20 w-full resize-none rounded-[12px] border border-gray-100 bg-white px-3 py-2 text-[13px] outline-none focus:border-amber-300 dark:border-white/10 dark:bg-[#111827]" />
                <div className="grid grid-cols-2 gap-2 text-[12px]">
                  <label className="flex items-center gap-2 rounded-[12px] bg-white px-3 py-2 dark:bg-[#111827]">
                    <input type="checkbox" checked={draft.hasOriginal} onChange={(e) => setDraft({ ...draft, hasOriginal: e.target.checked })} />
                    有原始载体
                  </label>
                  <label className="flex items-center gap-2 rounded-[12px] bg-white px-3 py-2 dark:bg-[#111827]">
                    <input type="checkbox" checked={draft.chainComplete} onChange={(e) => setDraft({ ...draft, chainComplete: e.target.checked })} />
                    链条完整
                  </label>
                </div>
                <select value={draft.opponentRisk} onChange={(e) => setDraft({ ...draft, opponentRisk: e.target.value as EvidenceItem['opponentRisk'] })} className="h-10 w-full rounded-[12px] border border-gray-100 bg-white px-3 text-[12px] outline-none dark:border-white/10 dark:bg-[#111827]">
                  {(['低', '中', '高'] as const).map(risk => <option key={risk} value={risk}>对方异议风险：{risk}</option>)}
                </select>
                <button onClick={addEvidence} className="flex h-10 w-full items-center justify-center gap-2 rounded-[14px] bg-amber-500 text-[13px] font-bold text-white transition-colors hover:bg-amber-600">
                  <Plus size={15} />
                  加入证据包
                </button>
              </div>
            </div>
          </aside>

          <section className="flex min-h-0 flex-col rounded-[24px] border border-gray-100/60 bg-white shadow-sm dark:border-white/10 dark:bg-[#151822]">
            <div className="flex shrink-0 items-center justify-between border-b border-gray-50 px-6 py-4 dark:border-white/10">
              <div className="flex items-center gap-2">
                <FileCheck2 size={15} className="text-amber-600" />
                <h2 className="text-[13px] font-bold">证据包评分</h2>
              </div>
              <span className="text-[11px] text-gray-400">{items.length} 项证据</span>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-5">
              {scoredItems.length === 0 ? (
                <div className="flex h-full min-h-[420px] flex-col items-center justify-center text-center">
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-[22px] bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-300">
                    <Camera size={26} />
                  </div>
                  <h3 className="text-[16px] font-bold">先建立证据包</h3>
                  <p className="mt-2 max-w-[360px] text-[12px] leading-6 text-gray-400">添加证据后，这里会按真实性、合法性、关联性计算初评并排序。</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {scoredItems.map(({ item, score }, index) => (
                    <button
                      key={item.id}
                      onClick={() => setActiveId(item.id)}
                      className={`w-full rounded-[18px] border p-4 text-left transition-colors ${
                        active?.item.id === item.id
                          ? 'border-amber-200 bg-amber-50/70 dark:border-amber-800/30 dark:bg-amber-900/10'
                          : 'border-gray-100 bg-[#F8FAFC] hover:bg-white dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10'
                      }`}
                    >
                      <div className="mb-3 flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-[11px] font-black text-amber-700 dark:bg-white/10 dark:text-amber-300">{index + 1}</span>
                            <h3 className="truncate text-[14px] font-bold">{item.name}</h3>
                          </div>
                          <p className="mt-2 line-clamp-2 text-[12px] leading-5 text-gray-500 dark:text-gray-400">{item.purpose}</p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="text-[26px] font-black leading-none text-gray-900 dark:text-gray-100">{score.total}</p>
                          <p className="mt-1 text-[10px] font-bold text-amber-700 dark:text-amber-300">{score.level}</p>
                        </div>
                      </div>
                      <div className="grid gap-2 md:grid-cols-3">
                        <ScoreBar label="真实性" value={score.authenticity} color="#F59E0B" />
                        <ScoreBar label="合法性" value={score.legality} color="#0F9D58" />
                        <ScoreBar label="关联性" value={score.relevance} color="#4285F4" />
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </section>

          <aside className="flex min-h-0 flex-col gap-4 overflow-y-auto">
            <div className="rounded-[24px] bg-[#1A1C1E] p-5 text-white dark:bg-[#151822] dark:ring-1 dark:ring-white/10">
              <div className="mb-4 flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">Evidence Index</span>
                <ShieldCheck size={15} className="text-amber-300" />
              </div>
              <div className="flex items-end gap-2">
                <span className="text-[42px] font-black leading-none">{averageScore || '--'}</span>
                <span className="mb-1 text-[12px] text-gray-500">/ 100</span>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3 text-[12px]">
                <div className="rounded-[14px] bg-white/5 p-3">
                  <p className="text-gray-500">核心/重要</p>
                  <p className="mt-1 text-xl font-black">{coreCount}</p>
                </div>
                <div className="rounded-[14px] bg-white/5 p-3">
                  <p className="text-gray-500">待补强</p>
                  <p className="mt-1 text-xl font-black">{weakCount}</p>
                </div>
              </div>
            </div>

            {active && (
              <div className="rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-widest text-gray-400">当前证据</p>
                    <h3 className="mt-1 text-[15px] font-bold">{active.item.name}</h3>
                  </div>
                  <button onClick={() => removeEvidence(active.item.id)} className="rounded-full p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20">
                    <Trash2 size={15} />
                  </button>
                </div>
                <div className="space-y-2 text-[12px] leading-6 text-gray-500 dark:text-gray-400">
                  <p><span className="font-bold text-gray-700 dark:text-gray-200">类型：</span>{active.item.type}</p>
                  <p><span className="font-bold text-gray-700 dark:text-gray-200">取得：</span>{active.item.obtainWay}</p>
                  <p><span className="font-bold text-gray-700 dark:text-gray-200">说明：</span>{active.item.detail || '暂无补充说明'}</p>
                </div>
              </div>
            )}

            <div className="min-h-[300px] rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-[13px] font-bold">AI 证据意见</h2>
                {status === 'done' && (
                  <button onClick={() => { setReport(''); setStatus('idle'); }} className="rounded-full p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-white/10">
                    <RotateCcw size={13} />
                  </button>
                )}
              </div>
              {status === 'running' ? (
                <div className="flex min-h-[220px] flex-col items-center justify-center gap-3 text-[13px] text-gray-400">
                  <Loader2 size={22} className="animate-spin text-amber-600" />
                  正在评估证据链...
                </div>
              ) : report ? (
                <div className="prose prose-sm max-w-none text-[13px] leading-7 dark:prose-invert prose-headings:text-[14px] prose-headings:font-bold">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{normalizeMarkdown(report)}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex min-h-[220px] flex-col items-center justify-center text-center text-[12px] leading-6 text-gray-400">
                  <CheckCircle2 className="mb-3 text-amber-500" size={22} />
                  证据包完成后可生成逐项证据意见、补强清单和庭审使用顺序。
                </div>
              )}
            </div>
          </aside>
        </section>

        <footer className="mt-auto shrink-0 pb-2 pt-4 text-center">
          <p className="text-xs font-normal tracking-wide text-gray-400 dark:text-white/50">AI 生成内容仅供参考，不构成正式法律意见</p>
        </footer>
      </div>
    </main>
  );
}
