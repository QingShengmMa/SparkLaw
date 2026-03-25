import Link from 'next/link';
import {
  MessageSquare,
  Wrench,
  Gavel,
  Github,
  ArrowRight,
} from 'lucide-react';
import ScaleIcon from '@/components/ScaleIcon';

const LandingPage = () => {
  return (
    <div className="h-screen bg-[#FDFDFD] text-slate-600 font-sans overflow-hidden relative flex flex-col selection:bg-blue-100">
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-[10%] -left-[10%] w-[50%] h-[50%] bg-cyan-200/40 blur-[100px] rounded-full mix-blend-multiply" />
        <div className="absolute top-[10%] -right-[10%] w-[40%] h-[50%] bg-purple-200/40 blur-[120px] rounded-full mix-blend-multiply" />
        <div className="absolute -bottom-[20%] left-[20%] w-[60%] h-[60%] bg-blue-300/30 blur-[150px] rounded-full mix-blend-multiply" />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+CjxwYXRoIGQ9Ik0wIDBoNDB2NDBIMHoiIGZpbGw9Im5vbmUiLz4KPHBhdGggZD0iTTAgMTBoNDBNMTAgMHY0ME0wIDIwaDQwTTIwIDB2NDBNMCAzMGg0ME0zMCAwdjQwIiBzdHJva2U9InJnYmEoMCwwLDAsMC4wMikiIHN0cm9rZS13aWR0aD0iMSIvPgo8L3N2Zz4=')] opacity-60" />
      </div>

      <header className="relative z-20 px-6 py-4 md:px-12 flex items-center justify-between border-b border-white/50 bg-white/30 backdrop-blur-md">
        <div className="flex items-center space-x-3 cursor-pointer group">
          <div className="bg-gradient-to-tr from-blue-600 to-cyan-500 p-2 rounded-xl shadow-md group-hover:shadow-lg transition-all duration-300 transform group-hover:-translate-y-0.5">
            <ScaleIcon size={20} className="text-white" withFire={true} />
          </div>
          <span className="text-xl font-extrabold tracking-tight text-slate-800">SparkLaw</span>
        </div>

        <div className="flex items-center space-x-4">
          <a href="https://github.com/QingShengmMa/SparkLaw/blob/main/README.md" target="_blank" rel="noreferrer" className="hidden md:flex items-center text-sm font-medium text-slate-500 hover:text-slate-800 transition">文档</a>
          <a href="https://github.com/QingShengmMa/SparkLaw/blob/main/CONTRIBUTING.md" target="_blank" rel="noreferrer" className="hidden md:flex items-center text-sm font-medium text-slate-500 hover:text-slate-800 transition">贡献指南</a>
          <a
            href="https://github.com/QingShengmMa/SparkLaw"
            target="_blank"
            rel="noreferrer"
            className="flex items-center px-4 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:shadow-md"
          >
            <Github className="w-4 h-4 mr-2" />
            <span>Star on GitHub</span>
          </a>
        </div>
      </header>

      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-4">
        <div className="text-center max-w-4xl mx-auto mb-10">
          <h1 className="text-6xl md:text-8xl font-extrabold tracking-tight leading-tight text-slate-900 mb-4">
            让法律服务
            <br className="md:hidden" />
            <span
              className="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-600 animate-pulse"
              style={{ animationDuration: '4s' }}
            >
              触手可及
            </span>
          </h1>
          <p className="text-lg md:text-xl text-slate-500 max-w-2xl mx-auto leading-relaxed font-medium">
            致力于用纯粹的技术，为你提供优质的法律智能体验。
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-5">
            <Link href="/tools" className="w-full sm:w-auto px-8 py-3.5 rounded-2xl bg-slate-900 hover:bg-slate-800 text-white font-semibold shadow-lg hover:shadow-xl transition-all flex items-center justify-center group transform hover:-translate-y-0.5">
              立即体验
              <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
            </Link>
            <a
              href="https://github.com/QingShengmMa/SparkLaw#部署指南"
              target="_blank"
              rel="noreferrer"
              className="w-full sm:w-auto px-8 py-3.5 rounded-2xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-semibold backdrop-blur-sm shadow-sm hover:shadow-md transition-all flex items-center justify-center transform hover:-translate-y-0.5"
            >
              部署指南
            </a>
          </div>
        </div>

        <div className="w-full max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-6 px-4">
            <Link href="/chat" className="group relative bg-white/70 backdrop-blur-xl border border-white p-7 rounded-[2rem] hover:border-blue-200 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_20px_40px_rgb(37,99,235,0.08)] transition-all duration-300 transform hover:-translate-y-1 block">
              <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mb-5 border border-blue-100 shadow-sm">
                <MessageSquare className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-800 mb-2">普法问答</h3>
              <p className="text-slate-500 text-sm leading-relaxed mb-4">
                日常纠纷不知道怎么办？法条太生涩看不懂？在这里用大白话向 AI 提问，获取通俗易懂的法律解答与指引。
              </p>
              <div className="text-blue-600 text-sm font-semibold flex items-center opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 duration-300">
                开始提问 <ArrowRight className="w-4 h-4 ml-1" />
              </div>
            </Link>

            <Link href="/tools" className="group relative bg-white/70 backdrop-blur-xl border border-white p-7 rounded-[2rem] hover:border-emerald-200 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_20px_40px_rgb(16,185,129,0.08)] transition-all duration-300 transform hover:-translate-y-1 block">
              <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mb-5 border border-emerald-100 shadow-sm">
                <Wrench className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-800 mb-2">实用法律工具</h3>
              <p className="text-slate-500 text-sm leading-relaxed mb-4">
                提供诉讼费速算、劳动仲裁补偿金计算、基础合同条款检查等开箱即用的小工具，自己也能把账算清楚。
              </p>
              <div className="text-emerald-600 text-sm font-semibold flex items-center opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 duration-300">
                使用工具 <ArrowRight className="w-4 h-4 ml-1" />
              </div>
            </Link>

            <Link href="/court" className="group relative bg-white/70 backdrop-blur-xl border border-white p-7 rounded-[2rem] hover:border-purple-200 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_20px_40px_rgb(168,85,247,0.08)] transition-all duration-300 transform hover:-translate-y-1 block">
              <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-2xl flex items-center justify-center mb-5 border border-purple-100 shadow-sm">
                <Gavel className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-800 mb-2">模拟法庭</h3>
              <p className="text-slate-500 text-sm leading-relaxed mb-4">
                扮演原告或被告，在 AI 审判长的引导下进行回合制庭审推演。提前演练抗辩策略，提升法庭应变能力。
              </p>
              <div className="text-purple-600 text-sm font-semibold flex items-center opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 duration-300">
                进入法庭 <ArrowRight className="w-4 h-4 ml-1" />
              </div>
            </Link>
          </div>
        </div>
      </main>

      <footer className="relative z-10 py-5 border-t border-slate-200/50 bg-white/30 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center text-xs text-slate-500 font-medium">
          <div className="flex items-center space-x-2 mb-2 md:mb-0">
            <ScaleIcon size={16} className="text-slate-400" withFire={true} />
            <span>SparkLaw - 开源法律智能体</span>
          </div>
          <div>
            <span>遵循 MIT 开源协议</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
