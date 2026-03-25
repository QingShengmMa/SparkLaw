'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, Send, FileText, Sparkles, PenLine,
  Scale, Briefcase, AlertOctagon, Download, Copy,
  MessageSquare, Building2, ShieldAlert, ArrowUpRight,
  UserRound, File, Image as ImageIcon, RefreshCw,
  Library, Loader2, RotateCcw, CheckCircle2, AlertCircle, X,
} from 'lucide-react';
import { streamDraft, streamRefine } from '@/lib/api';

type DraftStatus = 'idle' | 'drafting' | 'results';

interface Template {
  icon: React.ReactElement;
  title: string;
  text: string;
}

const ALL_TEMPLATES: Template[] = [
  { icon: <AlertOctagon size={16} />, title: '催款律师函', text: '我方是[我方公司全称]，对方[对方公司全称]因[业务背景/项目名称]拖欠我方各项款项共计人民币[金额]元。逾期已有[时长]个月，请起草一份措辞极其严厉的催款律师函，要求其在收到函件后3个工作日内结清全款，否则我方将提起诉讼。' },
  { icon: <Scale size={16} />, title: '民事起诉状', text: '我要起草一份规范的民事起诉状。原告：[原告姓名/公司]，被告：[被告姓名/公司]。诉讼请求：1. 判令被告立即偿还借款本金[金额]元；2. 支付逾期利息（自逾期日起至实际清偿日止）；3. 本案诉讼费由被告承担。事实与理由部分：[简述违约事实]。' },
  { icon: <Briefcase size={16} />, title: '解除劳动关系', text: '起草一份发给员工的《解除劳动合同通知书》。员工姓名[员工姓名]，因该员工存在严重违反公司规章制度的行为（具体事由：[连续旷工超3天/严重失职]），公司决定于[生效日期]起正式单方解除劳动关系，且依法不予支付经济补偿金。' },
  { icon: <FileText size={16} />, title: '婚前财产协议', text: '起草一份婚前财产协议。核心条款：1. 男方名下房产（地址：...）及婚后产生的所有增值、收益均属于男方婚前个人财产；2. 婚后双方的工资等收入实行财产分别制；3. 婚前及婚后以个人名义所负债务由各自承担。' },
  { icon: <Building2 size={16} />, title: '股权转让协议', text: '起草一份有限责任公司股权转让协议。转让方将持有的[目标公司名称]XX%的股权转让给受让方。转让对价为人民币XX万元，分两期支付：协议签署后3日内支付50%，工商变更登记完成后5日内支付剩余50%。请加入转让前隐性债务由转让方承担的兜底担保条款。' },
  { icon: <ShieldAlert size={16} />, title: '商业保密协议', text: '为我司起草一份《员工保密及竞业限制协议》。要求：1. 离职后永久对公司商业秘密保密；2. 竞业限制期限为2年；3. 竞业补偿金按离职前12个月平均工资的30%按月发放；4. 违反竞业限制需支付违约金[金额]万元。' },
  { icon: <PenLine size={16} />, title: '公开发布严正声明', text: '帮我写一份对外公开发布的《严正声明》。背景：近期网络平台上出现大量针对我司（[公司全称]）的不实谣言。声明要求：1. 严厉谴责造谣传谣行为；2. 勒令立即停止侵权并删帖；3. 我司已委托律师取证，坚决追究法律责任。' },
  { icon: <UserRound size={16} />, title: '离婚起诉状', text: '起草一份离婚纠纷民事起诉状。原告[姓名]，被告[姓名]。事实与理由强调双方因[性格不合/分居]导致感情确已彻底破裂。诉讼请求：1. 依法判令原被告离婚；2. 婚生子/女[姓名]抚养权归原告，被告每月支付抚养费[金额]元；3. 依法平均分割双方共同财产。' },
  { icon: <FileText size={16} />, title: '房屋租赁合同', text: '起草一份保护出租方权益的《房屋租赁合同》。出租方[姓名]，承租方[姓名]。标的位于[地址]，租期为[期限]，月租金[金额]元。核心条款：1. 严禁擅自转租或群租；2. 逾期交租超7天有权解除合同并没收全额押金；3. 承租期内物业水电等由承租方承担。' },
  { icon: <Briefcase size={16} />, title: '和解协议书', text: '起草一份民事纠纷《和解协议书》。甲乙双方因[纠纷事由]产生争议，现协商和解。约定：1. 乙方于[日期]前一次性向甲方支付和解款[金额]元；2. 甲方收到全款后，自愿放弃其余诉求，并承诺不再向乙方主张权利；3. 双方对协议内容绝对保密。' },
  { icon: <AlertOctagon size={16} />, title: '知识产权维权', text: '撰写一份关于知识产权侵权的《律师函》。委托人是[商标/专利名称]的合法权利人。对方（[侵权方公司全称]）未经授权擅自使用。要求对方立即停止一切侵权行为，下架商品，并赔偿经济损失。态度要极其强硬，并附带明确的起诉警告。' },
  { icon: <Scale size={16} />, title: '劳动仲裁申请', text: '起草一份《劳动争议仲裁申请书》。申请人：[姓名]，被申请人：[公司全称]。诉求：1. 裁决支付自[日期]至[日期]拖欠的工资共计[金额]元；2. 裁决支付违法解除劳动合同赔偿金（2N）共计[金额]元。事实与理由重点说明遭非法辞退的过程。' },
];

