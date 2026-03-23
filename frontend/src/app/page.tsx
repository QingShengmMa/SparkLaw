'use client';

import { FileText, MessageSquare, Settings, Sparkles, Zap, Shield } from 'lucide-react';
import Link from 'next/link';
import ScaleIcon from '@/components/ScaleIcon';
import { useEffect, useState } from 'react';

export default function HomePage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-slate-950 via-blue-950 to-slate-900">
      {/* 动态背景粒子 */}
      <div className="absolute inset-0 overflow-hidden">
        {mounted && [...Array(50)].map((_, i) => (
          <div
            key={i}
            className="particle"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${3 + Math.random() * 4}s`,
            }}
          />
        ))}
      </div>

      {/* 光晕效果 */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl animate-pulse-slow" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />

      {/* 主内容 */}
      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-4 pb-20">
        {/* 中央火焰天秤 */}
        <div className="mb-6 animate-float">
          <div className="relative">
            {/* 外层光环 */}
            <div className="absolute inset-0 animate-spin-slow">
              <div className="h-64 w-64 rounded-full border-2 border-dashed border-blue-400/30" />
            </div>
            <div className="absolute inset-0 animate-spin-reverse">
              <div className="h-64 w-64 rounded-full border-2 border-dotted border-purple-400/30" />
            </div>
            
            {/* 火焰天秤容器 */}
            <div className="relative flex h-64 w-64 items-center justify-center">
              <div className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-600/20 via-purple-600/20 to-orange-600/20 blur-2xl animate-pulse-slow" />
              <div className="relative flex h-48 w-48 items-center justify-center rounded-full bg-gradient-legal shadow-2xl">
                <ScaleIcon size={96} className="text-white" withFire={true} />
              </div>
            </div>
          </div>
        </div>

        {/* 标题 */}
        <div className="text-center mb-4 animate-fadeIn">
          <h1 className="mb-4 bg-gradient-to-r from-blue-400 via-purple-400 to-orange-400 bg-clip-text text-7xl font-bold text-transparent animate-gradient">
            SparkLaw
          </h1>
          <p className="text-xl text-slate-400">
            AI 驱动的智能法律助手 · 开源 · 免费 · 强大
          </p>
        </div>

        {/* 特性标签 */}
        <div className="mb-6 flex flex-wrap items-center justify-center gap-4 animate-fadeIn" style={{ animationDelay: '0.2s' }}>
          <div className="flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-2 backdrop-blur-sm">
            <Zap size={16} className="text-blue-400" />
            <span className="text-sm text-blue-300">LangGraph 多智能体</span>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-purple-500/30 bg-purple-500/10 px-4 py-2 backdrop-blur-sm">
            <Sparkles size={16} className="text-purple-400" />
            <span className="text-sm text-purple-300">实时流式推演</span>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-orange-500/30 bg-orange-500/10 px-4 py-2 backdrop-blur-sm">
            <Shield size={16} className="text-orange-400" />
            <span className="text-sm text-orange-300">专业法律分析</span>
          </div>
        </div>

        {/* 功能卡片 */}
        <div className="grid max-w-4xl grid-cols-1 gap-6 md:grid-cols-3 mb-6 animate-fadeIn" style={{ animationDelay: '0.4s' }}>
          <Link href="/chat">
            <div className="group relative overflow-hidden rounded-2xl border border-blue-500/20 bg-slate-900/50 p-6 backdrop-blur-sm transition-all hover:scale-105 hover:border-blue-500/50 hover:shadow-2xl hover:shadow-blue-500/20">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="relative">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg">
                  <MessageSquare className="text-white" size={28} />
                </div>
                <h3 className="mb-2 text-xl font-bold text-white">普法问答</h3>
                <p className="text-sm text-slate-400">
                  智能法律咨询，支持多轮对话和上下文记忆
                </p>
              </div>
            </div>
          </Link>

          <Link href="/contract">
            <div className="group relative overflow-hidden rounded-2xl border border-purple-500/20 bg-slate-900/50 p-6 backdrop-blur-sm transition-all hover:scale-105 hover:border-purple-500/50 hover:shadow-2xl hover:shadow-purple-500/20">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="relative">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 shadow-lg">
                  <FileText className="text-white" size={28} />
                </div>
                <h3 className="mb-2 text-xl font-bold text-white">合同审查</h3>
                <p className="text-sm text-slate-400">
                  AI 深度审查合同条款，识别风险和陷阱
                </p>
              </div>
            </div>
          </Link>

          <Link href="/debate">
            <div className="group relative overflow-hidden rounded-2xl border border-orange-500/20 bg-slate-900/50 p-6 backdrop-blur-sm transition-all hover:scale-105 hover:border-orange-500/50 hover:shadow-2xl hover:shadow-orange-500/20">
              <div className="absolute inset-0 bg-gradient-to-br from-orange-600/10 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="relative">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 shadow-lg">
                  <ScaleIcon size={28} className="text-white" withFire={true} />
                </div>
                <h3 className="mb-2 text-xl font-bold text-white">模拟法庭</h3>
                <p className="text-sm text-slate-400">
                  多智能体辩论，预测胜诉概率和判决结果
                </p>
              </div>
            </div>
          </Link>
        </div>

        {/* 底部统计 */}
        <div className="mt-8 grid grid-cols-3 gap-8 text-center animate-fadeIn" style={{ animationDelay: '0.6s' }}>
          <div>
            <div className="mb-2 text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">3</div>
            <div className="text-sm text-slate-400">核心功能模块</div>
          </div>
          <div>
            <div className="mb-2 text-4xl font-bold bg-gradient-to-r from-purple-400 to-orange-400 bg-clip-text text-transparent">5+</div>
            <div className="text-sm text-slate-400">审查维度</div>
          </div>
          <div>
            <div className="mb-2 text-4xl font-bold bg-gradient-to-r from-orange-400 to-blue-400 bg-clip-text text-transparent">24/7</div>
            <div className="text-sm text-slate-400">全天候服务</div>
          </div>
        </div>
      </div>
    </div>
  );
}
