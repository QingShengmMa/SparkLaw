'use client';

import React, { useState, useRef, useCallback } from 'react';
import {
  Scale, Gavel, Users, Shield, Zap,
  MessageSquare, Plus, Trash2, ArrowLeft, Award,
  Clock, FileSearch, Target, CheckCircle2,
  AlertCircle, Settings2,
  PieChart, Star, RefreshCw, Library, X, ArrowUpRight,
  PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen,
} from 'lucide-react';
import { streamCourtDebate, CourtSSEEvent } from '@/lib/api';

// 后端新协议扩展类型
interface CourtChunkEvent {
  type: 'new_message' | 'chunk' | 'result' | 'evidence_list' | 'law_list' | 'evidence_reference' | 'law_reference' | 'thread';
  msg_id?: string;
  node?: string;
  role?: string;
  role_key?: string;
  phase?: string;
  content?: string;
  evidence_id?: string;
  law_id?: string;
  evidence_list?: EvidenceRefItem[];
  law_list?: LawRefItem[];
  result?: {
    transcript?: Array<{ role: string; role_key: string; phase: string; content: string }>;
    verdict?: string;
    plaintiff_win_rate?: number;
    defendant_win_rate?: number;
    evidence_list?: EvidenceRefItem[];
    law_list?: LawRefItem[];
  };
}
type AnyCourtEvent = CourtSSEEvent | CourtChunkEvent;

type View = 'setup' | 'live' | 'review';
type UserRole = 'plaintiff' | 'defendant' | 'audience';
interface EvidenceItem { id: number; category: string; content: string; }
interface AiPersonas { plaintiff: string; defendant: string; judge: string; }
interface ChatMsg {
  msgId?: string;
  role: 'judge' | 'plaintiff' | 'defendant' | 'system' | 'user';
  name: string; content: string; isFollowUp?: boolean;
}
interface LawRefItem { id: string; title: string; content: string; source?: string; party?: 'plaintiff' | 'defendant' | 'both'; }
interface EvidenceRefItem { id: string; title: string; content: string; source?: string; party?: 'plaintiff' | 'defendant' | 'both'; }
interface HoverRefOptions {
  onRefHover?: (type: '证据' | '法条', value: string) => void;
  onRefLeave?: () => void;
  onRefClick?: (type: '证据' | '法条', value: string) => void;
  resolveRefDetail?: (type: '证据' | '法条', value: string) => string | undefined;
}
interface ReviewData {
  win_probability: { plaintiff: number; defendant: number };
  summary: string;
  keyPoints: string[];
  transcript?: ChatMsg[];
  evidenceRefs?: EvidenceRefItem[];
  lawRefs?: LawRefItem[];
  scores?: { statute: number; logic: number; jury: number };
}
interface CaseExample {
  label: string;
  text: string;
}

interface SetupViewProps {
  caseDesc: string;
  setCaseDesc: (v: string) => void;
  userRole: UserRole;
  setUserRole: (v: UserRole) => void;
  evidence: { plaintiff: EvidenceItem[]; defendant: EvidenceItem[] };
  addEv: (s: 'plaintiff'|'defendant') => void;
  updEv: (s: 'plaintiff'|'defendant', id: number, patch: Partial<EvidenceItem>) => void;
  delEv: (s: 'plaintiff'|'defendant', id: number) => void;
  aiPersonas: AiPersonas;
  setAiPersonas: (v: AiPersonas) => void;
  onStart: () => void;
  visibleCaseExamples: CaseExample[];
  onShuffleCaseExamples: () => void;
  onOpenCaseLibrary: () => void;
}

const JUDGE_STYLES = ['法条释明型', '程序主导型', '实质审查型'];
const PARTY_STYLES = ['法条论证型', '证据链推进型', '攻防博弈型'];

const PARTY_STYLE_DESC: Record<string, string> = {
  法条论证型: '以法条构成要件为核心，强调请求权基础与规范适用。',
  证据链推进型: '围绕证据三性与证明力展开，逐步搭建或拆解事实链条。',
  攻防博弈型: '兼顾进攻与防守节奏，强调交叉质证与论点反制。',
};

const JUDGE_STYLE_DESC: Record<string, string> = {
  法条释明型: '偏重法律释明与规范阐释，聚焦法理与裁判依据。',
  程序主导型: '强调程序秩序与举证责任分配，控制庭审节奏。',
  实质审查型: '注重事实查明与实质正义，深入追问关键争点。',
};
const EVIDENCE_CATEGORIES = ['书证', '物证', '电子数据', '证人证言', '鉴定意见', '视听资料'];

function extractEvidenceCategory(name: string): string {
  const matched = name.match(/^(.*?)(\d{3})$/);
  return matched?.[1] || EVIDENCE_CATEGORIES[0];
}

function buildEvidenceName(category: string, seq: number): string {
  return `${category}${String(seq).padStart(3, '0')}`;
}

function toPlainDisplayText(raw: string): string {
  const cleaned = (raw || '')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*/g, '')
    .trim();

  return cleaned
    .replace(/\s*【/g, '\n【')
    .replace(/\s*(\d+)[\.、]\s*/g, '\n$1. ')
    .replace(/([。；;])(?!\n)/g, '$1\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

const TRIAL_STAGES = ['开庭准备', '法庭调查', '举证质证', '法庭辩论', '最后陈述', '评议宣判'] as const;
type TrialStage = typeof TRIAL_STAGES[number];

function detectTrialStage(text: string): TrialStage | null {
  const t = toPlainDisplayText(text);
  if (!t) return null;

  if (/宣布开庭|核对当事人|法庭纪律|案由|开庭/.test(t)) return '开庭准备';
  if (/法庭调查|诉讼请求|答辩|争议焦点|事实/.test(t)) return '法庭调查';
  if (/举证|质证|证据|三性|证明力/.test(t)) return '举证质证';
  if (/法庭辩论|辩论意见|代理意见|辩论阶段/.test(t)) return '法庭辩论';
  if (/最后陈述|最后意见|补充意见/.test(t)) return '最后陈述';
  if (/评议|宣判|裁判|判决|本庭认为|裁判结论|verdict/.test(t)) return '评议宣判';

  return null;
}

function renderReadableMessage(raw: string, options?: HoverRefOptions): React.ReactNode {
  const text = toPlainDisplayText(raw);
  if (!text) return null;

  const renderLineWithRefs = (line: string): React.ReactNode[] => {
    const nodes: React.ReactNode[] = [];
    const regex = /\[(证据|法条):([^\]]+)\]/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(line)) !== null) {
      if (match.index > lastIndex) nodes.push(line.slice(lastIndex, match.index));
      const type = match[1];
      const rawValue = match[2];
      // Resolve ID to human-readable title if possible
      const detail = options?.resolveRefDetail?.(type as '证据' | '法条', rawValue);
      const isRawId = /^(evidence|law|ev|evi)_?\d+$/i.test(rawValue);
      const displayLabel = isRawId && detail ? detail.split('\n')[0] : rawValue;
      nodes.push(
        <span
          key={`${type}-${rawValue}-${match.index}`}
          title={detail || `${type}:${rawValue}`}
          onMouseEnter={() => options?.onRefHover?.(type as '证据' | '法条', rawValue)}
          onMouseLeave={() => options?.onRefLeave?.()}
          onClick={() => options?.onRefClick?.(type as '证据' | '法条', rawValue)}
          className={type === '证据'
            ? 'inline-flex mx-0.5 px-2 py-0.5 rounded-md text-[11px] font-semibold align-middle bg-emerald-50 text-emerald-700 border border-emerald-200 cursor-pointer hover:bg-emerald-100 dark:bg-emerald-900/25 dark:text-emerald-200 dark:border-emerald-700/60 dark:hover:bg-emerald-900/40'
            : 'inline-flex mx-0.5 px-2 py-0.5 rounded-md text-[11px] font-semibold align-middle bg-indigo-50 text-indigo-700 border border-indigo-200 cursor-pointer hover:bg-indigo-100 dark:bg-indigo-900/25 dark:text-indigo-200 dark:border-indigo-700/60 dark:hover:bg-indigo-900/40'}
        >
          {type}:{displayLabel}
        </span>
      );
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < line.length) nodes.push(line.slice(lastIndex));
    return nodes;
  };

  const lines = text.split('\n').map(s => s.trim()).filter(Boolean);
  return (
    <div className="space-y-2">
      {lines.map((line, idx) => {
        const isPoint = /^\d+\./.test(line);
        return (
          <p key={`${idx}-${line.slice(0, 16)}`} className={isPoint ? 'pl-3 border-l-2 border-slate-200' : ''}>
            {renderLineWithRefs(line)}
          </p>
        );
      })}
    </div>
  );
}

