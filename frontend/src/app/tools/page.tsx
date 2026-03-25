'use client';

import Link from 'next/link';
import {
  FileText, Calculator, PenSquare, Camera,
  Building2, TrendingUp, ArrowRight, Scale
} from 'lucide-react';

type Tool = {
  id: string;
  icon: React.ReactNode;
  title: string;
  desc: string;
  href: string;
  accent: string; // tailwind bg color for icon container hover
};

const TOOLS: Tool[] = [
  {
    id: 'contract-review',
    icon: <FileText size={22} strokeWidth={1.8}/>,
    title: '合同审查',
    desc: '上传合同文件，AI 自动扫描高危条款并给出修改建议',
    href: '/tools/contract-review',
    accent: 'group-hover:text-[#4285F4]',
  },
  {
    id: 'calculators',
    icon: <Calculator size={22} strokeWidth={1.8}/>,
    title: '法律计算器',
    desc: 'N/N+1/2N 补偿金、逾期利息、诉讼费阶梯速算',
    href: '/tools/calculators',
    accent: 'group-hover:text-[#0F9D58]',
  },
  {
    id: 'drafting',
    icon: <PenSquare size={22} strokeWidth={1.8}/>,
    title: '文书起草',
    desc: '问答式采集案情，自动生成起诉状、律师函等标准文书',
    href: '/tools/drafting',
    accent: 'group-hover:text-[#9B72CB]',
  },
  {
    id: 'evidence',
    icon: <Camera size={22} strokeWidth={1.8}/>,
    title: '证据评估',
    desc: '从真实性、合法性、关联性三维分析，给出采信度评分',
    href: '/tools/evidence',
    accent: 'group-hover:text-[#F4B400]',
  },
  {
    id: 'risk-prediction',
    icon: <TrendingUp size={22} strokeWidth={1.8}/>,
    title: '风险预测',
    desc: '基于同类案件判例，预测诉讼胜率与潜在赔偿区间',
    href: '/tools/risk-prediction',
    accent: 'group-hover:text-[#D96570]',
  },
  {
    id: 'compliance',
    icon: <Building2 size={22} strokeWidth={1.8}/>,
    title: '合规检查',
    desc: '全链路扫描企业用工风险，输出评分与整改优先级清单',
    href: '/tools/compliance',
    accent: 'group-hover:text-[#1A73E8]',
  },
];

export default function ToolsPage() {
  return (
    <div className="flex flex-col min-h-screen bg-white dark:bg-[#0B0D14] transition-colors duration-300 ease-in-out">
      <div className="flex-1 max-w-[860px] mx-auto w-full px-10 py-14">

        {/* ── Greeting Header ── */}
        <header className="mb-14">
          <h1 className="!text-[36px] !leading-tight !font-medium !font-sans mb-2 !tracking-tight">
            <span className="bg-gradient-to-r from-[#4285F4] via-[#9B72CB] to-[#D96570] bg-clip-text text-transparent">
              您好，
            </span>
          </h1>
          <h2 className="!text-[36px] !leading-tight !font-medium !font-sans text-[#444746] dark:text-gray-300 !tracking-tight transition-colors duration-300 ease-in-out">
            需要处理什么法律事务？
          </h2>
        </header>

        {/* ── Tool Grid ── */}
        <section>
          <div className="grid grid-cols-3 gap-4">
            {TOOLS.map((tool) => (
              <Link
                key={tool.id}
                href={tool.href}
                className="group flex flex-col bg-[#F0F4F9] dark:bg-[#151822] hover:bg-[#E4E9F0] dark:hover:bg-white/10 rounded-[24px] p-6 transition-colors duration-300 ease-in-out outline-none focus-visible:ring-2 focus-visible:ring-[#4285F4]"
              >
                {/* Icon */}
                <div className={`w-11 h-11 rounded-[14px] bg-white dark:bg-white/5 flex items-center justify-center mb-5 text-[#9AA0A6] dark:text-gray-400 transition-colors duration-300 ease-in-out ${tool.accent}`}>
                  {tool.icon}
                </div>

                {/* Text */}
                <h3 className="text-[16px] font-semibold text-[#1F1F1F] dark:text-gray-100 mb-1.5 leading-snug transition-colors duration-300 ease-in-out">
                  {tool.title}
                </h3>
                <p className="text-[13px] text-[#6B7280] dark:text-gray-400 leading-relaxed flex-1 transition-colors duration-300 ease-in-out">
                  {tool.desc}
                </p>

                {/* Arrow */}
                <div className="mt-5 flex items-center gap-1 text-[#9AA0A6] group-hover:text-[#4285F4] transition-colors duration-150">
                  <span className="text-[12px] font-medium">开始使用</span>
                  <ArrowRight size={13} className="translate-x-0 group-hover:translate-x-1 transition-transform duration-150"/>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>

      {/* ── Footer ── */}
      <footer className="mt-auto py-6 text-center transition-colors duration-300 ease-in-out">
        <p className="text-xs text-[#70757a] dark:text-white/50 font-normal tracking-wide">
          AI 生成内容仅供参考，不构成正式法律意见
        </p>
      </footer>
    </div>
  );
}
