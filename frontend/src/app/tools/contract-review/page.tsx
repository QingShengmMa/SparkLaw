'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, Upload, FileText,
  Zap, Download, Target, Activity,
  RotateCcw, AlertCircle,
  Eye, Building2, Briefcase, ShoppingCart, X, Loader2,
} from 'lucide-react';
import {
  uploadDocument, streamContractReview, getTemplate,
  ContractRiskItem,
} from '@/lib/api';

type Status = 'idle' | 'uploading' | 'scanning' | 'results';

type RiskLevel = 'high' | 'medium' | 'low';

function getRiskStyle(level: string) {
  if (level === 'high' || level === 'High Risk')
    return { bg: 'bg-red-50/60', textCls: 'text-red-700', badge: 'bg-red-100 text-red-700', label: 'Critical', border: '#EF4444' };
  if (level === 'medium' || level === 'Medium Risk')
    return { bg: 'bg-amber-50/60', textCls: 'text-amber-700', badge: 'bg-amber-100 text-amber-700', label: 'Warning', border: '#F59E0B' };
  return { bg: 'bg-green-50/40', textCls: 'text-green-700', badge: 'bg-green-100 text-green-700', label: 'Low', border: '#10B981' };
}

interface ReviewResult {
  score: number;
  riskCount: number;
  overall_summary: string;
  risks: ContractRiskItem[];
}

