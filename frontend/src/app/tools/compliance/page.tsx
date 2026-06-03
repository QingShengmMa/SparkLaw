'use client';

import React, { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  ClipboardCheck,
  FileWarning,
  Loader2,
  RotateCcw,
  Send,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';
import { runAiTool } from '@/lib/api';

type ModuleStatus = '合规' | '风险' | '待确认';

interface ComplianceModule {
  id: string;
  title: string;
  scope: string;
  law: string;
  weight: number;
  status: ModuleStatus;
}

interface CompanyProfile {
  industry: string;
  employees: string;
  city: string;
  payrollMode: string;
  notes: string;
}

const moduleSeed: ComplianceModule[] = [
  { id: 'contract', title: '劳动合同签订', scope: '入职一个月内签订、续签、岗位/薪资条款', law: '《劳动合同法》第10条、第82条', weight: 18, status: '待确认' },
  { id: 'social', title: '社保公积金', scope: '缴纳时间、缴费基数、试用期参保', law: '《社会保险法》第58条、第63条', weight: 20, status: '待确认' },
  { id: 'overtime', title: '工时与加班', scope: '审批流程、调休、加班费、综合工时备案', law: '《劳动法》第36条、第41条、第44条', weight: 17, status: '待确认' },
  { id: 'salary', title: '薪酬发放', scope: '工资结构、绩效扣减、离职结算、工资条', law: '《工资支付暂行规定》第6条、第7条', weight: 13, status: '待确认' },
  { id: 'rules', title: '规章制度', scope: '民主程序、公示送达、奖惩依据', law: '《劳动合同法》第4条', weight: 14, status: '待确认' },
  { id: 'outsourcing', title: '外包/派遣', scope: '混同用工、直接管理、同工同酬', law: '《劳动合同法》第58条、第66条', weight: 16, status: '待确认' },
  { id: 'noncompete', title: '竞业与保密', scope: '适用人员、补偿标准、违约金合理性', law: '《劳动合同法》第23条、第24条', weight: 10, status: '待确认' },
];

const examples: Array<{ title: string; profile: CompanyProfile; statuses: Record<string, ModuleStatus> }> = [
  {
    title: '互联网研发团队',
    profile: {
      industry: '互联网/软件',
      employees: '60',
      city: '杭州',
      payrollMode: '基本工资 + 绩效 + 项目奖金',
      notes: '研发团队经常晚上和周末上线，部分加班只有群通知。销售岗位入职后三个月才缴纳社保。',
    },
    statuses: { contract: '合规', social: '风险', overtime: '风险', salary: '待确认', rules: '待确认', outsourcing: '合规', noncompete: '待确认' },
  },
  {
    title: '外包客服团队',
    profile: {
      industry: '电商/客服',
      employees: '120',
      city: '上海',
      payrollMode: '固定工资 + 绩效',
      notes: '客服与内容审核岗位由外包公司签约，但在公司系统排班，由公司项目经理直接分配任务。',
    },
    statuses: { contract: '待确认', social: '待确认', overtime: '风险', salary: '待确认', rules: '风险', outsourcing: '风险', noncompete: '合规' },
  },
  {
    title: '核心人员竞业',
    profile: {
      industry: '智能硬件',
      employees: '85',
      city: '深圳',
      payrollMode: '月薪 + 年终奖',
      notes: '准备让研发负责人、销售负责人签竞业限制，限制两年，补偿标准为离职前十二个月平均工资的 20%。',
    },
    statuses: { contract: '合规', social: '合规', overtime: '待确认', salary: '合规', rules: '待确认', outsourcing: '合规', noncompete: '风险' },
  },
];

const blankProfile: CompanyProfile = {
  industry: '',
  employees: '',
  city: '',
  payrollMode: '',
  notes: '',
};

function normalizeMarkdown(raw: string) {
  return raw.replace(/\r\n/g, '\n').replace(/^(\d+[.、]\s*)?【([^】]+)】\s*/gm, '### $2\n').trim();
}

function scoreModules(modules: ComplianceModule[]) {
  const deduction = modules.reduce((sum, item) => {
    if (item.status === '风险') return sum + item.weight;
    if (item.status === '待确认') return sum + Math.round(item.weight * 0.35);
    return sum;
  }, 0);
  return Math.max(0, Math.min(100, 100 - deduction));
}

function statusStyle(status: ModuleStatus) {
  if (status === '风险') return 'border-red-100 bg-red-50 text-red-700 dark:border-red-900/40 dark:bg-red-900/10 dark:text-red-300';
  if (status === '合规') return 'border-emerald-100 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-900/10 dark:text-emerald-300';
  return 'border-blue-100 bg-blue-50 text-blue-700 dark:border-blue-900/40 dark:bg-blue-900/10 dark:text-blue-300';
}

export default function CompliancePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<CompanyProfile>(blankProfile);
  const [modules, setModules] = useState<ComplianceModule[]>(moduleSeed);
  const [status, setStatus] = useState<'idle' | 'running' | 'done'>('idle');
  const [report, setReport] = useState('');
  const [error, setError] = useState('');

  const score = useMemo(() => scoreModules(modules), [modules]);
  const riskModules = modules.filter(item => item.status === '风险');
  const unknownModules = modules.filter(item => item.status === '待确认');
  const okModules = modules.filter(item => item.status === '合规');
  const priorities = riskModules.length ? riskModules.slice().sort((a, b) => b.weight - a.weight).slice(0, 3) : unknownModules.slice(0, 3);

  const updateProfile = <K extends keyof CompanyProfile>(key: K, value: CompanyProfile[K]) => {
    setProfile(prev => ({ ...prev, [key]: value }));
  };

  const setModuleStatus = (id: string, next: ModuleStatus) => {
    setModules(prev => prev.map(item => item.id === id ? { ...item, status: next } : item));
  };

  const loadExample = (index: number) => {
    const example = examples[index];
    setProfile(example.profile);
    setModules(moduleSeed.map(item => ({ ...item, status: example.statuses[item.id] || '待确认' })));
    setReport('');
    setStatus('idle');
    setError('');
  };

  const buildPrompt = () => [
    '请根据以下企业用工合规体检数据，输出合规审查报告。要求包含合规评分、重大风险项、待确认事项、法条依据、整改优先级、整改周期和责任部门建议。',
    `行业：${profile.industry || '未填写'}`,
    `员工规模：${profile.employees || '未填写'}`,
    `所在城市：${profile.city || '未填写'}`,
    `薪酬模式：${profile.payrollMode || '未填写'}`,
    `业务说明：${profile.notes || '未填写'}`,
    `前端初评合规分：${score}`,
    '',
    '模块状态：',
    ...modules.map(item => `${item.title}：${item.status}；范围：${item.scope}；对应依据：${item.law}；风险权重：${item.weight}`),
  ].join('\n');

  const runReview = async () => {
    if (!profile.industry.trim() && !profile.notes.trim()) {
      setError('请先填写企业基本情况或用工场景。');
      return;
    }
    setStatus('running');
    setReport('');
    setError('');
    try {
      const response = await runAiTool('compliance', buildPrompt());
      setReport(response.result || '未返回合规审查结果，请稍后重试。');
      setStatus('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : '合规审查失败，请稍后重试。');
      setStatus('idle');
    }
  };

  return (
    <main className="relative flex h-full flex-col overflow-hidden bg-[#FDFDFF] text-[#1F1F1F] transition-colors duration-300 dark:bg-[#0B0D14] dark:text-gray-100">
      <div className="pointer-events-none absolute left-1/2 top-0 h-[260px] w-[560px] -translate-x-1/2 rounded-full bg-blue-50/50 blur-[100px] dark:bg-blue-900/10" />

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
              <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-300">
                <Building2 size={20} strokeWidth={1.9} />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">合规审查</h1>
                <p className="mt-0.5 text-[12px] text-[#6B7280] dark:text-gray-400">模块体检、风险矩阵、整改优先级与责任建议</p>
              </div>
            </div>
          </div>
          <button
            onClick={runReview}
            disabled={status === 'running'}
            className="flex items-center gap-2 rounded-full bg-blue-600 px-5 py-2 text-[13px] font-bold text-white shadow-lg shadow-blue-100 transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:shadow-none dark:shadow-none dark:disabled:bg-gray-700"
          >
            {status === 'running' ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            生成审查报告
          </button>
        </header>

        <section className="grid min-h-0 flex-1 grid-cols-1 gap-5 xl:grid-cols-[390px_1fr_360px]">
          <aside className="flex min-h-0 flex-col gap-4 overflow-y-auto rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ClipboardCheck size={15} className="text-blue-600" />
                <h2 className="text-[13px] font-bold">企业画像</h2>
              </div>
              <button onClick={() => { setProfile(blankProfile); setModules(moduleSeed); setReport(''); setStatus('idle'); }} className="flex items-center gap-1 text-[11px] font-bold text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">
                <RotateCcw size={12} />
                重置
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {examples.map((example, index) => (
                <button key={example.title} onClick={() => loadExample(index)} className="rounded-[14px] border border-blue-100 bg-blue-50/70 px-3 py-2 text-left text-[12px] font-bold text-blue-700 transition-colors hover:bg-blue-100 dark:border-blue-800/30 dark:bg-blue-900/10 dark:text-blue-300">
                  {example.title}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <input value={profile.industry} onChange={(e) => updateProfile('industry', e.target.value)} placeholder="行业" className="h-10 rounded-[12px] border border-gray-100 bg-[#F8FAFC] px-3 text-[13px] outline-none focus:border-blue-300 dark:border-white/10 dark:bg-[#0F1117]" />
              <input value={profile.employees} onChange={(e) => updateProfile('employees', e.target.value)} placeholder="员工数" className="h-10 rounded-[12px] border border-gray-100 bg-[#F8FAFC] px-3 text-[13px] outline-none focus:border-blue-300 dark:border-white/10 dark:bg-[#0F1117]" />
              <input value={profile.city} onChange={(e) => updateProfile('city', e.target.value)} placeholder="城市" className="h-10 rounded-[12px] border border-gray-100 bg-[#F8FAFC] px-3 text-[13px] outline-none focus:border-blue-300 dark:border-white/10 dark:bg-[#0F1117]" />
              <input value={profile.payrollMode} onChange={(e) => updateProfile('payrollMode', e.target.value)} placeholder="薪酬结构" className="h-10 rounded-[12px] border border-gray-100 bg-[#F8FAFC] px-3 text-[13px] outline-none focus:border-blue-300 dark:border-white/10 dark:bg-[#0F1117]" />
            </div>
            <textarea value={profile.notes} onChange={(e) => updateProfile('notes', e.target.value)} placeholder="补充用工场景：社保、加班、外包、规章制度、竞业限制等..." className="h-28 resize-none rounded-[16px] border border-gray-100 bg-[#F8FAFC] p-4 text-[13px] leading-6 outline-none focus:border-blue-300 dark:border-white/10 dark:bg-[#0F1117]" />

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <FileWarning size={15} className="text-blue-600" />
                <h2 className="text-[13px] font-bold">审查模块</h2>
              </div>
              {modules.map(item => (
                <div key={item.id} className="rounded-[18px] border border-gray-100 bg-[#F8FAFC] p-3 dark:border-white/10 dark:bg-white/5">
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[13px] font-bold text-gray-800 dark:text-gray-100">{item.title}</p>
                      <p className="mt-1 text-[11px] leading-5 text-gray-500 dark:text-gray-400">{item.scope}</p>
                    </div>
                    <span className="shrink-0 rounded-full bg-white px-2 py-1 text-[10px] font-black text-blue-700 dark:bg-white/10 dark:text-blue-300">{item.weight}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-1.5">
                    {(['合规', '风险', '待确认'] as ModuleStatus[]).map(next => (
                      <button
                        key={next}
                        onClick={() => setModuleStatus(item.id, next)}
                        className={`rounded-[10px] border px-2 py-1.5 text-[11px] font-bold transition-colors ${
                          item.status === next ? statusStyle(next) : 'border-gray-100 bg-white text-gray-400 hover:bg-gray-50 dark:border-white/10 dark:bg-[#111827] dark:hover:bg-white/10'
                        }`}
                      >
                        {next}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </aside>

          <section className="flex min-h-0 flex-col gap-5 overflow-y-auto">
            <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
              <div className="rounded-[24px] bg-[#1A1C1E] p-5 text-white shadow-sm dark:bg-[#151822] dark:ring-1 dark:ring-white/10">
                <div className="mb-4 flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">Compliance</span>
                  <ShieldCheck size={15} className="text-blue-300" />
                </div>
                <div className="flex items-end gap-2">
                  <span className="text-[46px] font-black leading-none">{score}</span>
                  <span className="mb-1 text-[12px] text-gray-500">/ 100</span>
                </div>
                <p className="mt-3 text-[12px] leading-6 text-gray-400">{score >= 80 ? '整体可控，关注待确认项' : score >= 60 ? '存在明显整改压力' : '重大合规风险需优先处理'}</p>
              </div>

              <div className="rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
                <div className="mb-4 flex items-center gap-2">
                  <ShieldAlert size={16} className="text-blue-600" />
                  <h2 className="text-[13px] font-bold">风险矩阵</h2>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  {[
                    { title: '重大风险', items: riskModules, icon: <AlertCircle size={15} />, cls: 'text-red-600 bg-red-50 border-red-100 dark:bg-red-900/10 dark:border-red-900/40 dark:text-red-300' },
                    { title: '待确认', items: unknownModules, icon: <FileWarning size={15} />, cls: 'text-blue-600 bg-blue-50 border-blue-100 dark:bg-blue-900/10 dark:border-blue-900/40 dark:text-blue-300' },
                    { title: '已合规', items: okModules, icon: <CheckCircle2 size={15} />, cls: 'text-emerald-600 bg-emerald-50 border-emerald-100 dark:bg-emerald-900/10 dark:border-emerald-900/40 dark:text-emerald-300' },
                  ].map(column => (
                    <div key={column.title} className={`min-h-[190px] rounded-[18px] border p-4 ${column.cls}`}>
                      <div className="mb-3 flex items-center justify-between">
                        <span className="text-[12px] font-black">{column.title}</span>
                        {column.icon}
                      </div>
                      <div className="space-y-2">
                        {column.items.length ? column.items.map(item => (
                          <div key={item.id} className="rounded-[12px] bg-white/70 px-3 py-2 text-[11px] font-bold dark:bg-white/5">
                            {item.title}
                          </div>
                        )) : <p className="pt-8 text-center text-[11px] opacity-60">暂无</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-[24px] border border-gray-100/60 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151822]">
              <div className="mb-4 flex items-center gap-2">
                <ClipboardCheck size={16} className="text-blue-600" />
                <h2 className="text-[13px] font-bold">整改优先级</h2>
              </div>
              <div className="grid gap-3 lg:grid-cols-3">
                {priorities.map((item, index) => (
                  <div key={item.id} className="rounded-[18px] border border-gray-100 bg-[#F8FAFC] p-4 dark:border-white/10 dark:bg-white/5">
                    <div className="mb-3 flex items-center justify-between">
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-[12px] font-black text-white">{index + 1}</span>
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${statusStyle(item.status)}`}>{item.status}</span>
                    </div>
                    <h3 className="text-[14px] font-bold">{item.title}</h3>
                    <p className="mt-2 text-[11px] leading-5 text-gray-500 dark:text-gray-400">{item.law}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <aside className="flex min-h-0 flex-col rounded-[24px] border border-gray-100/60 bg-white shadow-sm dark:border-white/10 dark:bg-[#151822]">
            <div className="flex shrink-0 items-center justify-between border-b border-gray-50 px-5 py-4 dark:border-white/10">
              <div className="flex items-center gap-2">
                <Building2 size={15} className="text-blue-600" />
                <h2 className="text-[13px] font-bold">AI 审查报告</h2>
              </div>
              <span className="text-[11px] text-gray-400">{status === 'done' ? '已生成' : '待生成'}</span>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-5">
              {status === 'running' ? (
                <div className="flex h-full min-h-[420px] flex-col items-center justify-center gap-3 text-[13px] text-gray-400">
                  <Loader2 size={24} className="animate-spin text-blue-600" />
                  正在生成整改台账...
                </div>
              ) : report ? (
                <div className="prose prose-sm max-w-none text-[13px] leading-7 dark:prose-invert prose-headings:text-[14px] prose-headings:font-bold">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{normalizeMarkdown(report)}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex h-full min-h-[420px] flex-col items-center justify-center text-center text-[12px] leading-6 text-gray-400">
                  <ShieldCheck className="mb-3 text-blue-500" size={24} />
                  完成模块体检后，生成法条依据、整改周期和责任部门建议。
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