function PromptCapsule({ icon, title, previewText, onClick }: {
  icon: React.ReactElement; title: string; previewText: string; onClick: () => void;
}) {
  return (
    <div onClick={onClick} className="group relative flex flex-col p-4 bg-white dark:bg-[#151822] border border-gray-100 dark:border-white/10 hover:border-blue-200 hover:bg-gradient-to-br hover:from-white hover:to-blue-50/50 rounded-[20px] cursor-pointer transition-all duration-300 shadow-[0_2px_10px_rgba(0,0,0,0.01)] hover:shadow-[0_4px_15px_rgba(59,130,246,0.08)] active:scale-[0.98]">
      <div className="flex items-center gap-2 mb-2 text-gray-700 dark:text-gray-200 group-hover:text-blue-700 transition-colors">
        <div className="text-gray-400 group-hover:text-blue-600 transition-colors">{icon}</div>
        <span className="text-[13px] font-bold">{title}</span>
        <ArrowUpRight size={14} className="ml-auto text-gray-300 opacity-0 group-hover:opacity-100 group-hover:text-blue-500 transition-all -translate-x-2 translate-y-2 group-hover:translate-x-0 group-hover:translate-y-0" />
      </div>
      <p className="text-[11px] text-gray-400 dark:text-gray-500 line-clamp-2 leading-relaxed group-hover:text-blue-700/70 transition-colors">&ldquo;{previewText}&rdquo;</p>
    </div>
  );
}

