'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Scale, Gavel, Users, User, Shield, Zap,
  MessageSquare, Plus, Trash2, ArrowLeft, Award,
  Clock, FileSearch, Target, CheckCircle2,
  AlertCircle, Settings2,
  PieChart, Star,
} from 'lucide-react';
import { streamCourtDebate, CourtSSEEvent } from '@/lib/api';

type View = 'setup' | 'live' | 'review';
type UserRole = 'plaintiff' | 'defendant' | 'audience';
interface EvidenceItem {
  id: number;
  category: string;
  content: string;
}
interface AiPersonas { plaintiff: string; defendant: string; judge: string; }
interface ChatMsg {
  role: 'judge' | 'plaintiff' | 'defendant' | 'system' | 'user';
  name: string; content: string; isFollowUp?: boolean;
}
interface ReviewData {
  win_probability: { plaintiff: number; defendant: number };
  summary: string; keyPoints: string[];
}

const JUDGE_STYLES = ['严厉追问型', '中立引导型', '倾向调解型'];
const PLAINTIFF_STYLES = ['激进攻击型', '严密论证型', '胡搅蛮缠型'];
const DEFENDANT_STYLES = ['保守防守型', '釜底抽薪型', '拖延推诿型'];
const CASE_EXAMPLES = [
  { label: '软著侵权', text: '计算机软件著作权侵权纠纷——原告主张被告软件抄袭其核心算法模块，要求赔偿经济损失500万元。' },
  { label: '劳动争议', text: '员工因公司未足额缴纳社保主动离职，申请仲裁要求支付经济补偿金3个月工资45000元，公司认为员工无故旷工拒绝支付。' },
  { label: '合同纠纷', text: '原告向被告预付购房定金20万元，被告因房价上涨拒绝按原价出售，原告要求双倍返还定金40万元并赔偿差价损失。' },
  { label: '租赁纠纷', text: '房东租期未满以装修自住为由要求租客7日内搬离，租客拒绝，房东切断水电逼迫搬离。' },
];