const CASE_EXAMPLES: CaseExample[] = [
  { label: '软著侵权', text: '原告系某企业管理软件著作权人，提交源代码开发日志、版本迭代记录及软著登记证书，主张被告上线的同类系统在核心算法、数据库结构和界面交互上高度近似。被告抗辩称系独立开发并委托第三方外包完成。原告诉请判令停止侵权、公开消除影响并赔偿经济损失及合理维权费用合计500万元。' },
  { label: '劳动争议', text: '员工在公司工作四年，主张公司长期未足额缴纳社保且存在加班费未支付情形，后以单位违法用工为由解除劳动关系并申请仲裁。公司则称员工多次旷工且绩效不达标，解除行为合法。员工请求支付经济补偿金、未休年休假工资及加班费共计9万元，并补缴社保。' },
  { label: '合同纠纷', text: '原告与被告签订房屋买卖合同并支付定金20万元，约定两个月内办理过户。后被告以市场价格上涨为由拒绝履行并将房屋另售他人。原告主张被告构成根本违约，要求双倍返还定金40万元、赔偿差价损失及中介评估费用。被告抗辩称原告未按时筹集余款，系原告先违约。' },
  { label: '租赁纠纷', text: '租赁合同尚余九个月，房东以“自住装修”为由要求租客限期搬离，后多次停水停电并更换门锁。租客提交转账记录、物业投诉记录及聊天记录，主张房东提前解约并采取不当手段，应返还押金、赔偿搬迁损失和停业损失。房东抗辩称租客存在转租行为且损坏房屋设施。' },
  { label: '机动车交通事故', text: '被告驾驶小型汽车追尾原告车辆，交警认定被告承担全部责任。原告称事故导致颈椎损伤，产生医疗费、误工费及车辆维修费，并提供病历、工资流水、维修清单等证据。保险公司抗辩部分费用与事故无关且误工期间过长。原告诉请被告与保险公司在责任范围内连带赔偿12万元。' },
  { label: '民间借贷', text: '原告主张向被告分两次出借共30万元，双方签有借条并通过银行转账支付，约定月利率1%及逾期违约责任。被告逾期八个月未还，仅零星支付利息。被告抗辩称其中10万元系投资款非借款。原告诉请返还本金、利息、违约金及保全保险费，并申请对被告名下账户采取财产保全。' },
  { label: '建设工程款', text: '承包方按施工合同完成主体及配套工程并通过竣工验收，发包方仍拖欠工程尾款280万元。承包方提交工程签证、结算报告、验收单和催款函，主张应支付工程价款及逾期利息。发包方抗辩工程存在质量瑕疵且结算金额争议较大。承包方请求先行支付无争议部分并确认优先受偿权。' },
  { label: '商品房质量', text: '业主收房后发现外墙渗漏、窗框变形、卫生间反味等问题，多次报修仅作临时处理，入住后再次出现。业主提交检测报告、维修照片及物业报修工单，主张开发商交付不符合质量标准。开发商辩称问题属正常使用磨损。业主请求判令彻底维修、支付过渡安置费并赔偿装修返工损失。' },
  { label: '物业服务', text: '物业公司起诉业主拖欠两年物业费及滞纳金，业主抗辩小区监控瘫痪、电梯故障频发、保洁不到位，物业未按合同提供服务。业主提交业主群记录、维修报修单及照片视频。物业主张已履行基本管理义务。法院需审查服务质量与收费标准是否匹配，并确定是否应当减免部分物业费。' },
  { label: '网络侵权名誉权', text: '被告在短视频平台连续发布针对原告企业的不实爆料，称其“欺诈消费者”，相关内容被大量转发导致订单明显下滑。原告提交平台数据、公证取证材料及业务损失报表，主张构成名誉侵权和商业诋毁。被告抗辩为“合理评论”。原告请求删除内容、公开道歉并赔偿经济及精神损失。' },
  { label: '医疗损害责任', text: '患者在被告医院接受手术后出现严重并发症并导致长期功能障碍，家属认为术前告知不充分、术中处置不当。医院提交病历资料称已尽到诊疗义务且并发症属可预见风险。双方围绕鉴定结论中“过错参与度”产生争议。原告请求赔偿医疗费、护理费、残疾赔偿金及后续康复费共80万元。' },
  { label: '产品责任', text: '原告购买的家用电器在正常使用中发生短路起火，造成家具及装修受损。原告提交消防出警记录、检测机构意见及购物凭证，主张产品存在设计缺陷。生产商辩称系用户私自改装电路导致，销售商主张仅为中间渠道。原告请求生产商与销售商承担连带赔偿责任并支付鉴定费用。' },
  { label: '知识产权商标', text: '原告拥有注册商标并长期在同类商品使用，被告在电商平台销售商品时使用近似标识并投放关键词广告，造成消费者混淆。原告提交商标证、销量数据、公证购买记录。被告抗辩其标识与原告存在显著差异且已停止销售。原告请求立即停止侵权、销毁库存并赔偿经济损失及维权开支。' },
  { label: '不正当竞争', text: '被告运营自媒体账号发布“横向测评”文章，多处使用绝对化表述贬损原告产品质量并引导用户转向被告品牌。原告主张该行为构成商业诋毁及虚假宣传，提交第三方检测报告、传播数据和客户流失证据。被告称系正常市场比较。原告请求停止侵害、澄清事实并赔偿商誉损失。' },
  { label: '公司股东知情权', text: '原告作为持股10%的小股东，多次书面要求查阅公司会计账簿、董事会决议及关联交易合同，均被以“商业秘密”为由拒绝。原告认为拒绝查阅损害股东法定权利，疑似存在利益输送。公司抗辩原告有竞争关系且查阅目的不正当。原告诉请法院判令公司限期提供查阅并复制相关资料。' },
  { label: '股权代持', text: '原告主张其实际出资并委托被告代持目标公司20%股权，现因双方关系恶化被告拒绝返还。原告提交转账凭证、聊天记录及分红流水，证明存在代持合意。被告抗辩相关款项系借款或经营往来。原告请求确认代持关系成立，判令办理工商变更并返还历年应得分红及相关收益。' },
  { label: '买卖合同质量异议', text: '买方签收工业设备后在试运行阶段提出关键部件存在质量瑕疵并拒付尾款，卖方认为买方已验收且超期提出异议。双方对检验标准、异议期限及替代履行方案存在分歧。买方提交第三方检测报告，卖方提交出厂质检单。法院需判断质量瑕疵是否达到解除合同或减价条件。' },
  { label: '培训服务退费', text: '学员与培训机构签订一年制课程服务协议，缴费后发现师资与宣传不符、课程频繁停开，遂申请退费。机构依据格式条款主张“开课后不退费”。学员认为该条款排除主要权利且未尽提示说明义务。学员请求解除合同、返还剩余课时费用并赔偿交通与资料损失。' },
  { label: '劳动报酬', text: '员工离职后主张公司拖欠加班费、绩效奖金及未签劳动合同二倍工资差额，提交考勤记录、工作邮件和工资流水。公司抗辩加班未经审批且绩效发放以经营指标达成为前提。双方对加班时长和绩效考核规则存在争议。员工请求支付劳动报酬、经济补偿并出具离职证明。' },
  { label: '竞业限制', text: '原单位起诉前员工在离职后六个月内入职竞争企业并接触核心客户，主张违反竞业限制协议应支付违约金。员工抗辩单位未按月支付竞业补偿，协议已失去约束力，且新岗位不构成竞争关系。双方围绕补偿支付记录、岗位重合度和商业秘密接触范围展开举证。' },
  { label: '数据权益争议', text: '平台公司发现合作方通过技术接口超范围抓取用户行为数据并用于商业推荐，认为该行为破坏数据交易秩序并构成不正当竞争。合作方抗辩抓取数据均为公开页面信息且已匿名化处理。原告提交技术日志、风控报告和损失评估。诉请停止抓取、删除数据并赔偿损失。' },
  { label: '平台交易纠纷', text: '商家因平台以“违规营销”为由下架店铺并冻结货款起诉平台，主张平台处罚程序不透明、证据不足且导致订单流失。平台提交规则条款、风控记录及用户投诉。商家抗辩平台条款系格式合同且存在滥用市场优势地位。商家请求恢复经营权限、返还货款并赔偿经营损失。' },
  { label: '保证合同', text: '债务人逾期未偿还贷款后，债权人依据保证合同起诉保证人承担连带清偿责任。保证人抗辩主债务展期未经其书面同意、保证期间已届满且债权人未在法定期间主张权利。债权人提交催收通知、展期协议及送达凭证。争议焦点在于保证责任范围与保证期间起算。' },
  { label: '合伙纠纷', text: '三名合伙人共同经营餐饮项目，后因账目不清和利润分配方式发生冲突，一方申请退伙并要求分割合伙财产。其余合伙人主张退伙方存在擅自转移客户资源、违反竞业约定行为，不应分配当期利润。各方提交流水账、采购合同及经营报表。法院需核算合伙盈亏并确定退伙结算方案。' },
  { label: '旅游服务合同', text: '游客报名出境游后，旅行社擅自减少景点并更换酒店标准，且返程航班延误导致额外住宿支出。游客提交合同、行程单、付款凭证和现场照片，主张旅行社未按约履行主要义务。旅行社抗辩系不可抗力及供应商临时调整。游客请求退还部分团费并赔偿额外支出与精神损失。' },
];

