'use client';

import React, { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  Briefcase,
  Gauge,
  Loader2,
  Route,
  Scale,
  Send,
  Target,
  TrendingUp,
} from 'lucide-react';
import { runAiTool } from '@/lib/api';

type DisputeType = '劳动争议' | '合同纠纷' | '房屋租赁' | '民间借贷' | '侵权责任' | '公司股权';
type Stage = '咨询评估' | '证据准备' | '已立案/已受理' | '庭前交换' | '一审审理' | '执行阶段';
type EvidenceGrade = '弱' | '中' | '强';
type Role = '原告/申请人' | '被告/被申请人' | '第三人';
type StrategyPath = '诉讼推进' | '调解和解' | '证据补强';

interface CaseProfile {
  disputeType: DisputeType;
  role: Role;
  stage: Stage;
  evidenceGrade: EvidenceGrade;
  amount: string;
  facts: string;
  claims: string;
  opponent: string;
}

const blankProfile: CaseProfile = {
  disputeType: '劳动争议',
  role: '原告/申请人',
  stage: '证据准备',
  evidenceGrade: '中',
  amount: '',
  facts: '',
  claims: '',
  opponent: '',
};

const examples: Array<{ title: string; profile: CaseProfile }> = [
  {
    title: '社保与加班仲裁',
    profile: {
      disputeType: '劳动争议',
      role: '原告/申请人',
      stage: '证据准备',
      evidenceGrade: '强',
      amount: '约 8 万元，包括经济补偿、加班费和未休年假工资',
      facts: '员工在公司工作四年，公司长期未足额缴纳社保，研发岗位经常周末上线。公司以业务调整为由解除劳动合同，仅愿意支付一个月工资。',
      claims: '主张经济补偿、加班费、未休年假工资，并要求公司补缴社保。',
      opponent: '公司可能抗辩加班未经审批，绩效奖金已包含加班补贴，社保基数按双方约定执行。',
    },
  },
  {
    title: '提前退租押金',
    profile: {
      disputeType: '房屋租赁',
      role: '原告/申请人',
      stage: '咨询评估',
      evidenceGrade: '中',
      amount: '押金 6000 元，搬家及差价损失约 12000 元',
      facts: '房屋租赁尚余九个月，房东以自住装修为由要求承租人提前搬离，并拒绝退还押金。',
      claims: '要求返还押金、赔偿搬家损失及因临时另租产生的差价损失。',
      opponent: '房东可能主张承租人同意协商解除，房屋设施存在损坏，损失金额缺乏票据。',
    },
  },
  {
    title: '借款逾期追偿',
    profile: {
      disputeType: '民间借贷',
      role: '原告/申请人',
      stage: '已立案/已受理',
      evidenceGrade: '中',
      amount: '本金 11 万元，逾期 8 个月，拟主张同期 LPR 利息',
      facts: '出借人向朋友转账 12 万元，对方已归还 1 万元。没有正式借款合同，但聊天记录中多次承认月底还款。',
      claims: '要求偿还剩余本金及逾期利息。',
      opponent: '对方可能抗辩部分款项为合伙投资，聊天记录不是完整上下文。',
    },
  },
];

const strategyText: Record<StrategyPath, string[]> = {
  诉讼推进: ['固定诉求金额', '整理证据目录', '提前准备对方抗辩回应'],
  调解和解: ['设定底线金额', '拆分本金与争议费用', '用证据强项换取快速履行'],
  证据补强: ['补原始载体', '补第三方记录', '补损失票据或计算依据'],
};

function normalizeMarkdown(raw: string) {
  return raw.replace(/\r\n/g, '\n').replace(/^(\d+[.、]\s*)?【([^】]+)】\s*/gm, '### $2\n').trim();
}