// ── SetupView ──────────────────────────────────────────────────────────────
function SetupView({ caseDesc, setCaseDesc, userRole, setUserRole, evidence, addEv, updEv, delEv, aiPersonas, setAiPersonas, onStart }: {
  caseDesc: string; setCaseDesc: (v: string) => void;
  userRole: UserRole; setUserRole: (v: UserRole) => void;
  evidence: { plaintiff: EvidenceItem[]; defendant: EvidenceItem[] };
  addEv: (s: 'plaintiff'|'defendant') => void;
  updEv: (s: 'plaintiff'|'defendant', id: number, patch: Partial<EvidenceItem>) => void;
  delEv: (s: 'plaintiff'|'defendant', id: number) => void;
  aiPersonas: AiPersonas; setAiPersonas: (v: AiPersonas) => void;
  onStart: () => void;
}) {
  return (
    <div className="flex-1 overflow-y-auto bg-slate-50/50 p-8">
      <div className="max-w-4xl mx-auto space-y-8 pb-12">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-slate-800 mb-3 bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">定制您的模拟法庭</h1>
          <p className="text-slate-500">完善案件事实与证据，设定AI对手风格，开启沉浸式庭审推演。</p>
        </div>
        <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center"><Gavel className="w-5 h-5 mr-2 text-blue-600"/> 0. 案件基本事实</h2>
          <textarea value={caseDesc} onChange={e => setCaseDesc(e.target.value)} rows={4} placeholder="请描述案件事实，包含争议焦点、涉及金额、双方立场..." className="w-full text-sm p-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-1 focus:ring-blue-500 outline-none resize-none transition mb-3"/>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {CASE_EXAMPLES.map((ex, i) => (
              <button key={i} onClick={() => setCaseDesc(ex.text)} className="text-xs border border-slate-200 rounded-lg px-3 py-2 hover:border-blue-300 hover:bg-blue-50 text-slate-600 hover:text-blue-600 transition text-left">
                <span className="font-bold block mb-0.5">{ex.label}</span>
                <span className="line-clamp-1 text-slate-400">{ex.text.slice(0, 18)}...</span>
              </button>
            ))}
          </div>
        </section>
        <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center"><Users className="w-5 h-5 mr-2 text-blue-600"/> 1. 选择您的角色</h2>
          <div className="grid grid-cols-3 gap-4">
            {([{id:'plaintiff',label:'原告/控方',desc:'主动出击，举证并主张权利'},{id:'defendant',label:'被告/辩方',desc:'防守反击，质证并提出抗辩'},{id:'audience',label:'旁听观众席',desc:'上帝视角，观摩AI双方对战'}] as const).map(r => (
              <div key={r.id} onClick={() => setUserRole(r.id)} className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${userRole===r.id?'border-blue-500 bg-blue-50/50 shadow-sm':'border-slate-100 hover:border-blue-200'}`}>
                <div className="font-bold text-slate-800 mb-1">{r.label}</div>
                <div className="text-xs text-slate-500">{r.desc}</div>
                {userRole===r.id && <CheckCircle2 className="w-5 h-5 text-blue-600 mt-2"/>}
              </div>
            ))}
          </div>
        </section>
        <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center"><FileSearch className="w-5 h-5 mr-2 text-blue-600"/> 2. 梳理双方证据</h2>
          <p className="text-xs text-slate-500 mb-4">若未为任一方添加证据，SparkLaw 将自动生成该方可能存在的证据，帮助你快速完成庭审推演。</p>
          <div className="grid grid-cols-2 gap-8">
            {(['plaintiff','defendant'] as const).map(side => (
              <div key={side}>
                <h3 className="text-sm font-bold text-slate-700 mb-3 flex items-center justify-between">
                  <span>{side==='plaintiff'?'原告':'被告'}证据清单</span>
                  <button onClick={() => addEv(side)} className="text-blue-600 hover:text-blue-700 text-xs flex items-center"><Plus className="w-3 h-3 mr-1"/>添加</button>
                </h3>
                <div className="space-y-3">
                  {evidence[side].map(ev => (
                    <div key={ev.id} className="rounded-xl bg-slate-50 border border-slate-200 p-3">
                      <div className="flex justify-end mb-2">
                        <button onClick={() => delEv(side,ev.id)} className="text-slate-300 hover:text-red-400 transition"><Trash2 className="w-4 h-4"/></button>
                      </div>
                      <input
                        type="text"
                        value={ev.category}
                        placeholder="证据类别或名称 (如：聊天记录截图 / 劳动合同)"
                        onChange={e => updEv(side,ev.id,{ category: e.target.value })}
                        className="w-full text-sm p-2.5 bg-white border border-slate-200 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none transition mb-2"
                      />
                      <textarea
                        value={ev.content}
                        rows={3}
                        placeholder="证据的具体内容与证明目的..."
                        onChange={e => updEv(side,ev.id,{ content: e.target.value })}
                        className="w-full text-sm p-2.5 bg-white border border-slate-200 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none resize-y transition"
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
        <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center"><Settings2 className="w-5 h-5 mr-2 text-blue-600"/> 3. 设定 AI 对手/法官风格</h2>
          <div className="grid grid-cols-3 gap-6">
            {userRole!=='plaintiff' && <div><label className="text-sm font-medium text-slate-700 block mb-2">AI 原告风格</label><select value={aiPersonas.plaintiff} onChange={e => setAiPersonas({...aiPersonas,plaintiff:e.target.value})} className="w-full p-2.5 text-sm border border-slate-200 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none">{PLAINTIFF_STYLES.map(s=><option key={s}>{s}</option>)}</select></div>}
            {userRole!=='defendant' && <div><label className="text-sm font-medium text-slate-700 block mb-2">AI 被告风格</label><select value={aiPersonas.defendant} onChange={e => setAiPersonas({...aiPersonas,defendant:e.target.value})} className="w-full p-2.5 text-sm border border-slate-200 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none">{DEFENDANT_STYLES.map(s=><option key={s}>{s}</option>)}</select></div>}
            <div><label className="text-sm font-medium text-slate-700 block mb-2">AI 审判长风格</label><select value={aiPersonas.judge} onChange={e => setAiPersonas({...aiPersonas,judge:e.target.value})} className="w-full p-2.5 text-sm border border-slate-200 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none">{JUDGE_STYLES.map(s=><option key={s}>{s}</option>)}</select></div>
          </div>
        </section>
        <div className="text-center pt-4 pb-10">
          <button onClick={onStart} disabled={!caseDesc.trim()} className={`px-10 py-4 rounded-xl font-bold text-lg shadow-lg transition-all flex items-center mx-auto ${caseDesc.trim()?'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-xl hover:-translate-y-0.5':'bg-slate-200 text-slate-400 cursor-not-allowed'}`}>
            <Gavel className="w-5 h-5 mr-2"/> 正式开庭
          </button>
          <p className="text-xs text-slate-400 mt-3">点击后将进入沉浸式庭审画面，您的进度将自动保存。</p>
        </div>
      </div>
    </div>
  );
}

// ── LiveView placeholder ────────────────────────────────────────────────────
function LiveView(props: {
  caseDesc: string; userRole: UserRole; chatHistory: ChatMsg[];
  chatEndRef: React.RefObject<HTMLDivElement | null>; isStreaming: boolean;
  scores: { statute: number; logic: number; jury: number };
  inputText: string; setInputText: (v: string) => void;
  evidence: { plaintiff: EvidenceItem[]; defendant: EvidenceItem[] };
  aiPersonas: AiPersonas;
  onSpeak: () => void; onBack: () => void; onEndReview: () => void;
}) {
  const { caseDesc, userRole, chatHistory, chatEndRef, isStreaming, scores, inputText, setInputText, evidence, onSpeak, onBack, onEndReview } = props;
  return (
    <div className="flex-1 flex flex-col bg-slate-50 overflow-hidden">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center">
          <button onClick={onBack} className="mr-4 text-slate-400 hover:text-blue-600 transition"><ArrowLeft className="w-5 h-5"/></button>
          <div>
            <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
              {caseDesc.slice(0,28)}{caseDesc.length>28?'...':''}
              <span className={`px-2 py-0.5 text-xs rounded border ${isStreaming?'bg-red-50 text-red-600 border-red-100':'bg-green-50 text-green-600 border-green-100'}`}>{isStreaming?'正在开庭 🔴':'庭审结束 ✅'}</span>
            </h2>
            <div className="text-xs text-slate-500 mt-0.5">您的角色：<strong className="text-blue-600">{userRole==='defendant'?'被告':userRole==='plaintiff'?'原告':'旁听'}</strong>&nbsp;|&nbsp;法庭调查</div>
          </div>
        </div>
        <button onClick={onEndReview} className="text-sm flex items-center text-blue-600 font-medium hover:bg-blue-50 px-4 py-2 rounded-lg transition"><Award className="w-4 h-4 mr-1"/> 结束并复盘</button>
      </header>
      <div className="flex-1 flex overflow-hidden"><aside className="w-60 bg-white border-r border-slate-200 p-4 overflow-y-auto hidden lg:flex flex-col gap-3 shrink-0">
          <h3 className="text-xs font-bold text-slate-600 flex items-center"><FileSearch className="w-4 h-4 mr-1.5 text-blue-500"/>质证看板</h3>
          {evidence.plaintiff.filter(e => e.category || e.content).slice(0,3).map((ev,i) => (
            <div key={i} className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
              <div className="text-xs font-medium text-slate-700 mb-1.5 truncate">原告证{i+1}：{ev.category || '未命名证据'}</div>
              {ev.content && <p className="text-[11px] text-slate-500 mb-1.5 line-clamp-2">{ev.content}</p>}
              <div className="flex flex-wrap gap-1">
                <span className="px-1.5 py-0.5 bg-green-50 text-green-700 rounded text-[10px] border border-green-200">真实性✓</span>
                <span className="px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded text-[10px] border border-amber-200">关联性存疑</span>
              </div>
            </div>
          ))}
          {evidence.plaintiff.filter(e => e.category || e.content).length===0 && <p className="text-xs text-slate-400">暂无原告证据</p>}
          <hr className="border-slate-100"/>
          <h3 className="text-xs font-bold text-slate-600 flex items-center"><Clock className="w-4 h-4 mr-1.5 text-blue-500"/>庭审进展</h3>
          <div className="relative border-l-2 border-slate-100 ml-2 space-y-3 pl-3">
            {chatHistory.filter(m => m.role==='judge').slice(-4).map((m,i) => (
              <div key={i} className="relative">
                <div className="absolute -left-[17px] top-1 w-2.5 h-2.5 bg-amber-400 rounded-full border-2 border-white"/>
                <p className="text-xs text-slate-600 line-clamp-2">{m.content.slice(0,40)}{m.content.length>40?'...':''}</p>
              </div>
            ))}
            {chatHistory.filter(m => m.role==='judge').length===0 && <p className="text-xs text-slate-400">等待庭审...</p>}
          </div>
        </aside>
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-slate-50/50">
            {chatHistory.map((msg,idx) => (
              <div key={idx} className={`flex flex-col ${msg.role==='system'||msg.role==='judge'?'items-center':msg.role==='plaintiff'?'items-start':'items-end'}`}>
                {msg.role==='system' ? (
                  <span className="text-[10px] text-slate-400 px-3 py-1 rounded-full bg-slate-100">{msg.content}</span>
                ) : msg.role==='judge' ? (
                  <div className="max-w-lg flex flex-col items-center">
                    <span className="text-xs text-slate-400 mb-1 flex items-center"><Gavel className="w-3 h-3 mr-1"/>{msg.name}</span>
                    <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${msg.isFollowUp?'bg-amber-50 text-amber-900 border border-amber-200':'bg-white text-slate-700 border border-slate-200'}`}>
                      {msg.isFollowUp && <span className="font-bold text-amber-700 mr-2">[法官追问]</span>}{msg.content}
                    </div>
                  </div>
                ) : (
                  <div className="max-w-lg flex flex-col">
                    <span className={`text-xs text-slate-400 mb-1 ${msg.role==='user'||msg.role==='defendant'?'text-right mr-1':'ml-1'}`}>{msg.name}</span>
                    <div className={`px-4 py-3 rounded-2xl text-sm shadow-sm leading-relaxed ${msg.role==='user'?'bg-blue-600 text-white rounded-tr-sm':'bg-white text-slate-800 border border-slate-200 rounded-tl-sm'}`}>{msg.content}</div>
                  </div>
                )}
              </div>
            ))}
            {isStreaming && <div className="flex justify-center"><span className="text-xs text-amber-600 px-3 py-1.5 bg-amber-50 rounded-full font-medium flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping inline-block mr-1"/>AI庭审进行中...</span></div>}
            {!isStreaming && userRole!=='audience' && chatHistory.length>0 && (
              <div className="flex flex-col items-end pt-2">
                <span className="text-xs text-blue-600 mb-1 font-bold animate-pulse">👉 轮到您发言</span>
                <div className="border border-blue-200 bg-blue-50/50 w-full max-w-lg h-10 rounded-2xl border-dashed flex items-center justify-center text-blue-400 text-xs">请在下方输入框发言...</div>
              </div>
            )}
            <div ref={chatEndRef}/>
          </div>
          {userRole!=='audience' && (
            <div className="p-4 bg-white border-t border-slate-200 shrink-0">
              <div className="mb-2 flex space-x-2">
                <button className="text-xs bg-blue-50 text-blue-600 px-3 py-1.5 rounded-full border border-blue-100 flex items-center hover:bg-blue-100 transition"><Zap className="w-3 h-3 mr-1"/> AI优化表达</button>
                <button className="text-xs bg-slate-50 text-slate-600 px-3 py-1.5 rounded-full border border-slate-200 flex items-center hover:bg-slate-100 transition"><Scale className="w-3 h-3 mr-1"/> 找法条</button>
                <button className="text-xs bg-slate-50 text-slate-600 px-3 py-1.5 rounded-full border border-slate-200 flex items-center hover:bg-slate-100 transition"><Shield className="w-3 h-3 mr-1"/> 破绽分析</button>
              </div>
              <div className="flex items-end space-x-3">
                <div className="flex-1 bg-white border border-slate-300 rounded-xl focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-all shadow-sm overflow-hidden">
                  <textarea rows={3} className="w-full bg-transparent p-3 text-sm outline-none resize-none" placeholder="在此输入您的发言，Enter发送，Shift+Enter换行..." value={inputText} onChange={e => setInputText(e.target.value)} onKeyDown={e => {if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();onSpeak();}}}/>
                </div>
                <button onClick={onSpeak} disabled={!inputText.trim()} className={`h-[76px] px-6 rounded-xl font-medium transition flex items-center shadow-md ${inputText.trim()?'bg-blue-600 text-white hover:bg-blue-700':'bg-slate-100 text-slate-300 cursor-not-allowed'}`}><MessageSquare className="w-5 h-5 mr-2"/>发言</button>
              </div>
            </div>
          )}
        </main>
        <aside className="w-64 bg-white border-l border-slate-200 p-4 overflow-y-auto hidden xl:flex flex-col gap-5 shrink-0">
          <h3 className="text-xs font-bold text-slate-600 flex items-center"><Target className="w-4 h-4 mr-1.5 text-blue-500"/>AI表现评估</h3>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 space-y-3">
            {(['法条适配度','逻辑严密性'] as const).map((label,i) => {
              const val = i===0?scores.statute:scores.logic;
              return (<div key={label}><div className="flex justify-between text-xs mb-1"><span className="text-slate-600">{label}</span><span className="text-blue-600 font-bold">{val>0?`${val}%`:'待评估'}</span></div><div className="h-1.5 bg-slate-200 rounded-full overflow-hidden"><div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{width:`${val}%`}}/></div></div>);
            })}
          </div>
          <h3 className="text-xs font-bold text-slate-600 flex items-center"><Users className="w-4 h-4 mr-1.5 text-blue-500"/>陪审团预测</h3>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 text-center">
            <div className={`text-3xl font-bold mb-1 ${scores.jury>0?'text-blue-600':'text-slate-300'}`}>{scores.jury>0?`${scores.jury}分`:'--'}</div>
            <div className="text-[10px] text-slate-500">{scores.jury>0?'综合表现得分':'等待首轮发言...'}</div>
          </div>
          <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-3">
            <h4 className="text-xs font-bold text-blue-800 mb-2 flex items-center"><Zap className="w-3 h-3 mr-1 text-orange-500"/>战术建议</h4>
            <p className="text-xs text-blue-700 leading-relaxed">{userRole==='defendant'?'建议核查原告证据关联性，从程序瑕疵角度提出质疑，准备替代性解释。':'建议强调证据链完整性，引用具体法条支撑主张。'}</p>
          </div>
        </aside></div>
    </div>
  );
}