function FullLibraryModal({ onClose, onSelect }: {
  onClose: () => void;
  onSelect: (text: string) => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[3px]"/>
      <div
        className="relative w-full max-w-[820px] max-h-[85vh] flex flex-col bg-white dark:bg-[#151822] rounded-[28px] shadow-2xl border border-gray-100 dark:border-white/10 overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-8 py-5 border-b border-gray-100 dark:border-white/10 shrink-0">
          <div className="flex items-center gap-3">
            <Library size={18} className="text-blue-600"/>
            <h2 className="text-[16px] font-bold text-gray-900 dark:text-gray-100">全量文书模板库</h2>
            <span className="text-[11px] font-semibold text-gray-400 bg-gray-100 dark:bg-white/10 px-2 py-0.5 rounded-full">{ALL_TEMPLATES.length} 个模板</span>
          </div>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-white/10 text-gray-400 transition-colors"><X size={16}/></button>
        </div>
        <div className="overflow-y-auto p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {ALL_TEMPLATES.map((tpl, idx) => (
              <button
                key={idx}
                onClick={() => { onSelect(tpl.text); onClose(); }}
                className="group text-left bg-[#F8F9FB] dark:bg-white/5 hover:bg-blue-50 dark:hover:bg-blue-900/20 border border-gray-100 dark:border-white/10 hover:border-blue-200 dark:hover:border-blue-700/50 rounded-[18px] p-4 transition-all duration-200 active:scale-[0.98]"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-gray-400 group-hover:text-blue-600 transition-colors">{tpl.icon}</span>
                  <span className="text-[13px] font-bold text-gray-800 dark:text-gray-100 group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors">{tpl.title}</span>
                  <ArrowUpRight size={12} className="ml-auto text-gray-300 opacity-0 group-hover:opacity-100 group-hover:text-blue-500 transition-all"/>
                </div>
                <p className="text-[11px] text-gray-400 dark:text-gray-500 line-clamp-2 leading-relaxed group-hover:text-blue-600/70 dark:group-hover:text-blue-400/70 transition-colors">
                  &ldquo;{tpl.text.slice(0, 60)}...&rdquo;
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DraftingPage() {
  const router = useRouter();
  const [status, setStatus] = useState<DraftStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [prompt, setPrompt] = useState('');
  const [templatePage, setTemplatePage] = useState(0);
  const [showLibrary, setShowLibrary] = useState(false);
  const [draftContent, setDraftContent] = useState('');
  const [streamingContent, setStreamingContent] = useState('');
  const [refineInput, setRefineInput] = useState('');
  const [refineLoading, setRefineLoading] = useState(false);
  const [refineMessages, setRefineMessages] = useState<{ role: 'user' | 'ai'; text: string }[]>([]);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachedFileName, setAttachedFileName] = useState('');
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (status === 'idle' && inputRef.current) inputRef.current.focus(); }, [status]);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [refineMessages]);

  const visibleTemplates = ALL_TEMPLATES.slice(templatePage * 3, templatePage * 3 + 3);
  const handleNextPage = () => setTemplatePage(p => (p + 1) % 4);
  const handleTemplateSelect = (text: string) => { setPrompt(text); inputRef.current?.focus(); };

  const handleFileAttach = (accept: string) => {
    if (fileInputRef.current) {
      fileInputRef.current.accept = accept;
      fileInputRef.current.click();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setAttachedFile(f);
    setAttachedFileName(f.name);
    e.target.value = '';
  };

  const handleStartDrafting = useCallback(async () => {
    if (!prompt.trim()) return;
    setStatus('drafting');
    setProgress(0);
    setLogs([]);
    setStreamingContent('');
    setDraftContent('');
    setError('');

    abortRef.current = new AbortController();

    // Safety: if still in drafting after 130s, force-reset
    const safetyTimer = setTimeout(() => {
      if (abortRef.current) abortRef.current.abort();
      setError('生成超时（130秒），请检查网络后重试');
      setStatus('idle');
    }, 130_000);

    try {
      await streamDraft(
        { prompt, templateType: '', file: attachedFile || undefined },
        (ev) => {
          if (ev.type === 'log') {
            setProgress(ev.progress);
            setLogs(prev => [...prev, ev.message].slice(-20));
          } else if (ev.type === 'token') {
            setStreamingContent(prev => prev + ev.token);
          } else if (ev.type === 'done') {
            clearTimeout(safetyTimer);
            setProgress(100);
            setDraftContent(ev.content);
            setRefineMessages([{
              role: 'ai',
              text: '已为您生成基础版本。如需调整，可在下方输入指令，例如：语气更严厉、补充特定条款、增加维权成本诉求等。',
            }]);
            setStatus('results');
          } else if (ev.type === 'error') {
            clearTimeout(safetyTimer);
            setError(ev.message);
            setStatus('idle');
          }
        },
        abortRef.current.signal,
      );
    } catch (e) {
      clearTimeout(safetyTimer);
      if ((e as Error).name !== 'AbortError') {
        setError(e instanceof Error ? e.message : '生成失败，请重试');
        setStatus('idle');
      }
    }
  }, [prompt, attachedFile]);

  const handleRefine = useCallback(async () => {
    if (!refineInput.trim() || refineLoading) return;
    const instruction = refineInput.trim();
    setRefineInput('');
    setRefineMessages(prev => [...prev, { role: 'user', text: instruction }]);
    setRefineLoading(true);
    let refined = '';
    const refineAbort = new AbortController();
    try {
      await streamRefine(
        { currentContent: draftContent, instruction },
        (ev) => {
          if (ev.type === 'token') {
            refined += ev.token;
            setDraftContent(refined);
          } else if (ev.type === 'done') {
            setDraftContent(ev.content);
            setRefineMessages(prev => [...prev, { role: 'ai', text: '已按您的要求完成修改。如需进一步调整，请继续输入。' }]);
          } else if (ev.type === 'error') {
            setRefineMessages(prev => [...prev, { role: 'ai', text: `润色失败：${ev.message}` }]);
          }
        },
        refineAbort.signal,
      );
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        setRefineMessages(prev => [...prev, { role: 'ai', text: `润色失败：${e instanceof Error ? e.message : '网络异常，请重试'}` }]);
      }
    } finally {
      setRefineLoading(false);
    }
  }, [refineInput, draftContent, refineLoading]);

  const handleReset = () => {
    abortRef.current?.abort();
    setStatus('idle'); setProgress(0); setLogs([]); setPrompt('');
    setDraftContent(''); setStreamingContent(''); setRefineMessages([]);
    setAttachedFile(null); setAttachedFileName(''); setError('');
  };

  const handleCopy = async () => { await navigator.clipboard.writeText(draftContent); };
  const displayContent = status === 'drafting' ? streamingContent : draftContent;

  return (
    <div className="relative flex flex-col h-full w-full bg-[#FDFDFF] dark:bg-[#0B0D14] text-[#1F1F1F] dark:text-gray-100 font-sans overflow-hidden transition-colors duration-300">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-blue-50/40 dark:bg-blue-900/10 rounded-full blur-[100px] pointer-events-none opacity-60" />
      <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileChange} />
      {error && (
        <div className="fixed top-4 right-4 z-50 flex items-center gap-3 bg-white dark:bg-[#151822] border border-red-100 dark:border-white/10 text-red-600 dark:text-red-400 rounded-[16px] px-5 py-3 text-[13px] shadow-lg">
          <AlertCircle size={15}/> {error} <button onClick={() => setError('')} className="ml-2 opacity-60 hover:opacity-100">✕</button>
        </div>
      )}
      <main className="relative z-10 flex-1 flex flex-col overflow-y-auto">
        <div className="flex-1 flex flex-col w-full px-6 pt-4 pb-2 h-full">
          <header className="mb-5 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-4">
              <button onClick={() => status === 'results' ? handleReset() : router.push('/tools')} className="p-2 rounded-full hover:bg-[#F0F4F9] dark:hover:bg-white/10 text-[#444746] dark:text-gray-400 transition-colors active:scale-95">
                {status === 'results' ? <RotateCcw size={18}/> : <ArrowLeft size={18}/>}
              </button>
              <h1 className="text-2xl font-bold tracking-tight text-[#1F1F1F] dark:text-gray-100">文书起草 ✍️</h1>
              {attachedFileName && status === 'idle' && (
                <span className="text-[12px] text-blue-500 font-medium flex items-center gap-1"><FileText size={12}/> {attachedFileName} <button onClick={() => { setAttachedFile(null); setAttachedFileName(''); }} className="text-gray-300 hover:text-red-400 ml-1">✕</button></span>
              )}
            </div>
            {status === 'results' && (
              <div className="flex items-center gap-2">
                <button onClick={handleCopy} className="flex items-center gap-1.5 px-4 py-1.5 rounded-full border border-gray-200 dark:border-white/10 bg-white dark:bg-[#151822] hover:bg-gray-50 text-[13px] font-medium text-gray-600 dark:text-gray-300 transition-colors"><Copy size={13}/> 复制</button>
                <button className="px-5 py-2 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-all flex items-center gap-2"><Download size={14}/> 导出 Word</button>
              </div>
            )}
          </header>
          <div className="flex-1 flex flex-col justify-center">
            {status === 'idle' && (
              <div className="flex flex-col items-center w-full max-w-[800px] mx-auto my-auto">
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold tracking-tight mb-2">输入案件事实，<span className="text-blue-600">一键起草文书</span></h2>
                  <p className="text-sm text-[#444746] dark:text-gray-400 opacity-70">用自然语言描述诉求，或上传相关证据材料，AI 将自动生成专业法律文书。</p>
                </div>
                <div className="w-full relative mb-6 group">
                  <div className="absolute -inset-1 bg-gradient-to-r from-blue-500/10 to-indigo-600/10 rounded-[32px] blur-lg opacity-0 group-hover:opacity-100 transition duration-500" />
                  <div className="relative bg-white dark:bg-[#151822] border border-gray-100 dark:border-white/10 hover:border-blue-200 focus-within:!border-blue-400 focus-within:ring-4 focus-within:ring-blue-500/10 rounded-[28px] p-2 transition-all flex flex-col">
                    <textarea ref={inputRef} value={prompt} onChange={e => setPrompt(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleStartDrafting(); } }}
                      placeholder="在这里描述案件事实。例如：客户拖欠了 50 万尾款长达半年，帮我写一份措辞严厉的律师函..."
                      className="w-full h-[150px] bg-transparent resize-none outline-none p-5 text-[15px] text-gray-800 dark:text-gray-100 placeholder-gray-400 leading-relaxed"
                    />
                    <div className="flex justify-between items-center px-3 pb-2 pt-2 border-t border-gray-50/50 dark:border-white/5">
                      <div className="flex items-center gap-1.5">
                        <button onClick={() => handleFileAttach('.docx,.doc')} className="flex items-center gap-1.5 px-3 py-2 rounded-[14px] text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"><FileText size={16}/><span className="text-[12px] font-medium hidden sm:inline">Word</span></button>
                        <button onClick={() => handleFileAttach('.pdf')} className="flex items-center gap-1.5 px-3 py-2 rounded-[14px] text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"><File size={16}/><span className="text-[12px] font-medium hidden sm:inline">PDF</span></button>
                        <button onClick={() => handleFileAttach('image/*')} className="flex items-center gap-1.5 px-3 py-2 rounded-[14px] text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"><ImageIcon size={16}/><span className="text-[12px] font-medium hidden sm:inline">图片</span></button>
                      </div>
                      <button onClick={handleStartDrafting} disabled={!prompt.trim()} className={`p-3 rounded-[16px] flex items-center justify-center transition-all ${ prompt.trim() ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md active:scale-95' : 'bg-gray-50 dark:bg-white/5 text-gray-300 cursor-not-allowed'}`}><Send size={18}/></button>
                    </div>
                  </div>
                </div>
                <div className="w-full flex flex-col gap-3">
                  <div className="flex items-center justify-between px-2">
                    <div className="flex items-center gap-1.5 text-[12px] text-gray-500 font-bold tracking-wider"><Sparkles size={14} className="text-blue-500"/> 试试这样吩咐 AI</div>
                    <div className="flex items-center gap-4">
                      <button onClick={handleNextPage} className="text-[12px] text-gray-400 hover:text-blue-600 flex items-center gap-1.5 font-medium active:scale-95"><RefreshCw size={14}/> 换一批</button>
                      <div className="w-px h-3 bg-gray-200 dark:bg-white/10" />
                      <button onClick={() => setShowLibrary(true)} className="text-[12px] text-gray-400 hover:text-[#1F1F1F] dark:hover:text-gray-100 flex items-center gap-1.5 font-medium"><Library size={14}/> 全量库</button>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {visibleTemplates.map((tpl,idx) => <PromptCapsule key={idx} icon={tpl.icon} title={tpl.title} previewText={tpl.text} onClick={() => handleTemplateSelect(tpl.text)}/>)}
                  </div>
                </div>
              </div>
            )}
            {/* DRAFTING */}
            {status === 'drafting' && (
              <div className="flex flex-col items-center justify-center h-full">
                <div className="w-full max-w-[860px] grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                  <div className="relative aspect-[3/4] bg-white dark:bg-[#151822] rounded-[32px] border border-gray-100 dark:border-white/10 overflow-hidden p-10 shadow-[0_10px_40px_rgba(0,0,0,0.03)]">
                    <div className="space-y-3 opacity-10">{Array.from({length:10}).map((_,i)=><div key={i} className={`h-2 rounded-full bg-gray-300 ${i%3===0?'w-1/2':i%3===1?'w-full':'w-3/4'}`}/>)}</div>
                    {displayContent && <div className="absolute inset-0 p-8 overflow-hidden text-[9px] leading-relaxed text-gray-600 dark:text-gray-400 font-mono opacity-60 select-none">{displayContent}</div>}
                    <div className="absolute left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-blue-500 to-transparent z-20" style={{top:`${Math.min(progress,98)}%`,transition:'top 0.15s linear',boxShadow:'0 0 12px rgba(59,130,246,0.6)'}}/>
                    <div className="absolute inset-0 bg-blue-500/5" style={{clipPath:`inset(0 0 ${100-Math.min(progress,98)}% 0)`}}/>
                  </div>
                  <div className="space-y-8">
                    <div>
                      <div className="flex justify-between items-end mb-2">
                        <h3 className="text-lg font-bold flex items-center gap-2 text-gray-800 dark:text-gray-100"><PenLine className="text-blue-600 animate-bounce" size={18}/> AI 撰写中...</h3>
                        <span className="text-lg font-mono text-blue-600 font-bold">{Math.floor(progress)}%</span>
                      </div>
                      <div className="w-full h-1 bg-gray-100 dark:bg-white/10 rounded-full overflow-hidden"><div className="h-full bg-blue-600 transition-all duration-300 rounded-full" style={{width:`${progress}%`}}/></div>
                    </div>
                    <div className="bg-[#1A1C1E] dark:bg-[#151822] rounded-[24px] p-6 h-56 overflow-y-auto">
                      <div className="text-[9px] font-black uppercase tracking-widest text-gray-600 mb-3 pb-2 border-b border-white/5">Drafting Engine Logs</div>
                      <div className="space-y-2">
                        {logs.map((log,i)=>(<div key={i} className="flex gap-3 text-[11px]"><span className="text-blue-400/50 shrink-0">[{String(i).padStart(2,'0')}]</span><span className="text-gray-400">{log}</span></div>))}
                        <div className="w-1 h-3 bg-blue-500 animate-pulse mt-1"/>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            {/* RESULTS */}
            {status === 'results' && (
              <div className="flex overflow-hidden gap-6 h-full py-2">
                <div className="flex-1 bg-white dark:bg-[#151822] rounded-[28px] flex flex-col overflow-hidden shadow-sm border border-gray-100/60 dark:border-white/10">
                  <div className="px-8 py-4 border-b border-gray-50 dark:border-white/5 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-2"><FileText size={16} className="text-gray-400"/><span className="font-bold text-xs text-gray-800 dark:text-gray-200 tracking-tight">文书生成结果</span></div>
                    <button onClick={handleCopy} className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-gray-50 dark:bg-white/5 hover:bg-gray-100 dark:hover:bg-white/10 text-gray-600 dark:text-gray-300 text-[10px] font-bold transition-colors"><Copy size={12}/> 复制全文</button>
                  </div>
                  <div className="flex-1 overflow-y-auto p-8 lg:px-12 bg-[#FAFAFA] dark:bg-[#0F1117]">
                    <div className="max-w-[650px] mx-auto bg-white dark:bg-[#151822] p-10 lg:p-14 shadow-[0_2px_15px_rgba(0,0,0,0.04)] border border-gray-100 dark:border-white/10 min-h-full font-serif text-[#1F1F1F] dark:text-gray-100 text-[14px] leading-[2]">
                      <pre className="whitespace-pre-wrap font-serif text-[14px] leading-[2] text-inherit">{displayContent}</pre>
                    </div>
                  </div>
                </div>
                <div className="w-[340px] flex flex-col gap-4 shrink-0">
                  <div className="bg-[#1A1C1E] dark:bg-[#151822] rounded-[28px] p-6 text-white border border-transparent dark:border-white/10 flex flex-col items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400"><CheckCircle2 size={20}/></div>
                    <div className="text-center"><h3 className="text-base font-bold">文书已就绪</h3><p className="text-[11px] text-gray-400 mt-1">可直接复制，或使用下方 AI 进行微调</p></div>
                  </div>
                  <div className="flex-1 bg-white dark:bg-[#151822] rounded-[28px] flex flex-col overflow-hidden border border-gray-100/60 dark:border-white/10 shadow-sm">
                    <div className="px-6 py-4 border-b border-gray-50 dark:border-white/5 shrink-0 flex items-center gap-2">
                      <MessageSquare size={15} className="text-blue-600"/>
                      <h3 className="font-bold text-xs text-gray-800 dark:text-gray-200 uppercase tracking-widest">AI 细节润色</h3>
                    </div>
                    <div className="flex-1 p-4 overflow-y-auto bg-[#FAFAFA] dark:bg-[#0F1117] space-y-3">
                      {refineMessages.map((msg, i) => (
                        <div key={i} className={`rounded-[16px] px-4 py-3 text-[12px] leading-relaxed max-w-[90%] ${
                          msg.role === 'user'
                            ? 'ml-auto bg-blue-600 text-white rounded-tr-sm'
                            : 'bg-white dark:bg-[#151822] border border-gray-100 dark:border-white/10 text-gray-700 dark:text-gray-300 rounded-tl-sm'
                        }`}>{msg.text}</div>
                      ))}
                      {refineLoading && <div className="flex items-center gap-2 text-[11px] text-gray-400"><Loader2 size={12} className="animate-spin"/> AI 正在润色...</div>}
                      <div ref={chatEndRef}/>
                    </div>
                    <div className="p-4 bg-white dark:bg-[#151822] border-t border-gray-50 dark:border-white/5 shrink-0">
                      <div className="relative bg-[#F0F4F9] dark:bg-white/5 rounded-[16px] flex items-center p-1.5 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
                        <input type="text" value={refineInput} onChange={e => setRefineInput(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') handleRefine(); }}
                          placeholder="例如：语气再严厉一些、补充违约金条款..."
                          className="flex-1 bg-transparent text-[12px] px-3 outline-none placeholder-gray-400 dark:text-gray-200 h-8"
                        />
                        <button onClick={handleRefine} disabled={refineLoading || !refineInput.trim()} className="w-8 h-8 rounded-xl bg-blue-600 disabled:opacity-40 text-white flex items-center justify-center hover:bg-blue-700 transition-colors shrink-0">
                          {refineLoading ? <Loader2 size={13} className="animate-spin"/> : <Send size={13} className="-ml-0.5"/>}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
          <footer className="mt-auto pt-4 pb-2 text-center shrink-0">
            <p className="text-xs text-gray-400 dark:text-white/40 font-normal tracking-wide">AI 生成内容仅供参考，不构成正式法律意见</p>
          </footer>
        </div>
      </main>
      {showLibrary && (
        <FullLibraryModal
          onClose={() => setShowLibrary(false)}
          onSelect={(text) => { setPrompt(text); inputRef.current?.focus(); }}
        />
      )}
    </div>
  );
}