function ContractExampleCard({
  icon, title, desc, onPreview, onReview,
}: { icon: React.ReactNode; title: string; desc: string; onPreview: () => void; onReview: () => void; }) {
  return (
    <div className="group bg-white dark:bg-[#151822] border border-gray-100/60 dark:border-white/10 rounded-[20px] p-4 transition-all duration-300 hover:shadow-md hover:border-blue-200 dark:hover:bg-white/10 flex flex-col h-full">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-xl bg-[#F0F4F9] dark:bg-white/5 text-[#444746] dark:text-gray-400 flex items-center justify-center group-hover:bg-blue-50 dark:group-hover:bg-blue-900/30 group-hover:text-blue-600 transition-colors duration-300">{icon}</div>
        <h3 className="text-[14px] font-bold text-[#1F1F1F] dark:text-gray-100 group-hover:text-blue-600 transition-colors duration-300">{title}</h3>
      </div>
      <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed mb-4 flex-1 line-clamp-3">{desc}</p>
      <div className="flex gap-2">
        <button
          onClick={e => { e.stopPropagation(); onPreview(); }}
          className="flex-1 py-1.5 bg-gray-50 dark:bg-white/5 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-white/20 active:scale-95 rounded-[10px] text-[11px] font-bold transition-all duration-200 flex items-center justify-center gap-1.5"
        ><Eye size={12}/> 预览</button>
        <button
          onClick={e => { e.stopPropagation(); onReview(); }}
          className="flex-1 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300 hover:bg-blue-600 hover:text-white dark:hover:bg-blue-600 dark:hover:text-white active:scale-95 rounded-[10px] text-[11px] font-bold transition-all duration-200 flex items-center justify-center gap-1.5"
        ><Zap size={12}/> 审查</button>
      </div>
    </div>
  );
}
export default function ContractReviewPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const consoleRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<Status>('idle');
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState('');
  const [error, setError] = useState('');
  const [taskId, setTaskId] = useState('');
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [selectedRisk, setSelectedRisk] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  // Preview modal state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTitle, setPreviewTitle] = useState('');
  const [previewContent, setPreviewContent] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    if (consoleRef.current) consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }, [logs]);

  const startSSEReview = useCallback(async (contractId: string, templateId?: string) => {
    setStatus('scanning');
    setProgress(0);
    setLogs(['正在连接审查引擎...']);
    setError('');

    abortRef.current = new AbortController();
    let gotResult = false;

    // Safety: force-reset if still scanning after 130s
    const safetyTimer = setTimeout(() => {
      if (!gotResult) {
        abortRef.current?.abort();
        setError('审查超时（130秒），请检查网络后重试');
        setStatus('idle');
      }
    }, 130_000);

    try {
      await streamContractReview(
        { contractId: templateId ? undefined : contractId, templateId },
        (event) => {
          if (event.type === 'log') {
            setProgress(event.progress);
            setLogs(prev => [...prev, event.message].slice(-20));
          } else if (event.type === 'result') {
            gotResult = true;
            clearTimeout(safetyTimer);
            setProgress(100);
            setLogs(prev => [...prev, `✅ 审查完成，发现 ${event.riskCount} 个风险点`]);
            setResult({
              score: event.score,
              riskCount: event.riskCount,
              overall_summary: event.overall_summary,
              risks: event.risks,
            });
            setStatus('results');
          } else if (event.type === 'error') {
            gotResult = true;
            clearTimeout(safetyTimer);
            setError(event.message);
            setStatus('idle');
          }
        },
        abortRef.current.signal
      );
      // Stream ended without result event (connection drop)
      if (!gotResult) {
        clearTimeout(safetyTimer);
        setError('连接中断，未收到分析结果，请重试');
        setStatus('idle');
      }
    } catch (e) {
      clearTimeout(safetyTimer);
      if ((e as Error).name !== 'AbortError') {
        setError(e instanceof Error ? e.message : '审查失败，请重试');
        setStatus('idle');
      }
    }
  }, []);

  const handleTemplatePreview = useCallback(async (templateId: string, title: string) => {
    setPreviewTitle(title);
    setPreviewContent('');
    setPreviewOpen(true);
    setPreviewLoading(true);
    try {
      const r = await getTemplate(templateId);
      setPreviewContent(r.content);
    } catch (e) {
      setPreviewContent('加载失败：' + (e instanceof Error ? e.message : '未知错误'));
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  const handleTemplateReview = useCallback((templateId: string, title: string) => {
    setFileName(title);
    setError('');
    setStatus('scanning');
    setProgress(0);
    setLogs([`正在加载示例合同：${title}...`]);
    startSSEReview(templateId, templateId);
  }, [startSSEReview]);

  const handleFile = useCallback(async (file: File) => {
    const valid = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/jpeg', 'image/png'];
    if (!valid.includes(file.type)) { setError('仅支持 PDF、Word 和图片文件'); return; }
    setFileName(file.name);
    setError('');
    setStatus('uploading');
    setProgress(0);
    setLogs(['文件上传中...']);
    try {
      const r = await uploadDocument(file);
      setLogs(prev => [...prev, `文档解析完成，共 ${r.chunk_count} 个段落`]);
      await startSSEReview(r.contract_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : '上传失败');
      setStatus('idle');
    }
  }, [startSSEReview]);

  const handleDrop = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); const f=e.dataTransfer.files[0]; if(f) handleFile(f); };
  const handleReset = () => {
    abortRef.current?.abort();
    setStatus('idle'); setProgress(0); setLogs([]); setFileName(''); setError(''); setTaskId(''); setResult(null); setSelectedRisk(0);
  };
  const isScanning = status==='uploading' || status==='scanning';
  const highCount = result?.risks.filter(r => r.risk_level==='high' || r.severity==='High Risk').length ?? 0;
  const midCount  = result?.risks.filter(r => r.risk_level==='medium' || r.severity==='Medium Risk').length ?? 0;
  const score = result?.score ?? 0;
  const scoreColor = score>=75?'#34A853':score>=50?'#F59E0B':'#EF4444';
  const circ = 2*Math.PI*36;
  const activeRisk = result?.risks[selectedRisk];
  const activeStyle = activeRisk ? getRiskStyle(activeRisk.risk_level || activeRisk.severity) : null;
  return (
    <div className="relative flex flex-col h-full bg-[#FDFDFF] dark:bg-[#0B0D14] text-[#1F1F1F] dark:text-gray-100 font-sans overflow-hidden transition-colors duration-300 ease-in-out">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[280px] bg-blue-50/40 rounded-full blur-[100px] pointer-events-none" />
      {error && (
        <div className="fixed top-4 right-4 z-50 flex items-center gap-3 bg-white dark:bg-[#151822] border border-red-100 dark:border-white/10 text-red-600 dark:text-red-400 rounded-[16px] px-5 py-3 text-[13px] shadow-lg transition-colors duration-300 ease-in-out">
          <AlertCircle size={15}/> {error}
          <button onClick={() => setError('')} className="ml-2 opacity-60 hover:opacity-100">✕</button>
        </div>
      )}
      <main className="relative z-10 flex-1 flex flex-col overflow-y-auto transition-colors duration-300 ease-in-out">
        <div className="flex-1 flex flex-col w-full px-6 pt-4 pb-2 lg:px-8">
          {/* 【铁律 1】Header */}
          <header className="mb-5 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-4">
              <button onClick={() => router.push('/tools')} className="p-2 rounded-full hover:bg-[#F0F4F9] dark:hover:bg-white/10 text-[#444746] dark:text-gray-400 transition-colors duration-300 ease-in-out active:scale-95"><ArrowLeft size={18}/></button>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-[#1F1F1F] dark:text-gray-100 flex items-center gap-2 transition-colors duration-300 ease-in-out">合同审查 📄</h1>
                {fileName && <span className="text-[13px] text-gray-400 dark:text-white/50 truncate max-w-[180px] transition-colors duration-300 ease-in-out">· {fileName}</span>}
              </div>
            </div>
            {status==='results' && (
              <div className="flex items-center gap-3">
                <button onClick={handleReset} className="flex items-center gap-1.5 px-4 py-1.5 rounded-full border border-gray-200 dark:border-white/10 bg-white dark:bg-[#151822] hover:bg-gray-50 dark:hover:bg-white/10 text-[13px] font-medium text-gray-600 dark:text-gray-300 transition-colors duration-300 ease-in-out"><RotateCcw size={13}/> 重新上传</button>
                <button className="px-5 py-2 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-lg shadow-blue-100 dark:shadow-none transition-colors duration-300 ease-in-out flex items-center gap-2"><Download size={14}/> 导出修正版</button>
              </div>
            )}
          </header>
          {/* Idle */}
          {status==='idle' && (
            <div className="flex flex-col items-center w-full max-w-5xl mx-auto mt-14 mb-auto">
              <div className="text-center mb-5">
                <h2 className="!text-[36px] md:!text-[40px] font-black tracking-tight leading-tight mb-2">
                  <span className="text-[#111827] dark:text-white drop-shadow-[0_1px_0_rgba(255,255,255,0.35)]">上传文档，</span>
                  <span className="ml-1 bg-gradient-to-r from-blue-600 via-violet-600 to-cyan-500 bg-clip-text text-transparent">启动 AI 审查</span>
                </h2>
                <p className="text-[13px] text-[#6B7280] dark:text-gray-400 transition-colors duration-300 ease-in-out">支持 PDF、Word 及图片。AI 自动识别高危条款并给出修改建议。</p>
              </div>
              <input ref={inputRef} type="file" className="hidden" accept=".pdf,.docx,.doc,.jpg,.jpeg,.png" onChange={e => { const f=e.target.files?.[0]; if(f) handleFile(f); }}/>
              <div onDragOver={e => { e.preventDefault(); setIsDragging(true); }} onDragLeave={() => setIsDragging(false)} onDrop={handleDrop} onClick={() => inputRef.current?.click()}
                className={`relative group cursor-pointer w-full mb-6 rounded-[24px] transition-colors duration-300 ease-in-out ${isDragging?'bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-400':'bg-white dark:bg-[#151822] border border-gray-100 dark:border-white/10 hover:border-blue-200 dark:hover:bg-white/10'}`}>
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-500/15 to-indigo-500/15 rounded-[28px] blur-lg opacity-0 group-hover:opacity-100 transition duration-500"/>
                <div className="relative py-12 flex flex-col items-center text-center">
                  <div className="w-12 h-12 rounded-2xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-300 mb-4 group-hover:scale-110 transition-colors duration-300 ease-in-out"><Upload size={22} strokeWidth={2.2}/></div>
                  <p className="text-[18px] font-bold text-[#1F1F1F] dark:text-gray-100 mb-1 transition-colors duration-300 ease-in-out">拖放文件或点击上传</p>
                  <p className="text-[12px] text-gray-400 dark:text-white/50 transition-colors duration-300 ease-in-out">PDF · Word · JPG / PNG，最大 50MB</p>
                </div>
              </div>
              <h3 className="mt-2 !text-[16px] font-medium text-gray-400 dark:text-white/50 uppercase tracking-wider mb-5 text-center transition-colors duration-300 ease-in-out flex items-center justify-center gap-2">
                <span className="inline-block animate-pulse">✨</span>
                <span>常见合同示例</span>
                <span className="inline-block animate-pulse" style={{ animationDelay: '0.6s' }}>📄</span>
              </h3>
              <div className="grid grid-cols-3 gap-4 w-full">
                <ContractExampleCard icon={<Building2 size={16}/>} title="房屋租赁合同" desc="包含常见押金陷阱、违约金畸高、单方解除权等高危条款。" onPreview={() => handleTemplatePreview('housing_lease', '房屋租赁合同')} onReview={() => handleTemplateReview('housing_lease', '房屋租赁合同')}/>
                <ContractExampleCard icon={<Briefcase size={16}/>} title="标准劳动合同" desc="包含不合理的竞业限制、薪酬结构风险及调岗调薪条款。" onPreview={() => handleTemplatePreview('labor_contract', '标准劳动合同')} onReview={() => handleTemplateReview('labor_contract', '标准劳动合同')}/>
                <ContractExampleCard icon={<ShoppingCart size={16}/>} title="采购购销协议" desc="包含交付验收争议、管辖权约定不利及不可抗力陷阱。" onPreview={() => handleTemplatePreview('purchase_agreement', '采购购销协议')} onReview={() => handleTemplateReview('purchase_agreement', '采购购销协议')}/>
              </div>
            </div>
          )}
          {/* Scanning */}
          {isScanning && (
            <div className="flex-1 flex flex-col items-center justify-center py-4">
              <div className="w-full max-w-[800px] grid grid-cols-2 gap-10 items-center">
                <div className="relative aspect-[3/4] bg-white dark:bg-gray-200 dark:text-gray-900 rounded-[28px] border border-gray-100/60 dark:border-white/10 overflow-hidden p-8 transition-colors duration-300 ease-in-out">
                  <div className="space-y-4 opacity-10">{Array.from({length:12}).map((_,i)=>(<div key={i} className={`h-2 rounded-full bg-gray-300 ${i%3===0?'w-1/2':i%3===1?'w-full':'w-3/4'}`}/>))}</div>
                  <div className="absolute left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-blue-500 to-transparent z-20" style={{top:`${Math.min(progress,98)}%`,transition:'top 0.15s linear',boxShadow:'0 0 12px rgba(59,130,246,0.6)'}}/>
                  <div className="absolute inset-0 bg-blue-500/5" style={{clipPath:`inset(0 0 ${100-Math.min(progress,98)}% 0)`}}/>
                </div>
                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="text-[16px] font-bold flex items-center gap-2 text-gray-800"><Activity className="text-blue-600 animate-pulse" size={16}/>{status==='uploading'?'上传中...':'AI 引擎分析中...'}</h3>
                      <span className="font-mono text-blue-600 font-bold">{Math.floor(progress)}%</span>
                    </div>
                    <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden"><div className="h-full bg-blue-600 rounded-full transition-all duration-500" style={{width:`${progress}%`}}/></div>
                  </div>
                  <div ref={consoleRef} className="bg-[#1A1C1E] dark:bg-[#151822] rounded-[20px] p-5 h-52 overflow-y-auto border border-transparent dark:border-white/10 transition-colors duration-300 ease-in-out">
                    <div className="text-[9px] font-black uppercase tracking-widest text-gray-600 mb-3 pb-2 border-b border-white/5">Audit Engine Logs</div>
                    <div className="space-y-2">
                      {logs.map((log,i)=>(<div key={i} className="flex gap-3 text-[11px]"><span className="text-blue-400/50 tabular-nums shrink-0">[{String(i).padStart(2,'0')}]</span><span className="text-gray-400 leading-relaxed">{log}</span></div>))}
                      <div className="w-1 h-3 bg-blue-500 animate-pulse mt-1"/>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          {/* Results */}
          {status==='results' && result && (
            <div className="flex gap-5 flex-1 min-h-0 py-2">
              <div className="flex gap-4 flex-1 min-w-0 overflow-hidden">
                <div className="w-[200px] shrink-0 flex flex-col gap-2 overflow-y-auto">
                  <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1 mb-1">风险条款 ({result.risks.length})</div>
                  {result.risks.map((rsk,i) => {
                    const st = getRiskStyle(rsk.risk_level || rsk.severity);
                    return (
                      <button key={i} onClick={() => setSelectedRisk(i)}
                        className={`w-full text-left px-4 py-3 rounded-[16px] border-l-[3px] transition-colors duration-300 ease-in-out ${selectedRisk===i?`${st.bg} ring-1 ring-blue-200`:'bg-white dark:bg-[#151822] hover:bg-gray-50 dark:hover:bg-white/10 border border-transparent dark:border-white/10'}`}
                        style={{borderLeftColor:st.border}}>
                        <span className={`text-[9px] font-black uppercase tracking-wider ${st.textCls}`}>{st.label}</span>
                        <p className="text-[12px] text-gray-700 dark:text-gray-300 mt-0.5 leading-snug line-clamp-2 transition-colors duration-300 ease-in-out">{(rsk.clause_text||rsk.originalText).slice(0,60)}...</p>
                      </button>
                    );
                  })}
                </div>
                <div className="flex-1 bg-white dark:bg-[#151822] rounded-[24px] border border-gray-100/60 dark:border-white/10 flex flex-col overflow-hidden transition-colors duration-300 ease-in-out">
                  <div className="px-6 py-3 border-b border-gray-50 dark:border-white/10 flex items-center justify-between shrink-0 transition-colors duration-300 ease-in-out">
                    <div className="flex items-center gap-2"><FileText size={14} className="text-gray-400 dark:text-gray-400"/><span className="text-[12px] font-bold text-gray-700 dark:text-gray-200 transition-colors duration-300 ease-in-out">合同原文（风险标注）</span></div>
                    <div className="flex gap-2">
                      <span className="px-2 py-0.5 rounded-full bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-300 text-[10px] font-bold transition-colors duration-300 ease-in-out">{highCount} 高风险</span>
                      <span className="px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-300 text-[10px] font-bold transition-colors duration-300 ease-in-out">{midCount} 中风险</span>
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto p-6 text-[13px] leading-[1.9] space-y-4">
                    <p className="text-gray-500 dark:text-gray-400 text-[12px] mb-4 transition-colors duration-300 ease-in-out">{result.overall_summary}</p>
                    {result.risks.map((rsk,i) => {
                      const st = getRiskStyle(rsk.risk_level || rsk.severity);
                      return (
                        <div key={i} onClick={() => setSelectedRisk(i)}
                          className={`rounded-[12px] px-4 py-3 cursor-pointer border-l-[3px] transition-colors duration-300 ease-in-out ${st.bg} ${selectedRisk===i?'ring-1 ring-blue-300':''}`}
                          style={{borderLeftColor:st.border}}>
                          <span className={`text-[10px] font-bold uppercase tracking-wider ${st.textCls}`}>{st.label}</span>
                          <p className="mt-1 text-[13px] text-gray-800 dark:text-gray-200 transition-colors duration-300 ease-in-out">{rsk.clause_text||rsk.originalText}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
              <div className="w-[300px] shrink-0 flex flex-col gap-4">
                <div className="bg-[#1A1C1E] dark:bg-[#151822] rounded-[24px] p-6 text-white border border-transparent dark:border-white/10 transition-colors duration-300 ease-in-out">
                  <div className="flex justify-between items-start mb-4"><span className="text-[9px] font-black uppercase tracking-widest text-gray-500">Compliance Score</span><Target className="text-blue-400" size={15}/></div>
                  <div className="flex items-center gap-6">
                    <div className="relative w-[80px] h-[80px] shrink-0 flex items-center justify-center">
                      <svg className="w-full h-full -rotate-90" viewBox="0 0 80 80">
                        <circle cx="40" cy="40" r="36" stroke="#ffffff" strokeOpacity="0.08" strokeWidth="7" fill="transparent"/>
                        <circle cx="40" cy="40" r="36" strokeWidth="7" fill="transparent" stroke={scoreColor} strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ-(circ*score)/100} style={{transition:'stroke-dashoffset 1s ease'}}/>
                      </svg>
                      <span className="absolute text-[24px] font-bold tracking-tighter" style={{color:scoreColor}}>{score}</span>
                    </div>
                    <div><p className="text-[14px] font-bold mb-0.5">{score>=75?'风险较低':score>=50?'需要关注':'高风险合同'}</p><p className="text-[10px] text-gray-500">{highCount} 高 · {midCount} 中 · {result.risks.length-highCount-midCount} 低</p></div>
                  </div>
                </div>
                {activeRisk && activeStyle && (
                  <div className="flex-1 bg-white dark:bg-[#151822] rounded-[24px] border border-gray-100/60 dark:border-white/10 flex flex-col overflow-hidden transition-colors duration-300 ease-in-out">
                    <div className="px-5 py-3 border-b border-gray-50 dark:border-white/10 flex items-center justify-between shrink-0 transition-colors duration-300 ease-in-out"><h3 className="text-[11px] font-bold text-gray-700 dark:text-gray-200 uppercase tracking-widest">审计详情</h3><Zap size={13} className="text-blue-500"/></div>
                    <div className="flex-1 overflow-y-auto p-5 space-y-3">
                      <div className="p-4 rounded-[16px] bg-[#F0F4F9] dark:bg-white/5 space-y-3 border border-transparent dark:border-white/10 transition-colors duration-300 ease-in-out">
                        <span className={`px-2 py-0.5 rounded-[6px] text-[9px] font-black uppercase tracking-wider ${activeStyle.badge}`}>{activeStyle.label}</span>
                        <div><p className="text-[10px] font-bold text-gray-400 dark:text-white/50 uppercase tracking-wider mb-1 transition-colors duration-300 ease-in-out">风险分析</p><p className="text-[12px] text-gray-600 dark:text-gray-300 leading-relaxed transition-colors duration-300 ease-in-out">{activeRisk.risk_analysis||activeRisk.analysis}</p></div>
                        <div className="bg-white dark:bg-[#151822] rounded-[12px] p-3 border border-gray-100 dark:border-white/10 transition-colors duration-300 ease-in-out"><p className="text-[10px] font-bold text-blue-500 uppercase tracking-wider mb-1">修改建议</p><p className="text-[12px] text-gray-700 dark:text-gray-200 italic leading-relaxed transition-colors duration-300 ease-in-out">{activeRisk.revision_suggestion||activeRisk.suggestion}</p></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 【铁律 2】Footer */}
          <footer className="mt-auto pt-4 pb-2 text-center shrink-0 transition-colors duration-300 ease-in-out">
            <p className="text-xs text-gray-400 dark:text-white/50 font-normal tracking-wide">AI 生成内容仅供参考，不构成正式法律意见</p>
          </footer>
        </div>
      </main>
      {/* Preview Modal */}
      {previewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setPreviewOpen(false)}>
          <div className="absolute inset-0 bg-black/40 backdrop-blur-[3px]"/>
          <div className="relative w-full max-w-[700px] max-h-[85vh] flex flex-col bg-white dark:bg-[#151822] rounded-[24px] shadow-2xl border border-gray-100 dark:border-white/10" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-white/10 shrink-0">
              <div className="flex items-center gap-3">
                <FileText size={16} className="text-blue-500"/>
                <h2 className="text-[15px] font-bold text-gray-900 dark:text-gray-100">{previewTitle}</h2>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 font-bold border border-amber-100 dark:border-amber-800/30">示例合同</span>
              </div>
              <button onClick={() => setPreviewOpen(false)} className="p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-white/10 text-gray-400 transition-colors"><X size={16}/></button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 bg-[#FAFAFA] dark:bg-[#0F1117]">
              {previewLoading ? (
                <div className="flex items-center justify-center py-20 gap-3 text-gray-400"><Loader2 size={18} className="animate-spin"/><span className="text-[13px]">加载合同内容...</span></div>
              ) : (
                <pre className="whitespace-pre-wrap font-mono text-[12px] leading-[1.8] text-gray-700 dark:text-gray-300 bg-white dark:bg-[#151822] rounded-[16px] p-6 border border-gray-100 dark:border-white/10 shadow-sm">{previewContent}</pre>
              )}
            </div>
            <div className="px-6 py-4 border-t border-gray-100 dark:border-white/10 shrink-0 flex items-center justify-between">
              <p className="text-[11px] text-gray-400">⚠️ 合同中的【法律风险提示】为 AI 预标注，仅供参考</p>
              <button onClick={() => setPreviewOpen(false)} className="px-4 py-1.5 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-semibold transition-colors">关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}