// ── ReviewView placeholder ───────────────────────────────────────────────────
function ReviewView({ reviewData, onReset }: { reviewData: ReviewData | null; onReset: () => void }) {
  const rd = reviewData;
  return (
    <div className="flex-1 bg-slate-50 overflow-y-auto p-8">
      <div className="max-w-3xl mx-auto space-y-8">
        <div className="text-center">
          <PieChart className="w-14 h-14 text-blue-600 mx-auto mb-4"/>
          <h1 className="text-2xl font-bold text-slate-800 mb-2">庭审复盘报告</h1>
          <p className="text-slate-500 text-sm">AI 综合双方陈述与证据，生成以下复盘分析</p>
        </div>
        {rd && (
          <>
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h2 className="text-base font-bold text-slate-800 mb-4 flex items-center"><Award className="w-5 h-5 mr-2 text-blue-600"/>胜诉概率预测</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 rounded-xl p-5 text-center border border-blue-100">
                  <div className="text-xs font-bold text-blue-500 uppercase tracking-widest mb-2">原告胜诉率</div>
                  <div className="text-4xl font-black text-blue-600">{rd.win_probability.plaintiff}%</div>
                </div>
                <div className="bg-red-50 rounded-xl p-5 text-center border border-red-100">
                  <div className="text-xs font-bold text-red-500 uppercase tracking-widest mb-2">被告胜诉率</div>
                  <div className="text-4xl font-black text-red-600">{rd.win_probability.defendant}%</div>
                </div>
              </div>
            </section>
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h2 className="text-base font-bold text-slate-800 mb-3 flex items-center"><Gavel className="w-5 h-5 mr-2 text-blue-600"/>裁判综述</h2>
              <p className="text-sm text-slate-600 leading-relaxed">{rd.summary}</p>
            </section>
            <section className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h2 className="text-base font-bold text-slate-800 mb-4 flex items-center"><Star className="w-5 h-5 mr-2 text-amber-500"/>关键点分析</h2>
              <div className="space-y-3">
                {rd.keyPoints.map((pt,i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <CheckCircle2 className="w-4 h-4 text-blue-500 mt-0.5 shrink-0"/>
                    <span className="text-sm text-slate-700">{pt}</span>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
        {!rd && <p className="text-center text-slate-400 text-sm">复盘数据生成中，请稍候...</p>}
        <div className="text-center pt-4 pb-10">
          <button onClick={onReset} className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-md transition flex items-center mx-auto">
            <Gavel className="w-4 h-4 mr-2"/> 重新开庭
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CourtPage() {
  const [view, setView] = useState<View>('setup');
  const [userRole, setUserRole] = useState<UserRole>('defendant');
  const [caseDesc, setCaseDesc] = useState('');
  const [evidence, setEvidence] = useState<{ plaintiff: EvidenceItem[]; defendant: EvidenceItem[] }>({
    plaintiff: [{ id: 1, category: '', content: '' }],
    defendant: [{ id: 2, category: '', content: '' }],
  });
  const [aiPersonas, setAiPersonas] = useState<AiPersonas>({ plaintiff: '激进攻击型', defendant: '保守防守型', judge: '严厉追问型' });
  const [chatHistory, setChatHistory] = useState<ChatMsg[]>([]);
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [reviewData, setReviewData] = useState<ReviewData | null>(null);
  const [error, setError] = useState('');
  const [scores, setScores] = useState({ statute: 0, logic: 0, jury: 0 });
  const abortRef = useRef<AbortController | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatHistory]);

  const addEv = (s: 'plaintiff' | 'defendant') => setEvidence(p => ({ ...p, [s]: [...p[s], { id: Date.now(), category: '', content: '' }] }));
  const updEv = (s: 'plaintiff' | 'defendant', id: number, patch: Partial<EvidenceItem>) => setEvidence(p => ({ ...p, [s]: p[s].map(e => e.id === id ? { ...e, ...patch } : e) }));
  const delEv = (s: 'plaintiff' | 'defendant', id: number) => setEvidence(p => ({ ...p, [s]: p[s].filter(e => e.id !== id) }));

  const handleStart = useCallback(async () => {
    setView('live'); setIsStreaming(true); setError(''); setChatHistory([]);
    setScores({ statute: 0, logic: 0, jury: 0 });
    abortRef.current = new AbortController();
    const pEv = evidence.plaintiff
      .filter(e => e.category.trim() || e.content.trim())
      .map(e => `${e.category || '未命名证据'}：${e.content || '（无具体说明）'}`)
      .join('；');
    const dEv = evidence.defendant
      .filter(e => e.category.trim() || e.content.trim())
      .map(e => `${e.category || '未命名证据'}：${e.content || '（无具体说明）'}`)
      .join('；');
    const humanEvidence = [
      ...evidence.plaintiff
        .filter(e => e.category.trim() || e.content.trim())
        .map((e, idx) => ({
          party: 'plaintiff' as const,
          name: e.category.trim() || `原告证据${idx + 1}`,
          desc: e.content.trim() || '（无具体说明）',
        })),
      ...evidence.defendant
        .filter(e => e.category.trim() || e.content.trim())
        .map((e, idx) => ({
          party: 'defendant' as const,
          name: e.category.trim() || `被告证据${idx + 1}`,
          desc: e.content.trim() || '（无具体说明）',
        })),
    ];
    const full = `${caseDesc}\n[原告证据]${pEv || '无'}\n[被告证据]${dEv || '无'}\n[原告风格]${aiPersonas.plaintiff}\n[被告风格]${aiPersonas.defendant}\n[法官风格]${aiPersonas.judge}`;
    try {
      await streamCourtDebate(
        { case_description: full, strategy: 'aggressive', plaintiff_name: `AI原告(${aiPersonas.plaintiff})`, defendant_name: `AI被告(${aiPersonas.defendant})`, human_evidence: humanEvidence },
        (ev: CourtSSEEvent) => {
          if (ev.type === 'error') { setError(ev.message || '庭审出错'); setIsStreaming(false); return; }
          if (ev.type === 'verdict') {
            setReviewData({ win_probability: ev.win_probability || { plaintiff: 50, defendant: 50 }, summary: ev.content || '庭审结束', keyPoints: ['证据链完整性已分析', '法条适配度已评估', '逻辑一致性已核查'] });
            setIsStreaming(false);
          } else if (['opening', 'plaintiff', 'defendant', 'judge', 'log'].includes(ev.type)) {
            const roleMap: Record<string, ChatMsg['role']> = { opening: 'system', plaintiff: 'plaintiff', defendant: 'defendant', judge: 'judge', log: 'system' };
            const nameMap: Record<string, string> = { opening: '庭审开始', plaintiff: `AI 原告代理人 (${aiPersonas.plaintiff})`, defendant: `AI 被告代理人 (${aiPersonas.defendant})`, judge: `AI 审判长 (${aiPersonas.judge})`, log: '系统' };
            setChatHistory(p => [...p, { role: roleMap[ev.type] ?? 'system', name: nameMap[ev.type] ?? '系统', content: ev.content || ev.message || '', isFollowUp: ev.type === 'judge' }]);
            setScores(p => ({ statute: Math.min(95, p.statute + Math.floor(Math.random() * 10) + 3), logic: Math.min(95, p.logic + Math.floor(Math.random() * 8) + 2), jury: Math.min(95, p.jury + Math.floor(Math.random() * 6) + 2) }));
          }
        },
        abortRef.current.signal,
      );
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setError(e instanceof Error ? e.message : '庭审失败');
      setIsStreaming(false);
    }
  }, [caseDesc, evidence, aiPersonas]);

  const handleSpeak = () => {
    if (!inputText.trim()) return;
    const label = userRole === 'plaintiff' ? '原告（您）' : userRole === 'defendant' ? '被告（您）' : '旁听（您）';
    setChatHistory(p => [...p, { role: 'user', name: label, content: inputText.trim() }]);
    setInputText('');
  };

  const handleEndReview = () => {
    abortRef.current?.abort(); setIsStreaming(false);
    if (!reviewData) setReviewData({ win_probability: { plaintiff: 50, defendant: 50 }, summary: '庭审提前结束。', keyPoints: ['请重新开庭获取完整复盘'] });
    setView('review');
  };

  const handleReset = () => {
    abortRef.current?.abort();
    setView('setup'); setChatHistory([]); setIsStreaming(false);
    setReviewData(null); setError(''); setScores({ statute: 0, logic: 0, jury: 0 }); setCaseDesc('');
  };

  return (
    <div className="flex flex-1 min-w-0 flex-col bg-slate-50 font-sans text-slate-900 overflow-y-auto">
      {error && (
        <div className="fixed top-4 right-4 z-50 flex items-center gap-3 bg-white border border-red-100 text-red-600 rounded-2xl px-5 py-3 text-sm shadow-lg">
          <AlertCircle size={15}/> {error}
          <button onClick={() => setError('')} className="ml-2 opacity-60 hover:opacity-100">✕</button>
        </div>
      )}
      {view === 'setup' && <SetupView
        caseDesc={caseDesc} setCaseDesc={setCaseDesc}
        userRole={userRole} setUserRole={setUserRole}
        evidence={evidence} addEv={addEv} updEv={updEv} delEv={delEv}
        aiPersonas={aiPersonas} setAiPersonas={setAiPersonas}
        onStart={handleStart}
      />}
      {view === 'live' && <LiveView
        caseDesc={caseDesc} userRole={userRole}
        chatHistory={chatHistory} chatEndRef={chatEndRef}
        isStreaming={isStreaming} scores={scores}
        inputText={inputText} setInputText={setInputText}
        evidence={evidence} aiPersonas={aiPersonas}
        onSpeak={handleSpeak} onBack={() => setView('setup')} onEndReview={handleEndReview}
      />}
      {view === 'review' && <ReviewView reviewData={reviewData} onReset={handleReset}/>}
    </div>
  );
}