function SetupView({ caseDesc, setCaseDesc, userRole, setUserRole, evidence, addEv, updEv, delEv, aiPersonas, setAiPersonas, onStart, visibleCaseExamples, onShuffleCaseExamples, onOpenCaseLibrary }: SetupViewProps) {
  return (
    <div className="flex-1 overflow-y-auto bg-slate-50 dark:bg-slate-800/50 dark:bg-slate-900/40 p-5 lg:p-6">
      <div className="max-w-6xl mx-auto space-y-6 pb-4">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-slate-800 dark:text-slate-100 mb-3 bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">定制您的模拟法庭</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">按流程完成配置后即可进入庭审。</p>
          <div className="mt-4 relative mx-auto max-w-4xl">
            <div className="absolute left-8 right-8 top-1/2 -translate-y-1/2 h-[2px] bg-gradient-to-r from-blue-200 via-indigo-300 to-cyan-200" />
            <div className="pointer-events-none absolute inset-0 hidden lg:block">
              <svg viewBox="0 0 1000 110" preserveAspectRatio="none" className="w-full h-full">
                <path id="court-flow-orbit" d="M34 55 V20 H226 V90 H34 V55 H280 V20 H472 V90 H280 V55 H526 V20 H718 V90 H526 V55 H772 V20 H964 V90 H772 V55" fill="none" stroke="transparent" />
                <circle r="4.2" fill="#06b6d4" className="drop-shadow-[0_0_8px_rgba(6,182,212,0.95)]">
                  <animateMotion dur="7.2s" repeatCount="indefinite" rotate="auto">
                    <mpath href="#court-flow-orbit" />
                  </animateMotion>
                </circle>
                <circle r="7.5" fill="rgba(6,182,212,0.24)">
                  <animateMotion dur="7.2s" repeatCount="indefinite" rotate="auto">
                    <mpath href="#court-flow-orbit" />
                  </animateMotion>
                </circle>
              </svg>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {([
                { icon: <Gavel className="w-4 h-4"/>, label: '事实' },
                { icon: <Users className="w-4 h-4"/>, label: '身份' },
                { icon: <FileSearch className="w-4 h-4"/>, label: '证据' },
                { icon: <Settings2 className="w-4 h-4"/>, label: '风格' },
              ] as const).map((step, idx) => (
                <div key={step.label} className="relative z-10 group">
                  <div className="mx-auto w-full rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-900/95 backdrop-blur-sm px-3 py-2.5 flex items-center justify-center gap-2 text-slate-600 dark:text-slate-300 shadow-sm transition-all duration-300 group-hover:-translate-y-0.5 group-hover:border-blue-300 group-hover:text-blue-700">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-50 text-blue-600">{step.icon}</span>
                    <span className="text-xs font-semibold tracking-wide">{String(idx + 1).padStart(2, '0')} · {step.label}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <section className="bg-white dark:bg-slate-900 p-5 lg:p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
          <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4 flex items-center"><Gavel className="w-5 h-5 mr-2 text-blue-600"/> 第一步：归纳案件事实与争点</h2>
          <textarea value={caseDesc} onChange={e => setCaseDesc(e.target.value)} rows={4} placeholder="请陈述案件事实、争议焦点、请求事项及主要抗辩..." className="w-full text-sm p-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:ring-1 focus:ring-blue-500 outline-none resize-none transition mb-2"/>
          <div className="mt-2 mb-2 flex flex-wrap items-center justify-between gap-2 px-1">
            <span className="text-[11px] text-slate-400 dark:text-slate-500">以下为案情示例，可直接点击填入后再按需修改。</span>
            <div className="flex items-center gap-4">
              <button onClick={onShuffleCaseExamples} className="text-[12px] text-slate-400 dark:text-slate-500 hover:text-blue-600 flex items-center gap-1.5 font-medium active:scale-95"><RefreshCw className="w-3.5 h-3.5"/> 换一换</button>
              <div className="w-px h-3 bg-slate-200" />
              <button onClick={onOpenCaseLibrary} className="text-[12px] text-slate-400 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 flex items-center gap-1.5 font-medium"><Library className="w-3.5 h-3.5"/> 案情示例库</button>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-2 w-full">
            {visibleCaseExamples.map((ex, i) => (
              <button key={`${ex.label}-${i}`} onClick={() => setCaseDesc(ex.text)} className="min-w-0 h-full text-xs border border-slate-200 dark:border-slate-700 rounded-md px-2.5 py-2.5 hover:border-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 text-slate-600 dark:text-slate-300 hover:text-blue-600 transition text-left">
                <span className="font-bold block mb-0.5">{ex.label}</span>
                <span className="block text-slate-400 dark:text-slate-500 text-[11px] leading-4 line-clamp-2">{ex.text}</span>
              </button>
            ))}
          </div>
        </section>
        <section className="bg-white dark:bg-slate-900 p-5 lg:p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
          <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4 flex items-center"><Users className="w-5 h-5 mr-2 text-blue-600"/> 第二步：选择庭审参与身份</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {([{id:'plaintiff',label:'原告代理人',desc:'围绕请求权基础进行主张与举证'},{id:'defendant',label:'被告代理人',desc:'围绕抗辩事由开展质证与反驳'},{id:'audience',label:'旁听席',desc:'以中立视角观测双方论证结构'}] as const).map(r => (
              <div key={r.id} onClick={() => setUserRole(r.id)} className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${userRole===r.id?'border-blue-500 bg-blue-50/50 dark:bg-blue-900/25 shadow-sm':'border-slate-100 dark:border-slate-700 hover:border-blue-200 dark:hover:border-blue-500/50 bg-white dark:bg-slate-900/80'}`}>
                <div className="font-bold text-slate-800 dark:text-slate-100 mb-1">{r.label}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{r.desc}</div>
                {userRole===r.id && <CheckCircle2 className="w-5 h-5 text-blue-600 mt-2"/>}
              </div>
            ))}
          </div>
        </section>
        <section className="bg-white dark:bg-slate-900 p-5 lg:p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
          <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4 flex items-center"><FileSearch className="w-5 h-5 mr-2 text-blue-600"/> 第三步：整理双方证据目录</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">请先选择证据类别，系统将自动生成证据名称编号（如：书证001、电子数据002）；随后补充该证据的证明对象与证明目的。</p>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {(['plaintiff','defendant'] as const).map(side => (
              <div key={side}>
                <h3 className="text-sm font-bold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
                  <span>{side==='plaintiff'?'原告':'被告'}证据清单</span>
                  <button onClick={() => addEv(side)} className="text-blue-600 hover:text-blue-700 text-xs inline-flex items-center"><Plus className="w-3 h-3 mr-1"/>添加</button>
                </h3>
                <div className="space-y-3">
                  {evidence[side].map(ev => (
                    <div key={ev.id} className="rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-3">
                      <div className="flex justify-end mb-2">
                        <button onClick={() => delEv(side,ev.id)} className="text-slate-300 hover:text-red-400 transition"><Trash2 className="w-4 h-4"/></button>
                      </div>
                      <div className="grid grid-cols-[1fr_auto] gap-2 mb-2">
                        <select
                          value={extractEvidenceCategory(ev.category)}
                          onChange={e => {
                            const selectedCategory = e.target.value;
                            const sameCategoryCount = evidence[side]
                              .filter(item => item.id !== ev.id && extractEvidenceCategory(item.category) === selectedCategory)
                              .length;
                            updEv(side, ev.id, { category: buildEvidenceName(selectedCategory, sameCategoryCount + 1) });
                          }}
                          className="w-full text-sm p-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none transition"
                        >
                          {EVIDENCE_CATEGORIES.map(cat => (
                            <option key={cat} value={cat}>{cat}</option>
                          ))}
                        </select>
                        <div className="min-w-[84px] text-center text-xs text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-2.5 font-medium">
                          {ev.category.match(/\d{3}$/)?.[0] || '001'}
                        </div>
                      </div>
                      <textarea value={ev.content} rows={3} placeholder="证据的具体内容与证明目的..." onChange={e => updEv(side,ev.id,{ content: e.target.value })} className="w-full text-sm p-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none resize-y transition"/>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
        <section className="bg-white dark:bg-slate-900 p-5 lg:p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
          <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-4 flex items-center"><Settings2 className="w-5 h-5 mr-2 text-blue-600"/> 第四步：设定原告/被告/法官风格</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {userRole !== 'plaintiff' && (
              <div>
                <label className="text-sm font-medium text-slate-700 dark:text-slate-200 block mb-2">原告风格</label>
                <select value={aiPersonas.plaintiff} onChange={e => setAiPersonas({ ...aiPersonas, plaintiff: e.target.value })} className="w-full p-2.5 text-sm border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
                  {PARTY_STYLES.map(s => <option key={s}>{s}</option>)}
                </select>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">当前：{PARTY_STYLE_DESC[aiPersonas.plaintiff]}</p>
              </div>
            )}

            {userRole !== 'defendant' && (
              <div>
                <label className="text-sm font-medium text-slate-700 dark:text-slate-200 block mb-2">被告风格</label>
                <select value={aiPersonas.defendant} onChange={e => setAiPersonas({ ...aiPersonas, defendant: e.target.value })} className="w-full p-2.5 text-sm border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
                  {PARTY_STYLES.map(s => <option key={s}>{s}</option>)}
                </select>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">当前：{PARTY_STYLE_DESC[aiPersonas.defendant]}</p>
              </div>
            )}

            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-200 block mb-2">法官风格</label>
              <select value={aiPersonas.judge} onChange={e => setAiPersonas({...aiPersonas,judge:e.target.value})} className="w-full p-2.5 text-sm border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-1 focus:ring-blue-500 outline-none bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100">
                {JUDGE_STYLES.map(s=><option key={s}>{s}</option>)}
              </select>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">当前：{JUDGE_STYLE_DESC[aiPersonas.judge]}</p>
            </div>
          </div>
        </section>
        <div className="text-center pt-2 pb-0">
          <button onClick={onStart} disabled={!caseDesc.trim()} className={`w-full sm:w-auto min-w-[280px] px-8 py-3.5 rounded-xl font-bold text-base shadow-lg transition-all inline-flex items-center justify-center ${caseDesc.trim()?'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-xl hover:-translate-y-0.5':'bg-slate-200 text-slate-400 dark:text-slate-500 cursor-not-allowed'}`}>
            <Gavel className="w-5 h-5 mr-2"/> 完成配置并进入庭审
          </button>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-3">建议先补全事实与证据，再开始推演，以获得更稳定的裁判分析结果。</p>
        </div>
      </div>
    </div>
  );
}

function FullCaseLibraryModal({ onClose, onSelect }: { onClose: () => void; onSelect: (text: string) => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[3px]"/>
      <div
        className="relative w-full max-w-[900px] max-h-[85vh] flex flex-col bg-white dark:bg-slate-900 rounded-[24px] shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 shrink-0">
          <div className="flex items-center gap-3">
            <Library className="w-4 h-4 text-blue-600"/>
            <h2 className="text-[15px] font-bold text-slate-900">案情示例库</h2>
            <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-800/80 px-2 py-0.5 rounded-full">{CASE_EXAMPLES.length} 个常见示例</span>
          </div>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 dark:bg-slate-800/80 text-slate-400 dark:text-slate-500 transition-colors"><X className="w-4 h-4"/></button>
        </div>
        <div className="overflow-y-auto p-5">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {CASE_EXAMPLES.map((item, idx) => (
              <button
                key={`${item.label}-${idx}`}
                onClick={() => { onSelect(item.text); onClose(); }}
                className="group text-left bg-slate-50 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-900/30 border border-slate-100 hover:border-blue-200 rounded-[16px] p-4 transition-all duration-200 active:scale-[0.98]"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[13px] font-bold text-slate-800 dark:text-slate-100 group-hover:text-blue-700 transition-colors">{item.label}</span>
                  <ArrowUpRight className="w-3 h-3 ml-auto text-slate-300 opacity-0 group-hover:opacity-100 group-hover:text-blue-500 transition-all"/>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed group-hover:text-blue-700/70 transition-colors">
                  “{item.text.slice(0, 64)}...”
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ResizableLeftSidebar({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  const [width, setWidth] = React.useState(288);
  const dragging = React.useRef(false);
  const startX = React.useRef(0);
  const startW = React.useRef(0);

  const onMouseDown = (e: React.MouseEvent) => {
    dragging.current = true;
    startX.current = e.clientX;
    startW.current = width;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  React.useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const delta = e.clientX - startX.current;
      setWidth(Math.min(600, Math.max(200, startW.current + delta)));
    };
    const onUp = () => {
      dragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, []);

  return (
    <aside
      style={{ width }}
      className="relative bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700 hidden lg:flex flex-col shrink-0 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-2 shrink-0">
        <span className="text-xs font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">庭审辅助面板</span>
        <button onClick={onClose} className="p-1.5 rounded-md text-slate-400 dark:text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition" title="收起左侧栏">
          <PanelLeftClose className="w-4 h-4"/>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 pb-4 flex flex-col gap-4 min-h-0">
        {children}
      </div>
      {/* Drag handle on right edge */}
      <div
        onMouseDown={onMouseDown}
        className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-blue-400/40 transition-colors z-10 group"
      >
        <div className="absolute right-0.5 top-1/2 -translate-y-1/2 w-0.5 h-8 bg-slate-300 dark:bg-slate-600 group-hover:bg-blue-500 rounded-full transition-colors" />
      </div>
    </aside>
  );
}

function ResizableSidebar({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  const [width, setWidth] = React.useState(288);
  const dragging = React.useRef(false);
  const startX = React.useRef(0);
  const startW = React.useRef(0);

  const onMouseDown = (e: React.MouseEvent) => {
    dragging.current = true;
    startX.current = e.clientX;
    startW.current = width;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  React.useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const delta = startX.current - e.clientX;
      setWidth(Math.min(600, Math.max(220, startW.current + delta)));
    };
    const onUp = () => {
      dragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, []);

  return (
    <aside
      style={{ width }}
      className="relative bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 hidden xl:flex flex-col gap-4 shrink-0 overflow-hidden"
    >
      {/* Drag handle */}
      <div
        onMouseDown={onMouseDown}
        className="absolute left-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-blue-400/40 transition-colors z-10 group"
      >
        <div className="absolute left-0.5 top-1/2 -translate-y-1/2 w-0.5 h-8 bg-slate-300 dark:bg-slate-600 group-hover:bg-blue-500 rounded-full transition-colors" />
      </div>
      {/* Header with close */}
      <div className="flex items-center justify-between px-4 pt-4 shrink-0">
        <span className="text-xs font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">庭审辅助面板</span>
        <button onClick={onClose} className="p-1.5 rounded-md text-slate-400 dark:text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition" title="收起右侧栏">
          <PanelRightClose className="w-4 h-4"/>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 pb-4 flex flex-col gap-4 min-h-0">
        {children}
      </div>
    </aside>
  );
}

function LiveView(props: {
  caseDesc: string; userRole: UserRole; chatHistory: ChatMsg[];
  chatEndRef: React.RefObject<HTMLDivElement>; isStreaming: boolean;
  scores: { statute: number; logic: number; jury: number };
  inputText: string; setInputText: (v: string) => void;
  evidence: { plaintiff: EvidenceItem[]; defendant: EvidenceItem[] };
  onSpeak: () => void; onBack: () => void; onEndReview: () => void;
  leftSidebarOpen: boolean; rightSidebarOpen: boolean;
  onToggleLeftSidebar: () => void; onToggleRightSidebar: () => void;
  onJumpToMessage: (msgId: string) => void;
  evidenceRefs: EvidenceRefItem[];
  lawRefs: LawRefItem[];
  activeEvidenceId?: string | null;
  activeLawId?: string | null;
  onReferenceHover: (type: '证据' | '法条', value: string) => void;
  onReferenceLeave: () => void;
  onReferenceClick: (type: '证据' | '法条', value: string) => void;
  resolveRefDetail: (type: '证据' | '法条', value: string) => string | undefined;
}) {
  const { caseDesc, userRole, chatHistory, chatEndRef, isStreaming, scores, inputText, setInputText, evidence, onSpeak, onBack, onEndReview, leftSidebarOpen, rightSidebarOpen, onToggleLeftSidebar, onToggleRightSidebar, onJumpToMessage, evidenceRefs, lawRefs, activeEvidenceId, activeLawId, onReferenceHover, onReferenceLeave, onReferenceClick, resolveRefDetail } = props;

  const stageMessageMap = new Map<TrialStage, ChatMsg>();
  let currentStage: TrialStage = '开庭准备';
  chatHistory.forEach((m) => {
    if (m.role !== 'judge') return;
    const stage = detectTrialStage(m.content);
    if (!stage) return;
    currentStage = stage;
    stageMessageMap.set(stage, m);
  });
  const currentStageIndex = TRIAL_STAGES.indexOf(currentStage);

  const normalizeParty = (raw?: string, title?: string, content?: string): 'plaintiff' | 'defendant' | 'both' => {
    const src = `${raw || ''} ${(title || '')} ${(content || '')}`.toLowerCase();
    const hasPlaintiff = /plaintiff|原告|申请人|上诉人/.test(src);
    const hasDefendant = /defendant|被告|被申请人|被上诉人/.test(src);
    if (hasPlaintiff && hasDefendant) return 'both';
    if (hasPlaintiff) return 'plaintiff';
    if (hasDefendant) return 'defendant';
    if (raw === 'both' || raw === '双方') return 'both';
    return 'both';
  };

  const groupedEvidence = {
    plaintiff: evidenceRefs.filter(e => {
      const p = normalizeParty(e.party, e.title, e.content);
      return p === 'plaintiff' || p === 'both';
    }),
    defendant: evidenceRefs.filter(e => {
      const p = normalizeParty(e.party, e.title, e.content);
      return p === 'defendant' || p === 'both';
    }),
  };

  const groupedLaws = {
    plaintiff: lawRefs.filter(l => {
      const p = normalizeParty(l.party, l.title, l.content);
      return p === 'plaintiff' || p === 'both';
    }),
    defendant: lawRefs.filter(l => {
      const p = normalizeParty(l.party, l.title, l.content);
      return p === 'defendant' || p === 'both';
    }),
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-50 dark:bg-slate-800 overflow-hidden">
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 px-5 lg:px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center">
          <button onClick={onBack} className="mr-4 text-slate-400 dark:text-slate-500 hover:text-blue-600 transition"><ArrowLeft className="w-5 h-5"/></button>
          <div>
            <h2 className="text-base font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
              {caseDesc.slice(0,28)}{caseDesc.length>28?'...':''}
              <span className={`px-2 py-0.5 text-xs rounded border inline-flex items-center gap-1 ${isStreaming?'bg-red-50 text-red-600 border-red-100':'bg-green-50 text-green-600 border-green-100'}`}>
                {isStreaming ? '正在开庭' : '庭审结束'}
                <span className="text-sm leading-none">{isStreaming ? '🔴' : '🟢'}</span>
              </span>
            </h2>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">当前身份：<strong className="text-blue-600">{userRole==='defendant'?'被告代理人':userRole==='plaintiff'?'原告代理人':'旁听席'}</strong>&nbsp;|&nbsp;<strong className="text-blue-600">{currentStage}</strong></div>
          </div>
        </div>
        <button onClick={onEndReview} className="text-sm flex items-center text-blue-600 font-medium hover:bg-blue-50 dark:hover:bg-blue-900/30 px-4 py-2 rounded-lg transition"><Award className="w-4 h-4 mr-1"/> 终止审理并生成复盘</button>
      </header>
      <div className="flex-1 flex overflow-hidden">
        {leftSidebarOpen ? (
          <ResizableLeftSidebar onClose={onToggleLeftSidebar}>
            {/* 证据审查面板 */}
            <div className="shrink-0">
              <h3 className="text-xs font-bold text-slate-600 dark:text-slate-300 flex items-center mb-3"><FileSearch className="w-4 h-4 mr-1.5 text-blue-500"/>证据审查面板</h3>
              <div className="grid grid-cols-2 gap-2">
                {(['plaintiff','defendant'] as const).map(side => {
                  const evList = evidence[side].filter(e => e.category || e.content);
                  return (
                    <div key={side}>
                      <div className={`text-[10px] font-black uppercase tracking-wider mb-1.5 ${side==='plaintiff'?'text-blue-500':'text-red-500'}`}>
                        {side==='plaintiff'?'原告证据':'被告证据'}
                      </div>
                      <div className="space-y-1.5">
                        {evList.length===0 && <div className="text-[10px] text-slate-400 dark:text-slate-500">暂无</div>}
                        {evList.map((ev,i) => (
                          <div key={ev.id} className="bg-slate-50 dark:bg-slate-800 p-2 rounded-lg border border-slate-100 dark:border-slate-700">
                            <div className="text-[11px] font-semibold text-slate-700 dark:text-slate-200 truncate mb-1">
                              {side==='plaintiff'?'原告':'被告'}证{i+1}：{ev.category||'未命名'}
                            </div>
                            {ev.content && <p className="text-[10px] text-slate-500 dark:text-slate-400 mb-1.5 line-clamp-2">{ev.content}</p>}
                            <div className="flex flex-wrap gap-1">
                              <span className="px-1.5 py-0.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded text-[9px] border border-green-200 dark:border-green-700/40">真实性✓</span>
                              <span className="px-1.5 py-0.5 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 rounded text-[9px] border border-amber-200 dark:border-amber-700/40">关联性存疑</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 审理进程 */}
            <div className="flex-1 min-h-0 flex flex-col">
              <h3 className="text-xs font-bold text-slate-600 dark:text-slate-300 flex items-center mb-3 shrink-0"><Clock className="w-4 h-4 mr-1.5 text-blue-500"/>审理进程</h3>
              <div className="relative border-l-2 border-slate-100 dark:border-slate-700 ml-2 space-y-3 pl-3 overflow-y-auto flex-1">
                {TRIAL_STAGES.map((stage, i) => {
                  const msg = stageMessageMap.get(stage);
                  const reached = i <= currentStageIndex;
                  const active = i === currentStageIndex;
                  return (
                    <div key={stage} className="relative">
                      <div className={`absolute -left-[17px] top-1 w-2.5 h-2.5 rounded-full border-2 border-white dark:border-slate-900 ${active ? 'bg-blue-500' : reached ? 'bg-amber-400' : 'bg-slate-300 dark:bg-slate-600'}`}/>
                      <button
                        type="button"
                        disabled={!msg?.msgId}
                        onClick={() => msg?.msgId && onJumpToMessage(msg.msgId)}
                        className={`text-left w-full text-xs transition ${msg?.msgId ? 'text-slate-700 dark:text-slate-200 hover:text-blue-600 cursor-pointer' : 'text-slate-400 dark:text-slate-500 cursor-not-allowed'}`}
                      >
                        <span className={`font-semibold ${active ? 'text-blue-600' : ''}`}>{stage}</span>
                        {active && <span className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300 text-[9px] font-bold">进行中</span>}
                        <span className="block mt-0.5 line-clamp-2 text-[10px]">
                          {msg ? `${toPlainDisplayText(msg.content).slice(0,42)}${toPlainDisplayText(msg.content).length>42?'...':''}` : '等待该阶段...'}
                        </span>
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </ResizableLeftSidebar>
        ) : (
          <div className="hidden lg:flex w-11 bg-white dark:bg-slate-900 border-r border-slate-200 items-start justify-center pt-4 shrink-0">
            <button onClick={onToggleLeftSidebar} className="p-1.5 rounded-md text-slate-400 dark:text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition" title="展开左侧栏">
              <PanelLeftOpen className="w-4 h-4"/>
            </button>
          </div>
        )}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4 lg:p-5 space-y-4 bg-slate-50 dark:bg-slate-800/50 dark:bg-slate-900/40">
            {chatHistory.map((msg,idx) => (
              <div id={msg.msgId ? `court-msg-${msg.msgId}` : undefined} key={msg.msgId || idx} className={`flex flex-col ${msg.role==='system'||msg.role==='judge'?'items-center':msg.role==='plaintiff'?'items-start':'items-end'}`}>
                {msg.role==='system' ? (
                  <div className="text-[10px] text-slate-400 dark:text-slate-500 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800/80">{renderReadableMessage(msg.content, { onRefHover: onReferenceHover, onRefLeave: onReferenceLeave, onRefClick: onReferenceClick, resolveRefDetail })}</div>
                ) : msg.role==='judge' ? (
                  <div className="max-w-lg flex flex-col items-center">
                    <span className="text-xs text-slate-400 dark:text-slate-500 mb-1 flex items-center"><Gavel className="w-3 h-3 mr-1"/>{msg.name}</span>
                    <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${msg.isFollowUp?'bg-amber-50 text-amber-900 border border-amber-200':'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700'}`}>
                      {msg.isFollowUp && <span className="font-bold text-amber-700 mr-2">[法官追问]</span>}{renderReadableMessage(msg.content, { onRefHover: onReferenceHover, onRefLeave: onReferenceLeave, onRefClick: onReferenceClick, resolveRefDetail })}
                    </div>
                  </div>
                ) : (
                  <div className="max-w-lg flex flex-col">
                    <span className={`text-xs text-slate-400 dark:text-slate-500 mb-1 ${msg.role==='user'||msg.role==='defendant'?'text-right mr-1':'ml-1'}`}>{msg.name}</span>
                    <div className={`px-4 py-3 rounded-2xl text-sm shadow-sm leading-relaxed ${msg.role==='user'?'bg-blue-600 text-white rounded-tr-sm':'bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-slate-700 rounded-tl-sm'}`}>{msg.role === 'user' ? msg.content : renderReadableMessage(msg.content, { onRefHover: onReferenceHover, onRefLeave: onReferenceLeave, onRefClick: onReferenceClick, resolveRefDetail })}</div>
                  </div>
                )}
              </div>
            ))}
            {isStreaming && <div className="flex justify-center"><span className="text-xs text-amber-600 px-3 py-1.5 bg-amber-50 rounded-full font-medium flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping inline-block mr-1"/>AI庭审进行中...</span></div>}
            {!isStreaming && userRole!=='audience' && chatHistory.length>0 && (
              <div className="flex flex-col items-end pt-2">
                <span className="text-xs text-blue-600 mb-1 font-bold animate-pulse inline-flex items-center gap-1"><span className="text-base leading-none">🔵</span> 当前轮次：请提交陈述意见</span>
                <div className="border border-blue-200 bg-blue-50/50 w-full max-w-lg h-10 rounded-2xl border-dashed flex items-center justify-center text-blue-400 text-xs">请在下方输入框提交陈述要点...</div>
              </div>
            )}
            <div ref={chatEndRef}/>
          </div>
          {userRole!=='audience' && (
            <div className="p-4 bg-white dark:bg-slate-900 border-t border-slate-200 shrink-0">
              <div className="mb-2 flex flex-wrap gap-2">
                <button className="text-xs bg-blue-50 text-blue-600 px-3 py-1.5 rounded-full border border-blue-100 flex items-center hover:bg-blue-100 transition"><Zap className="w-3.5 h-3.5 mr-1"/> 论证措辞优化</button>
                <button className="text-xs bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700 flex items-center hover:bg-slate-100 dark:hover:bg-slate-800 dark:bg-slate-800/80 transition"><Scale className="w-3 h-3 mr-1"/> 法条检索</button>
                <button className="text-xs bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700 flex items-center hover:bg-slate-100 dark:hover:bg-slate-800 dark:bg-slate-800/80 transition"><Shield className="w-3 h-3 mr-1"/> 论证薄弱点分析</button>
              </div>
              <div className="flex items-end space-x-3">
                <div className="flex-1 bg-white dark:bg-slate-900 border border-slate-300 rounded-xl focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition-all shadow-sm overflow-hidden">
                  <textarea rows={3} className="w-full bg-transparent p-3 text-sm text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 outline-none resize-none" placeholder="在此输入陈述意见，Enter 发送，Shift+Enter 换行..." value={inputText} onChange={e => setInputText(e.target.value)} onKeyDown={e => {if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();onSpeak();}}}/>
                </div>
                <button onClick={onSpeak} disabled={!inputText.trim()} className={`h-[76px] px-6 rounded-xl font-medium transition flex items-center shadow-md ${inputText.trim()?'bg-blue-600 text-white hover:bg-blue-700':'bg-slate-100 dark:bg-slate-800/80 text-slate-300 cursor-not-allowed'}`}><MessageSquare className="w-5 h-5 mr-2"/>提交陈述</button>
              </div>
            </div>
          )}
        </main>
        {rightSidebarOpen ? (
          <ResizableSidebar onClose={onToggleRightSidebar}>
            {/* AI 表现评估 */}
            <div className="shrink-0">
              <h3 className="text-xs font-bold text-slate-600 dark:text-slate-300 flex items-center mb-2"><Target className="w-4 h-4 mr-1.5 text-blue-500"/>AI表现评估</h3>
              <div className="bg-slate-50 dark:bg-slate-800 p-3 rounded-xl border border-slate-100 dark:border-slate-700 space-y-3">
                {([{ label: '法条适配度', val: scores.statute, color: 'bg-indigo-500', icon: '⚖️' }, { label: '逻辑严密性', val: scores.logic, color: 'bg-blue-500', icon: '🧠' }]).map(({ label, val, color, icon }) => (
                  <div key={label}>
                    <div className="flex justify-between text-xs mb-1 items-center">
                      <span className="text-slate-600 dark:text-slate-300 flex items-center gap-1"><span>{icon}</span>{label}</span>
                      <span className={`font-bold tabular-nums ${val > 0 ? 'text-blue-600' : 'text-slate-400 dark:text-slate-500'}`}>{val > 0 ? `${val}%` : '待评估'}</span>
                    </div>
                    <div className="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div className={`h-full ${color} rounded-full transition-all duration-700 ease-out`} style={{ width: `${val}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            {/* 陪审团预测 */}
            <div className="shrink-0">
              <h3 className="text-xs font-bold text-slate-600 dark:text-slate-300 flex items-center mb-2"><Users className="w-4 h-4 mr-1.5 text-blue-500"/>陪审团预测</h3>
              <div className="bg-slate-50 dark:bg-slate-800 p-3 rounded-xl border border-slate-100 dark:border-slate-700 flex items-center gap-3">
                <div className="relative w-14 h-14 shrink-0">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 56 56">
                    <circle cx="28" cy="28" r="22" stroke="currentColor" strokeOpacity="0.1" strokeWidth="5" fill="transparent" className="text-slate-400"/>
                    <circle cx="28" cy="28" r="22"
                      stroke={scores.jury >= 80 ? '#22c55e' : scores.jury >= 60 ? '#3b82f6' : scores.jury > 0 ? '#f59e0b' : '#cbd5e1'}
                      strokeWidth="5" fill="transparent" strokeLinecap="round"
                      strokeDasharray={`${2 * Math.PI * 22}`}
                      strokeDashoffset={`${2 * Math.PI * 22 * (1 - scores.jury / 100)}`}
                      style={{ transition: 'stroke-dashoffset 0.8s ease' }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className={`text-sm font-black ${scores.jury > 0 ? 'text-slate-800 dark:text-slate-100' : 'text-slate-300 dark:text-slate-600'}`}>{scores.jury > 0 ? scores.jury : '--'}</span>
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className={`text-sm font-bold truncate ${scores.jury >= 80 ? 'text-green-600' : scores.jury >= 60 ? 'text-blue-600' : scores.jury > 0 ? 'text-amber-600' : 'text-slate-400 dark:text-slate-500'}`}>
                    {scores.jury >= 80 ? '说服力极强' : scores.jury >= 60 ? '论证有力' : scores.jury >= 40 ? '初步成型' : scores.jury > 0 ? '论证薄弱' : '等待首轮发言...'}
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">{scores.jury > 0 ? '综合法条与逻辑预测' : '庭审开始后实时更新'}</div>
                </div>
              </div>
            </div>

            {/* 证据 — 双列 */}
            <div className="flex-1 min-h-0 flex flex-col">
              <h3 className="text-xs font-bold text-slate-600 dark:text-slate-300 flex items-center mb-2 shrink-0"><FileSearch className="w-4 h-4 mr-1.5 text-emerald-500"/>证据清单</h3>
              <div className="grid grid-cols-2 gap-2 overflow-y-auto flex-1">
                {(['plaintiff','defendant'] as const).map(side => {
                  const sideEvidence = side === 'plaintiff'
                    ? evidenceRefs.filter(e => e.party === 'plaintiff' || !e.party)
                    : evidenceRefs.filter(e => e.party === 'defendant');
                  return (
                    <div key={side}>
                      <div className={`text-[10px] font-black uppercase tracking-wider mb-1.5 ${side==='plaintiff'?'text-blue-500':'text-red-500'}`}>{side==='plaintiff'?'原告':'被告'}</div>
                      <div className="space-y-1.5">
                        {sideEvidence.length===0 && <div className="text-[10px] text-slate-400 dark:text-slate-500">暂无</div>}
                        {sideEvidence.map(ev => {
                          const active = activeEvidenceId===ev.id;
                          return (
                            <div id={`evidence-card-${ev.id}`} key={ev.id} className={`rounded-lg border p-1.5 transition cursor-pointer ${active?'border-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 shadow-sm':'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-emerald-300'}`}>
                              <div className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-300 truncate">{ev.title||ev.id}</div>
                              <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">{toPlainDisplayText(ev.content)}</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 法条 — 双列 */}
            <div className="flex-1 min-h-0 flex flex-col">
              <h3 className="text-xs font-bold text-slate-600 dark:text-slate-300 flex items-center mb-2 shrink-0"><Scale className="w-4 h-4 mr-1.5 text-indigo-500"/>法条来源</h3>
              <div className="grid grid-cols-2 gap-2 overflow-y-auto flex-1">
                {(['plaintiff','defendant'] as const).map(side => {
                  const sideLaws = side === 'plaintiff'
                    ? lawRefs.filter(l => l.party === 'plaintiff' || !l.party)
                    : lawRefs.filter(l => l.party === 'defendant');
                  return (
                    <div key={side}>
                      <div className={`text-[10px] font-black uppercase tracking-wider mb-1.5 ${side==='plaintiff'?'text-blue-500':'text-red-500'}`}>{side==='plaintiff'?'原告':'被告'}</div>
                      <div className="space-y-1.5">
                        {sideLaws.length===0 && <div className="text-[10px] text-slate-400 dark:text-slate-500">暂无</div>}
                        {sideLaws.map(law => {
                          const active = activeLawId===law.id;
                          return (
                            <div id={`law-card-${law.id}`} key={law.id} className={`rounded-lg border p-1.5 transition cursor-pointer ${active?'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 shadow-sm':'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-indigo-300'}`}>
                              <div className="text-[11px] font-semibold text-indigo-700 dark:text-indigo-300 truncate">{law.title||law.id}</div>
                              <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">{toPlainDisplayText(law.content)}</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 战术建议 */}
            <div className="shrink-0 bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-800/40 rounded-xl p-3">
              <h4 className="text-xs font-bold text-blue-800 dark:text-blue-300 mb-1.5 flex items-center"><Zap className="w-3.5 h-3.5 mr-1 text-orange-500"/>战术建议</h4>
              <p className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">{userRole==='defendant'?'建议核查原告证据关联性，从程序瑕疵角度提出质疑，准备替代性解释。':'建议强调证据链完整性，引用具体法条支撑主张。'}</p>
            </div>
          </ResizableSidebar>
        ) : (
          <div className="hidden xl:flex w-11 bg-white dark:bg-slate-900 border-l border-slate-200 items-start justify-center pt-4 shrink-0">
            <button onClick={onToggleRightSidebar} className="p-1.5 rounded-md text-slate-400 dark:text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition" title="展开右侧栏">
              <PanelRightOpen className="w-4 h-4"/>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function ReviewView({ reviewData, onRestart, onBackToHome }: { reviewData: ReviewData | null; onRestart: () => void; onBackToHome: () => void }) {
  const rd = reviewData;
  return (
    <div className="flex-1 bg-slate-50 dark:bg-slate-900 overflow-y-auto p-6 lg:p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center mb-2">
          <PieChart className="w-12 h-12 text-blue-600 mx-auto mb-3"/>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">庭审复盘报告</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">AI 综合双方陈述、证据与法条，生成以下完整复盘分析</p>
        </div>
        {rd && (
          <>
            {/* 胜诉概率 */}
            <section className="bg-white dark:bg-slate-900 p-5 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
              <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-4 flex items-center"><Award className="w-4 h-4 mr-2 text-blue-600"/>胜诉概率预测</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-5 text-center border border-blue-100 dark:border-blue-800">
                  <div className="text-xs font-bold text-blue-500 uppercase tracking-widest mb-2">原告胜诉率</div>
                  <div className="text-4xl font-black text-blue-600">{rd.win_probability.plaintiff}%</div>
                  <div className="mt-2 h-1.5 bg-blue-100 dark:bg-blue-800 rounded-full overflow-hidden"><div className="h-full bg-blue-500 rounded-full" style={{width:`${rd.win_probability.plaintiff}%`}}/></div>
                </div>
                <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-5 text-center border border-red-100 dark:border-red-800">
                  <div className="text-xs font-bold text-red-500 uppercase tracking-widest mb-2">被告胜诉率</div>
                  <div className="text-4xl font-black text-red-600">{rd.win_probability.defendant}%</div>
                  <div className="mt-2 h-1.5 bg-red-100 dark:bg-red-800 rounded-full overflow-hidden"><div className="h-full bg-red-500 rounded-full" style={{width:`${rd.win_probability.defendant}%`}}/></div>
                </div>
              </div>
            </section>
            {/* AI 表现评分 */}
            {rd.scores && (
              <section className="bg-white dark:bg-slate-900 p-5 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
                <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-4 flex items-center"><Target className="w-4 h-4 mr-2 text-blue-600"/>AI 庭审表现评分</h2>
                <div className="grid grid-cols-3 gap-4">
                  {([{label:'法条适配度',val:rd.scores.statute,color:'text-indigo-600',bg:'bg-indigo-500'},{label:'逻辑严密性',val:rd.scores.logic,color:'text-blue-600',bg:'bg-blue-500'},{label:'陪审团综合',val:rd.scores.jury,color:'text-green-600',bg:'bg-green-500'}]).map(({label,val,color,bg}) => (
                    <div key={label} className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4 border border-slate-100 dark:border-slate-700 text-center">
                      <div className={`text-2xl font-black ${color}`}>{val}</div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 mb-2">{label}</div>
                      <div className="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden"><div className={`h-full ${bg} rounded-full`} style={{width:`${val}%`}}/></div>
                    </div>
                  ))}
                </div>
              </section>
            )}
            {/* 裁判综述 */}
            <section className="bg-white dark:bg-slate-900 p-5 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
              <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-3 flex items-center"><Gavel className="w-4 h-4 mr-2 text-blue-600"/>裁判综述</h2>
              <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">{rd.summary}</p>
            </section>
            {/* 关键要点 */}
            {rd.keyPoints.length > 0 && (
              <section className="bg-white dark:bg-slate-900 p-5 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
                <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-3 flex items-center"><Star className="w-4 h-4 mr-2 text-blue-600"/>关键争议要点</h2>
                <ul className="space-y-2">
                  {rd.keyPoints.map((point, i) => (
                    <li key={i} className="flex items-start text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800 rounded-lg px-3 py-2">
                      <span className="text-blue-600 font-bold mr-2 shrink-0">{i + 1}.</span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {/* 证据与法条汇总 */}
            {((rd.evidenceRefs && rd.evidenceRefs.length > 0) || (rd.lawRefs && rd.lawRefs.length > 0)) && (
              <section className="bg-white dark:bg-slate-900 p-5 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
                <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-4 flex items-center"><FileSearch className="w-4 h-4 mr-2 text-blue-600"/>庭审证据与法条汇总</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {rd.evidenceRefs && rd.evidenceRefs.length > 0 && (
                    <div>
                      <h3 className="text-xs font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-2">证据清单（{rd.evidenceRefs.length} 项）</h3>
                      <div className="space-y-1.5">
                        {rd.evidenceRefs.map((ev, i) => (
                          <div key={ev.id || i} className="rounded-lg bg-emerald-50 dark:bg-emerald-900/15 border border-emerald-100 dark:border-emerald-800/40 px-3 py-2">
                            <div className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">{ev.title || ev.id}</div>
                            <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">{toPlainDisplayText(ev.content)}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {rd.lawRefs && rd.lawRefs.length > 0 && (
                    <div>
                      <h3 className="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider mb-2">引用法条（{rd.lawRefs.length} 条）</h3>
                      <div className="space-y-1.5">
                        {rd.lawRefs.map((law, i) => (
                          <div key={law.id || i} className="rounded-lg bg-indigo-50 dark:bg-indigo-900/15 border border-indigo-100 dark:border-indigo-800/40 px-3 py-2">
                            <div className="text-[11px] font-semibold text-indigo-700 dark:text-indigo-300">{law.title || law.id}</div>
                            <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">{toPlainDisplayText(law.content)}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </section>
            )}
            {/* 庭审记录摘要 */}
            {rd.transcript && rd.transcript.length > 0 && (
              <section className="bg-white dark:bg-slate-900 p-5 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
                <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-4 flex items-center"><MessageSquare className="w-4 h-4 mr-2 text-blue-600"/>庭审发言记录（{rd.transcript.length} 条）</h2>
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {rd.transcript.map((msg, i) => (
                    <div key={i} className={`rounded-xl px-4 py-3 text-sm border ${
                      msg.role==='judge' ? 'bg-amber-50 dark:bg-amber-900/15 border-amber-100 dark:border-amber-800/40 text-amber-900 dark:text-amber-200'
                      : msg.role==='plaintiff' ? 'bg-blue-50 dark:bg-blue-900/15 border-blue-100 dark:border-blue-800/40 text-blue-900 dark:text-blue-200'
                      : msg.role==='defendant' ? 'bg-red-50 dark:bg-red-900/15 border-red-100 dark:border-red-800/40 text-red-900 dark:text-red-200'
                      : 'bg-slate-50 dark:bg-slate-800 border-slate-100 dark:border-slate-700 text-slate-600 dark:text-slate-300'
                    }`}>
                      <div className="text-[10px] font-bold uppercase tracking-wider mb-1 opacity-60">{msg.name}</div>
                      <div className="text-[12px] leading-relaxed line-clamp-4">{toPlainDisplayText(msg.content)}</div>
                    </div>
                  ))}
                </div>
              </section>
            )}
            {/* 操作按钮 */}
            <div className="flex items-center justify-center gap-3 pt-2 pb-4">
              <button onClick={onBackToHome} className="px-6 py-3 rounded-xl font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition shadow-sm flex items-center">
                <ArrowLeft className="w-4 h-4 mr-2"/>返回法庭
              </button>
              <button onClick={onRestart} className="px-8 py-3 rounded-xl font-medium bg-blue-600 text-white hover:bg-blue-700 transition shadow-md flex items-center">
                <Gavel className="w-4 h-4 mr-2"/>重新审判（同一案情）
              </button>
            </div>
          </>
        )}
        {!rd && (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-slate-300 mx-auto mb-4"/>
            <p className="text-slate-500 dark:text-slate-400">暂无复盘数据</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CourtPage() {
  const [view, setView] = useState<View>('setup');
  const [caseDesc, setCaseDesc] = useState('');
  const [userRole, setUserRole] = useState<UserRole>('plaintiff');
  const [evidence, setEvidence] = useState({ plaintiff: [] as EvidenceItem[], defendant: [] as EvidenceItem[] });
  const [aiPersonas, setAiPersonas] = useState<AiPersonas>({ plaintiff: PARTY_STYLES[0], defendant: PARTY_STYLES[0], judge: JUDGE_STYLES[0] });
  const [chatHistory, setChatHistory] = useState<ChatMsg[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [scores, setScores] = useState({ statute: 0, logic: 0, jury: 0 });
  const scoreAccRef = useRef({ messages: 0, lawRefs: 0, evidenceRefs: 0, phases: new Set<string>() });
  const [inputText, setInputText] = useState('');
  const [reviewData, setReviewData] = useState<ReviewData | null>(null);
  const [templatePage, setTemplatePage] = useState(0);
  const [showCaseLibrary, setShowCaseLibrary] = useState(false);
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);
  const [rightSidebarOpen, setRightSidebarOpen] = useState(true);
  const [evidenceRefs, setEvidenceRefs] = useState<EvidenceRefItem[]>([]);
  const [lawRefs, setLawRefs] = useState<LawRefItem[]>([]);
  const [activeEvidenceId, setActiveEvidenceId] = useState<string | null>(null);
  const [activeLawId, setActiveLawId] = useState<string | null>(null);
  const visibleCaseExamples = CASE_EXAMPLES.slice(templatePage * 4, templatePage * 4 + 4);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const addEv = useCallback((side: 'plaintiff' | 'defendant') => {
    setEvidence(prev => {
      const defaultCategory = EVIDENCE_CATEGORIES[0];
      const seq = prev[side].filter(e => extractEvidenceCategory(e.category) === defaultCategory).length + 1;
      return {
        ...prev,
        [side]: [...prev[side], { id: Date.now(), category: buildEvidenceName(defaultCategory, seq), content: '' }]
      };
    });
  }, []);

  const updEv = useCallback((side: 'plaintiff' | 'defendant', id: number, patch: Partial<EvidenceItem>) => {
    setEvidence(prev => ({
      ...prev,
      [side]: prev[side].map(e => e.id === id ? { ...e, ...patch } : e)
    }));
  }, []);

  const delEv = useCallback((side: 'plaintiff' | 'defendant', id: number) => {
    setEvidence(prev => ({
      ...prev,
      [side]: prev[side].filter(e => e.id !== id)
    }));
  }, []);

  const handleStart = useCallback(async () => {
    setView('live');
    setChatHistory([{ role: 'system', name: '系统', content: '庭审即将开始...' }]);
    setIsStreaming(true);
    setScores({ statute: 0, logic: 0, jury: 0 });
    scoreAccRef.current = { messages: 0, lawRefs: 0, evidenceRefs: 0, phases: new Set<string>() };
    setEvidenceRefs([]);
    setLawRefs([]);
    setActiveEvidenceId(null);
    setActiveLawId(null);

    // 本地实时评分引擎
    const computeScores = (acc: typeof scoreAccRef.current) => {
      // 法条适配度：引用法条数 * 15，上限 95
      const statute = Math.min(95, acc.lawRefs * 15 + (acc.phases.size >= 3 ? 10 : 0));
      // 逻辑严密性：消息数 * 8 + 证据引用 * 10，上限 95
      const logic = Math.min(95, acc.messages * 8 + acc.evidenceRefs * 10);
      // 陪审团预测：综合均值略微加权
      const jury = Math.min(99, Math.round((statute * 0.45 + logic * 0.55)));
      return { statute, logic, jury };
    };

    try {
      const strategy = userRole === 'plaintiff' ? `原告代理人（${aiPersonas.plaintiff}）` : userRole === 'defendant' ? `被告代理人（${aiPersonas.defendant}）` : '旁听席';
      const humanEvidence = [
        ...evidence.plaintiff.filter(e => e.category || e.content).map(e => ({ party: 'plaintiff' as const, name: e.category, desc: e.content })),
        ...evidence.defendant.filter(e => e.category || e.content).map(e => ({ party: 'defendant' as const, name: e.category, desc: e.content }))
      ];

      await streamCourtDebate(
        {
          case_description: caseDesc,
          strategy,
          human_evidence: humanEvidence
        },
        (event: AnyCourtEvent) => {
          const mapRole = (ev: AnyCourtEvent): ChatMsg['role'] => {
            const roleKey = 'role_key' in ev ? ev.role_key : undefined;
            const role = ev.role;
            return roleKey === 'judge' || role === 'judge'
              ? 'judge'
              : roleKey === 'plaintiff' || role === 'plaintiff'
                ? 'plaintiff'
                : roleKey === 'defendant' || role === 'defendant'
                  ? 'defendant'
                  : 'system';
          };

          if (event.type === 'new_message') {
            const mappedRole = mapRole(event);
            const msgId = 'msg_id' in event ? event.msg_id : undefined;
            // 每条新消息更新消息计数和阶段
            if (mappedRole !== 'system') {
              scoreAccRef.current.messages += 1;
              const phase = 'phase' in event ? event.phase : undefined;
              if (phase) scoreAccRef.current.phases.add(phase);
              setScores(computeScores(scoreAccRef.current));
            }
            setChatHistory(prev => [
              ...prev,
              {
                msgId: msgId || `msg_${Date.now()}_${prev.length}`,
                role: mappedRole,
                name: event.role || '系统',
                content: '',
              },
            ]);
          } else if (event.type === 'chunk') {
            const chunkText = event.content || '';
            if (!chunkText) return;

            setChatHistory(prev => {
              const msgId = 'msg_id' in event ? event.msg_id : undefined;
              const next = [...prev];

              if (msgId) {
                for (let i = next.length - 1; i >= 0; i -= 1) {
                  if (next[i].msgId === msgId) {
                    next[i] = { ...next[i], content: (next[i].content || '') + chunkText };
                    return next;
                  }
                }
              }

              const mappedRole = mapRole(event);
              if (next.length > 0 && next[next.length - 1].role === mappedRole) {
                const last = next[next.length - 1];
                next[next.length - 1] = { ...last, content: (last.content || '') + chunkText };
                return next;
              }

              next.push({
                msgId: msgId || `msg_${Date.now()}_${next.length}`,
                role: mappedRole,
                name: event.role || '系统',
                content: chunkText,
              });
              return next;
            });
          } else if (event.type === 'evidence_list') {
            if (Array.isArray(event.evidence_list)) {
              setEvidenceRefs(event.evidence_list);
              scoreAccRef.current.evidenceRefs = event.evidence_list.length;
              setScores(computeScores(scoreAccRef.current));
            }
          } else if (event.type === 'law_list') {
            if (Array.isArray(event.law_list)) {
              setLawRefs(event.law_list);
              scoreAccRef.current.lawRefs = event.law_list.length;
              setScores(computeScores(scoreAccRef.current));
            }
          } else if (event.type === 'evidence_reference') {
            if (event.evidence_id) {
              setActiveEvidenceId(event.evidence_id);
              scoreAccRef.current.evidenceRefs += 1;
              setScores(computeScores(scoreAccRef.current));
            }
          } else if (event.type === 'law_reference') {
            if (event.law_id) {
              setActiveLawId(event.law_id);
              scoreAccRef.current.lawRefs += 1;
              setScores(computeScores(scoreAccRef.current));
            }
          } else if (event.type === 'result') {
            if (event.result?.evidence_list) setEvidenceRefs(event.result.evidence_list);
            if (event.result?.law_list) setLawRefs(event.result.law_list);
            if (event.result?.verdict) {
              setChatHistory(prev => [...prev, {
                msgId: `msg_${Date.now()}_${prev.length}`,
                role: 'judge',
                name: '审判长',
                content: toPlainDisplayText(event.result?.verdict || '本轮庭审阶段结束')
              }]);
            }
            if (event.result?.plaintiff_win_rate !== undefined && event.result?.defendant_win_rate !== undefined) {
              setReviewData(prev => ({
                win_probability: {
                  plaintiff: event.result!.plaintiff_win_rate!,
                  defendant: event.result!.defendant_win_rate!
                },
                summary: toPlainDisplayText(event.result?.verdict || '庭审推演已完成'),
                keyPoints: [],
                transcript: prev?.transcript,
                evidenceRefs: event.result?.evidence_list,
                lawRefs: event.result?.law_list,
                scores: scoreAccRef.current ? {
                  statute: Math.min(95, scoreAccRef.current.lawRefs * 15 + (scoreAccRef.current.phases.size >= 3 ? 10 : 0)),
                  logic: Math.min(95, scoreAccRef.current.messages * 8 + scoreAccRef.current.evidenceRefs * 10),
                  jury: 0,
                } : undefined,
              }));
            }
          }
        }
      );
    } catch (err) {
      setChatHistory(prev => [...prev, {
        role: 'system',
        name: '系统',
        content: `错误: ${err instanceof Error ? err.message : '未知错误'}`
      }]);
    } finally {
      setIsStreaming(false);
    }
  }, [caseDesc, userRole, evidence, aiPersonas]);

  const handleSpeak = useCallback(() => {
    if (!inputText.trim()) return;
    setChatHistory(prev => [...prev, {
      role: 'user',
      name: userRole === 'plaintiff' ? '原告代理人' : '被告代理人',
      content: inputText
    }]);
    setInputText('');
  }, [inputText, userRole]);

  const handleShuffleCaseExamples = useCallback(() => {
    setTemplatePage(p => (p + 1) % Math.ceil(CASE_EXAMPLES.length / 4));
  }, []);

  const handleEndReview = useCallback(() => {
    // 生成复盘时把完整 transcript 存入 reviewData
    setChatHistory(prev => {
      setReviewData(rd => rd ? { ...rd, transcript: prev } : {
        win_probability: { plaintiff: 50, defendant: 50 },
        summary: '庭审已结束，等待 AI 综合评估...',
        keyPoints: [],
        transcript: prev,
        evidenceRefs: [],
        lawRefs: [],
      });
      return prev;
    });
    setView('review');
  }, []);

  const handleReset = useCallback(() => {
    // 返回法庭主界面，清空所有状态
    setView('setup');
    setCaseDesc('');
    setEvidence({ plaintiff: [], defendant: [] });
    setChatHistory([]);
    setReviewData(null);
    setScores({ statute: 0, logic: 0, jury: 0 });
    setEvidenceRefs([]);
    setLawRefs([]);
    setActiveEvidenceId(null);
    setActiveLawId(null);
  }, []);

  // 重新审判：保留案情/身份/证据/风格，重新开庭
  const handleRestart = useCallback(() => {
    setChatHistory([]);
    setReviewData(null);
    setScores({ statute: 0, logic: 0, jury: 0 });
    setEvidenceRefs([]);
    setLawRefs([]);
    setActiveEvidenceId(null);
    setActiveLawId(null);
    // handleStart 依赖 view==='live' 之外的状态，直接调用即可
    setView('live');
    // 用 setTimeout 让 React 先完成 state 更新再触发庭审
    setTimeout(() => { handleStart(); }, 0);
  }, [handleStart]);

  const handleJumpToMessage = useCallback((msgId: string) => {
    const el = document.getElementById(`court-msg-${msgId}`);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const resolveRefDetail = useCallback((type: '证据' | '法条', value: string): string | undefined => {
    if (type === '法条') {
      const law = lawRefs.find(l => l.id === value || l.title === value || l.title?.includes(value));
      return law ? `${law.title}\n${law.content}` : undefined;
    }
    const ev = evidenceRefs.find(e => e.id === value || e.title === value || e.title?.includes(value));
    return ev ? `${ev.title}\n${ev.content}` : undefined;
  }, [lawRefs, evidenceRefs]);

  const handleReferenceHover = useCallback((type: '证据' | '法条', value: string) => {
    if (type === '法条') {
      const law = lawRefs.find(l => l.id === value || l.title === value || l.title?.includes(value));
      setActiveLawId(law?.id || value);
    } else {
      const ev = evidenceRefs.find(e => e.id === value || e.title === value || e.title?.includes(value));
      setActiveEvidenceId(ev?.id || value);
    }
  }, [lawRefs, evidenceRefs]);

  const handleReferenceLeave = useCallback(() => {
    setActiveEvidenceId(null);
    setActiveLawId(null);
  }, []);

  const handleReferenceClick = useCallback((type: '证据' | '法条', value: string) => {
    if (type === '法条') {
      const law = lawRefs.find(l => l.id === value || l.title === value || l.title?.includes(value));
      const targetId = law?.id || value;
      setActiveLawId(targetId);
      const el = document.getElementById(`law-card-${targetId}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    const ev = evidenceRefs.find(e => e.id === value || e.title === value || e.title?.includes(value));
    const targetId = ev?.id || value;
    setActiveEvidenceId(targetId);
    const el = document.getElementById(`evidence-card-${targetId}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [lawRefs, evidenceRefs]);

  return (
    <div className="h-screen flex flex-col bg-slate-50 dark:bg-slate-800 dark:bg-slate-950">
      {view === 'setup' && (
        <SetupView
          caseDesc={caseDesc}
          setCaseDesc={setCaseDesc}
          userRole={userRole}
          setUserRole={setUserRole}
          evidence={evidence}
          addEv={addEv}
          updEv={updEv}
          delEv={delEv}
          aiPersonas={aiPersonas}
          setAiPersonas={setAiPersonas}
          onStart={handleStart}
          visibleCaseExamples={visibleCaseExamples}
          onShuffleCaseExamples={handleShuffleCaseExamples}
          onOpenCaseLibrary={() => setShowCaseLibrary(true)}
        />
      )}
      {view === 'live' && (
        <LiveView
          caseDesc={caseDesc}
          userRole={userRole}
          chatHistory={chatHistory}
          chatEndRef={chatEndRef}
          isStreaming={isStreaming}
          scores={scores}
          inputText={inputText}
          setInputText={setInputText}
          evidence={evidence}
          onSpeak={handleSpeak}
          onBack={() => setView('setup')}
          onEndReview={handleEndReview}
          leftSidebarOpen={leftSidebarOpen}
          rightSidebarOpen={rightSidebarOpen}
          onToggleLeftSidebar={() => setLeftSidebarOpen(v => !v)}
          onToggleRightSidebar={() => setRightSidebarOpen(v => !v)}
          onJumpToMessage={handleJumpToMessage}
          evidenceRefs={evidenceRefs}
          lawRefs={lawRefs}
          activeEvidenceId={activeEvidenceId}
          activeLawId={activeLawId}
          onReferenceHover={handleReferenceHover}
          onReferenceLeave={handleReferenceLeave}
          onReferenceClick={handleReferenceClick}
          resolveRefDetail={resolveRefDetail}
        />
      )}
      {view === 'review' && (
        <ReviewView
          reviewData={reviewData}
          onRestart={handleRestart}
          onBackToHome={handleReset}
        />
      )}
      {showCaseLibrary && (
        <FullCaseLibraryModal
          onClose={() => setShowCaseLibrary(false)}
          onSelect={(text) => setCaseDesc(text)}
        />
      )}
    </div>
  );
}