function clamp(value: number, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

function calcFactors(profile: CaseProfile) {
  const evidence = profile.evidenceGrade === '强' ? 82 : profile.evidenceGrade === '中' ? 62 : 40;
  const facts = clamp(32 + profile.facts.length / 3 + profile.claims.length / 6);
  const amount = profile.amount.trim().length > 8 ? 78 : profile.amount.trim() ? 58 : 36;
  const defense = profile.opponent.trim().length > 20 ? 62 : profile.opponent.trim() ? 70 : 52;
  const stage = profile.stage === '证据准备' || profile.stage === '咨询评估' ? 72 : profile.stage === '庭前交换' ? 64 : 56;
  const base = Math.round(evidence * 0.34 + facts * 0.24 + amount * 0.14 + defense * 0.14 + stage * 0.14);
  return {
    base,
    optimistic: clamp(base + 12),
    pessimistic: clamp(base - 16),
    factors: [
      { label: '证据强度', value: evidence, color: '#D96570' },
      { label: '事实清晰度', value: Math.round(facts), color: '#4285F4' },
      { label: '金额可计算性', value: Math.round(amount), color: '#0F9D58' },
      { label: '抗辩压力', value: Math.round(defense), color: '#F59E0B' },
      { label: '程序窗口', value: Math.round(stage), color: '#9B72CB' },
    ],
  };
}

function FactorBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-[16px] border border-gray-100 bg-[#F8FAFC] p-3 dark:border-white/10 dark:bg-white/5">
      <div className="mb-2 flex items-center justify-between text-[12px]">
        <span className="font-bold text-gray-700 dark:text-gray-200">{label}</span>
        <span className="font-black" style={{ color }}>{value}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-gray-100 dark:bg-white/10">
        <div className="h-full rounded-full" style={{ width: `${value}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

export default function RiskPredictionPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<CaseProfile>(blankProfile);
  const [strategy, setStrategy] = useState<StrategyPath>('诉讼推进');
  const [status, setStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [report, setReport] = useState('');
  const [error, setError] = useState('');

  const risk = useMemo(() => calcFactors(profile), [profile]);
  const riskLevel = risk.base >= 76 ? '优势较明显' : risk.base >= 60 ? '胜负取决于证据' : '风险偏高';
  const mainGap = risk.factors.slice().sort((a, b) => a.value - b.value)[0];

  const updateProfile = <K extends keyof CaseProfile>(key: K, value: CaseProfile[K]) => {
    setProfile(prev => ({ ...prev, [key]: value }));
  };

  const loadExample = (index: number) => {
    setProfile(examples[index].profile);
    setReport('');
    setStatus('idle');
    setError('');
  };

  const buildPrompt = () => [
    '请基于以下案情画像输出诉讼风险预测。要求包含胜诉概率区间、关键争点、对方抗辩压力、赔偿/补偿金额区间、三条策略路径和下一步行动清单。',
    `纠纷类型：${profile.disputeType}`,
    `当前身份：${profile.role}`,
    `案件阶段：${profile.stage}`,
    `证据强度自评：${profile.evidenceGrade}`,
    `金额/诉求规模：${profile.amount || '未明确'}`,
    `核心事实：${profile.facts || '未填写'}`,
    `主要诉求：${profile.claims || '未填写'}`,
    `对方可能抗辩：${profile.opponent || '未填写'}`,
    `前端模型初算：悲观 ${risk.pessimistic}% / 基准 ${risk.base}% / 乐观 ${risk.optimistic}%，最低因素为${mainGap.label} ${mainGap.value}分。`,
    `用户当前偏好策略：${strategy}`,
  ].join('\n');

  const runPrediction = async () => {
    if (profile.facts.trim().length < 20 || profile.claims.trim().length < 8) {
      setError('请至少填写较完整的核心事实和主要诉求。');
      return;
    }
    setStatus('running');
    setReport('');
    setError('');
    try {
      const response = await runAiTool('risk-prediction', buildPrompt());
      setReport(response.result || '未返回风险预测结果，请稍后重试。');
      setStatus('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : '风险预测失败，请稍后重试。');
      setStatus('idle');
    }
  };

  return (
    <main className="relative flex h-full flex-col overflow-hidden bg-[#FDFDFF] text-[#1F1F1F] transition-colors duration-300 dark:bg-[#0B0D14] dark:text-gray-100">
      <div className="pointer-events-none absolute left-1/2 top-0 h-[260px] w-[560px] -translate-x-1/2 rounded-full bg-rose-50/50 blur-[100px] dark:bg-rose-900/10" />

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
              <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-rose-50 text-rose-600 dark:bg-rose-900/20 dark:text-rose-300">
                <TrendingUp size={20} strokeWidth={1.9} />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">风险预测</h1>
                <p className="mt-0.5 text-[12px] text-[#6B7280] dark:text-gray-400">案情画像、胜率区间、抗辩压力与策略路径</p>
              </div>
            </div>
          </div>
          <button
            onClick={runPrediction}
            disabled={status === 'running'}
            className="flex items-center gap-2 rounded-full bg-rose-500 px-5 py-2 text-[13px] font-bold text-white shadow-lg shadow-rose-100 transition-colors hover:bg-rose-600 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:shadow-none dark:shadow-none dark:disabled:bg-gray-700"
          >
            {status === 'running' ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            生成预测
          </button>
        </header>

        <section className="grid min-h-0 flex-1 grid-cols-1 gap-5 xl:grid-cols-[390px_1fr_360px]">
          <aside className="flex min-h-0 flex-col gap-4 overflow-y-auto rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Briefcase size={15} className="text-rose-600" />
                <h2 className="text-[13px] font-bold">案情画像</h2>
              </div>
              <button onClick={() => { setProfile(blankProfile); setReport(''); setStatus('idle'); }} className="text-[11px] font-bold text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">重置</button>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {examples.map((example, index) => (
                <button key={example.title} onClick={() => loadExample(index)} className="rounded-[14px] border border-rose-100 bg-rose-50/70 px-3 py-2 text-left text-[12px] font-bold text-rose-700 transition-colors hover:bg-rose-100 dark:border-rose-800/30 dark:bg-rose-900/10 dark:text-rose-300">
                  {example.title}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <label className="text-[11px] font-bold text-gray-400">
                纠纷类型
                <select value={profile.disputeType} onChange={(e) => updateProfile('disputeType', e.target.value as DisputeType)} className="mt-1 h-10 w-full rounded-[12px] border border-gray-100 bg-[#F8FAFC] px-3 text-[12px] text-gray-800 outline-none dark:border-white/10 dark:bg-[#0F1117] dark:text-gray-100">
                  {(['劳动争议', '合同纠纷', '房屋租赁', '民间借贷', '侵权责任', '公司股权'] as DisputeType[]).map(type => <option key={type}>{type}</option>)}
                </select>
              </label>
              <label className="text-[11px] font-bold text-gray-400">
                当前身份
                <select value={profile.role} onChange={(e) => updateProfile('role', e.target.value as Role)} className="mt-1 h-10 w-full rounded-[12px] border border-gray-100 bg-[#F8FAFC] px-3 text-[12px] text-gray-800 outline-none dark:border-white/10 dark:bg-[#0F1117] dark:text-gray-100">
                  {(['原告/申请人', '被告/被申请人', '第三人'] as Role[]).map(role => <option key={role}>{role}</option>)}
                </select>
              </label>
              <label className="text-[11px] font-bold text-gray-400">
                案件阶段
                <select value={profile.stage} onChange={(e) => updateProfile('stage', e.target.value as Stage)} className="mt-1 h-10 w-full rounded-[12px] border border-gray-100 bg-[#F8FAFC] px-3 text-[12px] text-gray-800 outline-none dark:border-white/10 dark:bg-[#0F1117] dark:text-gray-100">
                  {(['咨询评估', '证据准备', '已立案/已受理', '庭前交换', '一审审理', '执行阶段'] as Stage[]).map(stage => <option key={stage}>{stage}</option>)}
                </select>
              </label>
              <label className="text-[11px] font-bold text-gray-400">
                证据强度
                <select value={profile.evidenceGrade} onChange={(e) => updateProfile('evidenceGrade', e.target.value as EvidenceGrade)} className="mt-1 h-10 w-full rounded-[12px] border border-gray-100 bg-[#F8FAFC] px-3 text-[12px] text-gray-800 outline-none dark:border-white/10 dark:bg-[#0F1117] dark:text-gray-100">
                  {(['弱', '中', '强'] as EvidenceGrade[]).map(grade => <option key={grade}>{grade}</option>)}
                </select>
              </label>
            </div>

            <input value={profile.amount} onChange={(e) => updateProfile('amount', e.target.value)} placeholder="金额/诉求规模" className="h-11 rounded-[14px] border border-gray-100 bg-[#F8FAFC] px-4 text-[13px] outline-none focus:border-rose-300 dark:border-white/10 dark:bg-[#0F1117]" />
            <textarea value={profile.facts} onChange={(e) => updateProfile('facts', e.target.value)} placeholder="核心事实：时间线、法律关系、关键行为..." className="h-28 resize-none rounded-[16px] border border-gray-100 bg-[#F8FAFC] p-4 text-[13px] leading-6 outline-none focus:border-rose-300 dark:border-white/10 dark:bg-[#0F1117]" />
            <textarea value={profile.claims} onChange={(e) => updateProfile('claims', e.target.value)} placeholder="主要诉求：返还、赔偿、补偿、确认、停止侵害..." className="h-24 resize-none rounded-[16px] border border-gray-100 bg-[#F8FAFC] p-4 text-[13px] leading-6 outline-none focus:border-rose-300 dark:border-white/10 dark:bg-[#0F1117]" />
            <textarea value={profile.opponent} onChange={(e) => updateProfile('opponent', e.target.value)} placeholder="对方可能抗辩：否认事实、合同解释、时效、金额争议..." className="h-24 resize-none rounded-[16px] border border-gray-100 bg-[#F8FAFC] p-4 text-[13px] leading-6 outline-none focus:border-rose-300 dark:border-white/10 dark:bg-[#0F1117]" />
          </aside>

          <section className="flex min-h-0 flex-col gap-5 overflow-y-auto">
            <div className="rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
              <div className="mb-5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Gauge size={16} className="text-rose-600" />
                  <h2 className="text-[13px] font-bold">胜率区间</h2>
                </div>
                <span className="rounded-full border border-rose-100 bg-rose-50 px-3 py-1 text-[11px] font-bold text-rose-700 dark:border-rose-800/30 dark:bg-rose-900/20 dark:text-rose-300">{riskLevel}</span>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                {[
                  { label: '保守情景', value: risk.pessimistic, hint: '证据被削弱或抗辩成立' },
                  { label: '基准情景', value: risk.base, hint: '按当前材料正常推进' },
                  { label: '强化情景', value: risk.optimistic, hint: '补强证据并压低抗辩' },
                ].map(card => (
                  <div key={card.label} className="rounded-[20px] bg-[#F8FAFC] p-4 dark:bg-white/5">
                    <p className="text-[11px] font-bold text-gray-400">{card.label}</p>
                    <div className="mt-3 flex items-end gap-1">
                      <span className="text-[38px] font-black leading-none text-gray-900 dark:text-gray-100">{card.value}</span>
                      <span className="mb-1 text-[12px] text-gray-400">%</span>
                    </div>
                    <p className="mt-3 text-[11px] leading-5 text-gray-500 dark:text-gray-400">{card.hint}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-5 lg:grid-cols-[1fr_280px]">
              <div className="rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
                <div className="mb-4 flex items-center gap-2">
                  <BarChart3 size={16} className="text-rose-600" />
                  <h2 className="text-[13px] font-bold">影响因子</h2>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {risk.factors.map(factor => (
                    <FactorBar key={factor.label} label={factor.label} value={factor.value} color={factor.color} />
                  ))}
                </div>
              </div>

              <div className="rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
                <div className="mb-4 flex items-center gap-2">
                  <Target size={16} className="text-rose-600" />
                  <h2 className="text-[13px] font-bold">最低短板</h2>
                </div>
                <p className="text-[28px] font-black text-gray-900 dark:text-gray-100">{mainGap.label}</p>
                <p className="mt-2 text-[12px] leading-6 text-gray-500 dark:text-gray-400">当前模型认为该因素最可能影响裁判结果，生成报告时会优先给出补强动作。</p>
              </div>
            </div>

            <div className="rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
              <div className="mb-4 flex items-center gap-2">
                <Route size={16} className="text-rose-600" />
                <h2 className="text-[13px] font-bold">策略路径</h2>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                {(Object.keys(strategyText) as StrategyPath[]).map(path => (
                  <button
                    key={path}
                    onClick={() => setStrategy(path)}
                    className={`rounded-[18px] border p-4 text-left transition-colors ${
                      strategy === path
                        ? 'border-rose-200 bg-rose-50/70 dark:border-rose-800/30 dark:bg-rose-900/10'
                        : 'border-gray-100 bg-[#F8FAFC] hover:bg-white dark:border-white/10 dark:bg-white/5'
                    }`}
                  >
                    <p className="text-[13px] font-bold text-gray-800 dark:text-gray-100">{path}</p>
                    <ul className="mt-3 space-y-1 text-[11px] leading-5 text-gray-500 dark:text-gray-400">
                      {strategyText[path].map(item => <li key={item}>· {item}</li>)}
                    </ul>
                  </button>
                ))}
              </div>
            </div>
          </section>

          <aside className="flex min-h-0 flex-col rounded-[24px] border border-gray-100/60 bg-white shadow-sm dark:border-white/10 dark:bg-[#151822]">
            <div className="flex shrink-0 items-center justify-between border-b border-gray-50 px-5 py-4 dark:border-white/10">
              <div className="flex items-center gap-2">
                <Scale size={15} className="text-rose-600" />
                <h2 className="text-[13px] font-bold">AI 风险报告</h2>
              </div>
              <span className="text-[11px] text-gray-400">{status === 'done' ? '已生成' : '待生成'}</span>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-5">
              {status === 'running' ? (
                <div className="flex h-full min-h-[420px] flex-col items-center justify-center gap-3 text-[13px] text-gray-400">
                  <Loader2 size={24} className="animate-spin text-rose-600" />
                  正在推演裁判路径...
                </div>
              ) : report ? (
                <div className="prose prose-sm max-w-none text-[13px] leading-7 dark:prose-invert prose-headings:text-[14px] prose-headings:font-bold">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{normalizeMarkdown(report)}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex h-full min-h-[420px] flex-col items-center justify-center text-center text-[12px] leading-6 text-gray-400">
                  <TrendingUp className="mb-3 text-rose-500" size={24} />
                  完成案情画像后，生成胜率区间、金额区间和策略清单。
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
