'use client';

import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, Briefcase, Gavel, TrendingUp,
  Scale, Car, UserRound, HeartCrack,
  ShieldCheck, Stamp, Coins, Calculator,
  Percent, X, ChevronRight, Loader2,
  AlertCircle, CheckCircle2, HelpCircle, Zap,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type CalcType = 'labor_compensation' | 'litigation_fee' | 'lpr_interest'
  | 'work_injury' | 'traffic_accident' | 'personal_injury' | 'divorce_property'
  | 'lawyer_fee' | 'property_preservation' | 'notary_fee' | 'arbitration_fee'
  | 'default_penalty' | 'loan_interest' | 'unpaid_wages';

interface BreakdownItem { label: string; amount: number; }
interface CalcResult {
  totalAmount: number; breakdown: BreakdownItem[];
  formula: string; legalBasis: string; note: string;
}
interface FieldDef {
  key: string; label: string; type: 'number' | 'select';
  placeholder?: string; defaultValue?: string | number;
  options?: { value: string; label: string }[];
  step?: string; min?: string;
  hint?: string;    // 普通话解释，显示在字段下方
  group?: string;   // 字段分组标题（首次出现时显示）
}
interface QuickFill { label: string; values: Record<string, string | number>; }
interface CalcConfig {
  type: CalcType; title: string; subtitle: string;
  icon: React.ReactNode; color: string;
  fields: FieldDef[]; resultLabel: string;
  scenario?: string;         // 一句话场景描述
  quickFills?: QuickFill[];  // 快速填入示例
}

const CALC_CONFIGS: CalcConfig[] = [
  {
    type: 'labor_compensation', title: '劳动补偿计算',
    subtitle: '测算 N/N+1/2N 经济补偿及赔偿金',
    scenario: '被公司辞退或违法解除合同时，能拿到多少补偿？',
    icon: <Briefcase size={20}/>, color: 'text-blue-600', resultLabel: '补偿总额',
    quickFills: [
      { label: '月薪8000·3年·未提前通知', values: { monthly_salary: 8000, years_worked: 3, dismissal_type: 'N1' } },
      { label: '月薪12000·5年·违法解除', values: { monthly_salary: 12000, years_worked: 5, dismissal_type: '2N' } },
      { label: '月薪6000·1.5年·正常解除', values: { monthly_salary: 6000, years_worked: 1.5, dismissal_type: 'N' } },
    ],
    fields: [
      { key: 'monthly_salary', label: '税前月工资（元）', type: 'number', placeholder: '如：8000', min: '0.01', step: '100', group: '基本信息',
        hint: '填离职前12个月平均月工资（含奖金、津贴）。全年总收入 ÷ 12 即可。' },
      { key: 'years_worked', label: '在公司工作了多少年？', type: 'number', placeholder: '如：3.5（三年半填3.5）', min: '0', step: '0.5',
        hint: '从入职到离职的时长。不满半年按0.5算，满半年不满一年按1算。' },
      { key: 'dismissal_type', label: '你的情况是哪种？', type: 'select', defaultValue: 'N1',
        hint: '不确定？公司没提前30天书面通知就叫你走，选"N+1"最常见。',
        options: [
          { value: 'N',  label: 'N — 公司提前30天通知解除，或你主动辞职' },
          { value: 'N1', label: 'N+1 — 公司未提前通知，直接让你走（最常见）' },
          { value: '2N', label: '2N — 公司违法解除（怀孕期/工伤期被开）' },
        ] },
    ],
  },
  {
    type: 'litigation_fee', title: '诉讼费测算',
    subtitle: '根据标的额自动计算案件受理费',
    scenario: '打官司前先算清要预缴多少诉讼费，避免到法院时手足无措。',
    icon: <Gavel size={20}/>, color: 'text-emerald-600', resultLabel: '案件受理费',
    quickFills: [
      { label: '借款纠纷5万元', values: { claim_amount: 50000 } },
      { label: '合同纠纷30万元', values: { claim_amount: 300000 } },
      { label: '大额纠纷100万元', values: { claim_amount: 1000000 } },
    ],
    fields: [
      { key: 'claim_amount', label: '你要告对方多少钱？（元）', type: 'number', placeholder: '如：500000', min: '0.01', step: '1000', group: '诉讼信息',
        hint: '填写起诉时要求赔偿或追讨的总金额。胜诉后可要求对方承担全部诉讼费。' },
    ],
  },
  {
    type: 'lpr_interest', title: '逾期利息 (LPR)',
    subtitle: '基于全国银行间拆借中心基准利率',
    scenario: '对方还款逾期，按法院认可的LPR标准，能要求他支付多少利息？',
    icon: <TrendingUp size={20}/>, color: 'text-violet-600', resultLabel: '逾期利息合计',
    quickFills: [
      { label: '借了10万·逾期6个月', values: { principal: 100000, months: 6, lpr_rate: 3.45 } },
      { label: '借了50万·逾期1年', values: { principal: 500000, months: 12, lpr_rate: 3.45 } },
    ],
    fields: [
      { key: 'principal', label: '欠款本金（元）', type: 'number', placeholder: '如：100000', min: '0.01', step: '1000', group: '欠款信息',
        hint: '对方拖着没还的本金，不含之前已产生的利息。' },
      { key: 'months', label: '逾期了多久？（月）', type: 'number', placeholder: '如：6', min: '0.1', step: '1',
        hint: '从约定还款日到今天的月数。逾期20天可填0.67（20÷30）。' },
      { key: 'lpr_rate', label: 'LPR 年利率（%）', type: 'number', placeholder: '3.45', defaultValue: 3.45, min: '0.01', step: '0.01',
        hint: '一年期LPR由央行每月公布，2024年为3.45%，已预填。如需按LPR×1.5倍主张，可改为5.175。' },
    ],
  },
  // ── 赔偿与救济类 ──
  {
    type: 'work_injury', title: '工伤赔偿计算',
    subtitle: '一次性伤残补助金及就业/医疗补助金',
    scenario: '工作中受伤并评定伤残等级后，公司和工伤保险要赔多少？',
    icon: <Scale size={20}/>, color: 'text-orange-600', resultLabel: '工伤赔偿总额',
    quickFills: [
      { label: '月薪6000·均薪8000·十级', values: { monthly_salary: 6000, area_avg_salary: 8000, disability_level: '10', medical_cost: 5000 } },
      { label: '月薪8000·均薪10000·八级', values: { monthly_salary: 8000, area_avg_salary: 10000, disability_level: '8', medical_cost: 20000 } },
    ],
    fields: [
      { key: 'monthly_salary', label: '你的月工资（元）', type: 'number', placeholder: '如：6000', min: '0.01', step: '100', group: '个人信息',
        hint: '受伤前12个月的平均月工资，含奖金和补贴。入职不足12个月按实际月数平均。' },
      { key: 'area_avg_salary', label: '当地职工月均工资（元）', type: 'number', placeholder: '如：8000', min: '0.01', step: '100',
        hint: '由统筹地区（通常是你所在的市）社保局每年公布。可在当地社保局官网搜索"[城市]职工平均工资"获取。' },
      { key: 'disability_level', label: '伤残等级', type: 'select', defaultValue: '10', group: '伤残情况',
        hint: '由劳动能力鉴定委员会出具鉴定书确认。一级最重（完全丧失劳动能力），十级最轻。',
        options: [
          { value: '1', label: '一级伤残（最重）— 完全丧失劳动能力' },
          { value: '2', label: '二级伤残' }, { value: '3', label: '三级伤残' }, { value: '4', label: '四级伤残' },
          { value: '5', label: '五级伤残 — 大部分丧失劳动能力' },
          { value: '6', label: '六级伤残' }, { value: '7', label: '七级伤残 — 部分丧失劳动能力' },
          { value: '8', label: '八级伤残' }, { value: '9', label: '九级伤残' },
          { value: '10', label: '十级伤残（最轻）— 工作能力轻度受限' },
        ] },
      { key: 'medical_cost', label: '已发生医疗费（元）', type: 'number', placeholder: '如：5000', defaultValue: 0, min: '0', step: '100',
        hint: '工伤认定后发生的治疗费用（需正规发票）。若已由工伤保险报销，填0。' },
    ],
  },
  {
    type: 'traffic_accident', title: '交通事故赔偿',
    subtitle: '误工费、残疾赔偿金、护理费等速算',
    scenario: '发生车祸对方全责或部分责任，能要求赔偿哪些项目共计多少钱？',
    icon: <Car size={20}/>, color: 'text-red-600', resultLabel: '交通事故赔偿总额',
    quickFills: [
      { label: '轻伤无伤残·城镇', values: { medical_cost: 8000, lost_work_days: 30, daily_income: 200, nursing_days: 10, disability_level: '0', area_annual_income: 60000, is_urban: 'true' } },
      { label: '较重伤十级·城镇', values: { medical_cost: 50000, lost_work_days: 90, daily_income: 300, nursing_days: 30, disability_level: '10', area_annual_income: 80000, is_urban: 'true' } },
    ],
    fields: [
      { key: 'medical_cost', label: '医疗费（元）', type: 'number', placeholder: '如：10000', defaultValue: 0, min: '0', step: '100', group: '损失明细',
        hint: '住院、门诊、药费等全部医疗单据总金额（凭发票索赔）。' },
      { key: 'lost_work_days', label: '误工天数（天）', type: 'number', placeholder: '如：30', defaultValue: 0, min: '0', step: '1',
        hint: '因伤无法正常工作的天数，需医院出具误工证明。' },
      { key: 'daily_income', label: '日收入（元/天）', type: 'number', placeholder: '如：200', defaultValue: 0, min: '0', step: '10',
        hint: '月工资 ÷ 21.75 即为日收入。无固定收入可参考当地同行业平均水平。' },
      { key: 'nursing_days', label: '护理天数（天）', type: 'number', placeholder: '如：30', defaultValue: 0, min: '0', step: '1',
        hint: '住院期间及出院后生活不能自理需要护理的天数，需医院证明。' },
      { key: 'disability_level', label: '伤残等级（无伤残选0）', type: 'select', defaultValue: '0', group: '伤残情况',
        hint: '由司法鉴定机构出具鉴定意见书确认。无伤残选"无伤残"，不影响其他项目计算。',
        options: [{value:'0',label:'无伤残'}].concat([1,2,3,4,5,6,7,8,9,10].map(n => ({ value: String(n), label: `${n} 级伤残` }))) },
      { key: 'area_annual_income', label: '当地居民年均收入（元）', type: 'number', placeholder: '如：60000', defaultValue: 0, min: '0', step: '1000',
        hint: '用于计算残疾赔偿金。可在当地统计局官网查询上一年度居民人均可支配收入。' },
      { key: 'is_urban', label: '城乡标准', type: 'select', defaultValue: 'true',
        hint: '按事故发生时你的户籍或经常居住地判断。城镇标准赔偿金通常更高。',
        options: [{value:'true',label:'城镇居民'},{value:'false',label:'农村居民'}] },
    ],
  },
  {
    type: 'personal_injury', title: '人身损害赔偿',
    subtitle: '一般侵权各项赔偿金速算',
    icon: <UserRound size={20}/>, color: 'text-pink-600', resultLabel: '人身损害赔偿合计',
    fields: [
      { key: 'medical_cost', label: '医疗费（元）', type: 'number', placeholder: '如：5000', defaultValue: 0, min: '0', step: '0.01' },
      { key: 'lost_work_days', label: '误工天数（天）', type: 'number', placeholder: '如：15', defaultValue: 0, min: '0', step: '1' },
      { key: 'daily_income', label: '日收入（元/天）', type: 'number', placeholder: '如：200', defaultValue: 0, min: '0', step: '0.01' },
      { key: 'nursing_days', label: '护理天数（天）', type: 'number', placeholder: '如：7', defaultValue: 0, min: '0', step: '1' },
      { key: 'hospitalization_days', label: '住院天数（天）', type: 'number', placeholder: '如：5', defaultValue: 0, min: '0', step: '1' },
      { key: 'transport_cost', label: '交通费（元）', type: 'number', placeholder: '如：500', defaultValue: 0, min: '0', step: '0.01' },
    ],
  },
  {
    type: 'divorce_property', title: '离婚财产预估',
    subtitle: '共同财产分割比例预估',
    icon: <HeartCrack size={20}/>, color: 'text-rose-600', resultLabel: '本方预估分得',
    fields: [
      { key: 'total_joint_property', label: '共同财产总额（元）', type: 'number', placeholder: '如：1000000', min: '0.01', step: '100' },
      { key: 'joint_debt', label: '共同债务（元）', type: 'number', placeholder: '如：200000', defaultValue: 0, min: '0', step: '100' },
      { key: 'is_fault_party', label: '本方是否为过错方', type: 'select', defaultValue: 'false',
        options: [{value:'false',label:'否（无过错）'},{value:'true',label:'是（有过错）'}] },
      { key: 'fault_deduction_pct', label: '过错扣减比例（%，0-30）', type: 'number', placeholder: '如：10', defaultValue: 0, min: '0', step: '1' },
      { key: 'child_care_bonus_pct', label: '抚养子女补偿比例（%，0-10）', type: 'number', placeholder: '如：5', defaultValue: 0, min: '0', step: '1' },
    ],
  },
  // ── 法律费用类 ──
  {
    type: 'lawyer_fee', title: '律师费测算',
    subtitle: '按标的额阶梯累进（北京指导价）',
    icon: <Briefcase size={20}/>, color: 'text-sky-600', resultLabel: '律师费参考金额',
    fields: [
      { key: 'claim_amount', label: '标的额（元）', type: 'number', placeholder: '如：500000', min: '0.01', step: '100' },
    ],
  },
  {
    type: 'property_preservation', title: '财产保全费',
    subtitle: '申请保全费上限5000元阶梯计算',
    icon: <ShieldCheck size={20}/>, color: 'text-teal-600', resultLabel: '财产保全费',
    fields: [
      { key: 'claim_amount', label: '申请保全金额（元）', type: 'number', placeholder: '如：500000', min: '0.01', step: '100' },
    ],
  },
  {
    type: 'notary_fee', title: '公证费测算',
    subtitle: '财产性民事法律行为分段累进',
    icon: <Stamp size={20}/>, color: 'text-amber-600', resultLabel: '公证费',
    fields: [
      { key: 'notary_type', label: '公证类型', type: 'select', defaultValue: 'property',
        options: [{value:'property',label:'财产性公证（按标的额）'},{value:'non_property',label:'非财产性公证（固定200元）'}] },
      { key: 'claim_amount', label: '标的额（元，财产性公证填写）', type: 'number', placeholder: '如：500000', defaultValue: 0, min: '0', step: '100' },
    ],
  },
  {
    type: 'arbitration_fee', title: '仲裁费测算',
    subtitle: '商事仲裁受理费+处理费速算',
    icon: <Coins size={20}/>, color: 'text-indigo-600', resultLabel: '仲裁费合计',
    fields: [
      { key: 'arb_type', label: '仲裁类型', type: 'select', defaultValue: 'commercial',
        options: [{value:'commercial',label:'商事仲裁（CIETAC标准）'},{value:'labor',label:'劳动仲裁（免费）'}] },
      { key: 'claim_amount', label: '争议金额（元）', type: 'number', placeholder: '如：500000', defaultValue: 0, min: '0', step: '100' },
    ],
  },
  // ── 财务与利息类 ──
  {
    type: 'default_penalty', title: '违约金上限',
    subtitle: '损失130%/年化24%/LPR×4倍红线测算',
    icon: <Percent size={20}/>, color: 'text-red-500', resultLabel: '建议违约金上限',
    fields: [
      { key: 'contract_amount', label: '合同总额（元）', type: 'number', placeholder: '如：100000', min: '0.01', step: '100' },
      { key: 'actual_loss', label: '实际损失估算（元）', type: 'number', placeholder: '如：50000', defaultValue: 0, min: '0', step: '100' },
      { key: 'agreed_penalty', label: '约定违约金（元，可不填）', type: 'number', placeholder: '如：30000', defaultValue: 0, min: '0', step: '100' },
      { key: 'lpr_rate', label: 'LPR 年利率（%）', type: 'number', placeholder: '3.45', defaultValue: 3.45, min: '0.01', step: '0.01' },
      { key: 'months', label: '违约期限（月）', type: 'number', placeholder: '如：12', defaultValue: 12, min: '0.1', step: '1' },
    ],
  },
  {
    type: 'loan_interest', title: '借贷利息计算',
    subtitle: '民间借贷LPR×4倍保护上限速算',
    icon: <TrendingUp size={20}/>, color: 'text-green-600', resultLabel: '受法律保护利息',
    fields: [
      { key: 'principal', label: '本金（元）', type: 'number', placeholder: '如：100000', min: '0.01', step: '0.01' },
      { key: 'annual_rate', label: '约定年利率（%，不填则按LPR）', type: 'number', placeholder: '如：12', defaultValue: 0, min: '0', step: '0.1' },
      { key: 'months', label: '借贷月数', type: 'number', placeholder: '如：12', min: '0.1', step: '0.5' },
      { key: 'lpr_rate', label: 'LPR 年利率（%）', type: 'number', placeholder: '3.45', defaultValue: 3.45, min: '0.01', step: '0.01' },
    ],
  },
  {
    type: 'unpaid_wages', title: '欠薪补偿计算',
    subtitle: '未签合同双倍工资+年休假折算',
    icon: <Calculator size={20}/>, color: 'text-yellow-600', resultLabel: '欠薪补偿合计',
    fields: [
      { key: 'monthly_salary', label: '月工资（元）', type: 'number', placeholder: '如：8000', min: '0.01', step: '0.01' },
      { key: 'years_worked', label: '工作年限（年）', type: 'number', placeholder: '如：3', defaultValue: 1, min: '0.1', step: '0.5' },
      { key: 'months_no_contract', label: '未签合同月数（0-11）', type: 'number', placeholder: '如：3', defaultValue: 0, min: '0', step: '1' },
      { key: 'unused_annual_leave', label: '未休年假天数', type: 'number', placeholder: '如：5', defaultValue: 0, min: '0', step: '1' },
      { key: 'arrears_months', label: '拖欠工资月数', type: 'number', placeholder: '如：2', defaultValue: 0, min: '0', step: '1' },
    ],
  },
];

function fmt(n: number): string {
  if (Number.isInteger(n)) return n.toLocaleString('zh-CN');
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}
function fmtMoney(n: number): string {
  return '\u00A5 ' + n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const inp = 'w-full rounded-[12px] border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 px-4 py-2.5 text-[13px] text-gray-800 dark:text-gray-200 placeholder:text-gray-300 dark:placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-colors';

function CalcModal({ config, onClose }: { config: CalcConfig; onClose: () => void }) {
  const initValues: Record<string, string> = {};
  config.fields.forEach(f => { initValues[f.key] = f.defaultValue !== undefined ? String(f.defaultValue) : ''; });
  const [values, setValues] = useState<Record<string, string>>(initValues);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CalcResult | null>(null);
  const [error, setError] = useState('');
  const [activeHint, setActiveHint] = useState<string | null>(null);

  const applyQuickFill = (qf: QuickFill) => {
    const next = { ...initValues };
    Object.entries(qf.values).forEach(([k, v]) => { next[k] = String(v); });
    setValues(next); setResult(null); setError('');
  };

  const handleCalc = useCallback(async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const params: Record<string, string | number> = {};
      for (const f of config.fields) {
        const val = values[f.key];
        if (!val && val !== '0') throw new Error(`请填写「${f.label}」`);
        params[f.key] = f.type === 'number' ? parseFloat(val) : val;
      }
      const resp = await fetch(`${API_BASE}/api/tools/calculator/calculate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ calcType: config.type, params }),
      });
      if (!resp.ok) {
        const d = await resp.json().catch(() => ({})) as { detail?: string };
        throw new Error(d.detail || `服务器错误 ${resp.status}`);
      }
      const data = await resp.json() as { success: boolean; data: CalcResult };
      if (!data.success) throw new Error('计算失败，请检查参数');
      setResult(data.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : '计算失败');
    } finally { setLoading(false); }
  }, [config, values]);

  // 渲染字段列表，支持 group 分隔
  const renderedFields: React.ReactNode[] = [];
  let lastGroup = '';
  config.fields.forEach(f => {
    if (f.group && f.group !== lastGroup) {
      lastGroup = f.group;
      renderedFields.push(
        <div key={`g-${f.group}`} className="flex items-center gap-2 pt-1">
          <span className="text-[10px] font-black uppercase tracking-widest text-gray-400">{f.group}</span>
          <div className="flex-1 h-px bg-gray-100 dark:bg-white/10"></div>
        </div>
      );
    }
    renderedFields.push(
      <div key={f.key}>
        <div className="flex items-center gap-1.5 mb-1.5">
          <label className="text-[12px] font-semibold text-gray-700 dark:text-gray-300">{f.label}</label>
          {f.hint && (
            <button type="button" onClick={() => setActiveHint(activeHint === f.key ? null : f.key)}
              className={`p-0.5 rounded-full transition-colors ${activeHint === f.key ? 'text-blue-500' : 'text-gray-300 hover:text-blue-400'}`}>
              <HelpCircle size={13}/>
            </button>
          )}
        </div>
        {activeHint === f.key && (
          <div className="mb-2 px-3 py-2 rounded-[10px] bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/30 text-[11px] text-blue-700 dark:text-blue-300 leading-relaxed">
            💡 {f.hint}
          </div>
        )}
        {f.type === 'select' ? (
          <select value={values[f.key]} onChange={e => setValues(v => ({...v,[f.key]:e.target.value}))} className={inp}>
            {f.options!.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        ) : (
          <input type="number" value={values[f.key]} min={f.min} step={f.step} placeholder={f.placeholder} onChange={e => setValues(v => ({...v,[f.key]:e.target.value}))} className={inp}/>
        )}
      </div>
    );
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]"/>
      <div className="relative w-full max-w-[540px] max-h-[92vh] overflow-y-auto bg-white dark:bg-[#151822] rounded-[28px] shadow-2xl border border-gray-100 dark:border-white/10" onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 z-10 bg-white dark:bg-[#151822] px-7 pt-6 pb-4 border-b border-gray-50 dark:border-white/5 rounded-t-[28px]">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl bg-gray-50 dark:bg-white/5 flex items-center justify-center ${config.color}`}>{config.icon}</div>
              <div>
                <h2 className="text-[16px] font-bold text-gray-900 dark:text-gray-100">{config.title}</h2>
                <p className="text-[11px] text-gray-400 dark:text-gray-500">{config.subtitle}</p>
              </div>
            </div>
            <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-white/10 text-gray-400 transition-colors"><X size={16}/></button>
          </div>
          {config.scenario && (
            <div className="mt-3 px-3 py-2 rounded-[10px] bg-gray-50 dark:bg-white/5 text-[12px] text-gray-500 dark:text-gray-400 leading-relaxed">
              📌 {config.scenario}
            </div>
          )}
        </div>
        {config.quickFills && config.quickFills.length > 0 && (
          <div className="px-7 pt-5 pb-0">
            <div className="flex items-center gap-1.5 mb-2">
              <Zap size={11} className="text-amber-500"/>
              <span className="text-[10px] font-black uppercase tracking-widest text-gray-400">快速填入示例</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {config.quickFills.map((qf, i) => (
                <button key={i} onClick={() => applyQuickFill(qf)}
                  className="text-[11px] font-medium px-3 py-1.5 rounded-full border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-gray-600 dark:text-gray-300 hover:border-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 transition-all active:scale-95">
                  {qf.label}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="px-7 py-5 space-y-4">
          {renderedFields}
          {error && (
            <div className="flex items-center gap-2.5 rounded-[12px] bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800/30 px-4 py-3">
              <AlertCircle size={14} className="text-red-500 shrink-0"/>
              <p className="text-[12px] text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}
          <button onClick={handleCalc} disabled={loading} className="w-full rounded-[14px] bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-3 text-[14px] font-semibold transition-colors flex items-center justify-center gap-2">
            {loading ? <><Loader2 size={15} className="animate-spin"/> 计算中...</> : <><Calculator size={15}/> 开始计算</>}
          </button>
        </div>
        {result && (
          <div className="px-7 pb-7 space-y-4">
            <div className="rounded-[18px] bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-800/30 p-5">
              <div className="flex items-center gap-2 mb-1"><CheckCircle2 size={14} className="text-blue-500"/><span className="text-[11px] font-bold text-blue-500 uppercase tracking-widest">{config.resultLabel}</span></div>
              <p className="text-[32px] font-bold text-gray-900 dark:text-gray-100 tracking-tight">{fmtMoney(result.totalAmount)}</p>
              <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-1 font-mono">{result.formula}</p>
            </div>
            <div className="rounded-[16px] bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/10 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-gray-100 dark:border-white/10"><span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">计算明细</span></div>
              {result.breakdown.map((item, i) => (
                <div key={i} className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100 dark:border-white/5 last:border-0">
                  <span className="text-[12px] text-gray-500 dark:text-gray-400">{item.label}</span>
                  <span className="text-[12px] font-semibold text-gray-800 dark:text-gray-200 tabular-nums">{item.amount > 100 ? fmtMoney(item.amount) : fmt(item.amount)}</span>
                </div>
              ))}
            </div>
            <div className="rounded-[14px] bg-amber-50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-800/20 px-4 py-3">
              <p className="text-[10px] font-bold text-amber-600 dark:text-amber-400 uppercase tracking-widest mb-1">法律依据</p>
              <p className="text-[12px] text-gray-600 dark:text-gray-300 leading-relaxed">{result.legalBasis}</p>
            </div>
            {result.note && <p className="text-[11px] text-gray-400 dark:text-gray-500 leading-relaxed px-1">⚠️ {result.note}</p>}
          </div>
        )}
      </div>
    </div>
  );
}

function FeaturedCard({ config, onClick }: { config: CalcConfig; onClick: () => void }) {
  return (
    <button onClick={onClick} className="group cursor-pointer bg-[#F0F4F9] dark:bg-[#151822] hover:bg-[#E4E9F0] dark:hover:bg-white/10 rounded-[20px] p-4 transition-colors duration-300 flex flex-col text-left w-full">
      <div className={`w-8 h-8 flex items-center justify-center rounded-xl bg-white dark:bg-white/5 mb-2 shadow-sm group-hover:scale-110 transition-transform duration-300 ${config.color}`}>{config.icon}</div>
      <h3 className="text-[13px] font-bold text-[#1F1F1F] dark:text-gray-100 mb-0.5 group-hover:text-blue-600 transition-colors">{config.title}</h3>
      <p className="text-[11px] text-[#444746] dark:text-gray-400 leading-snug opacity-80">{config.subtitle}</p>
      <div className="mt-3 flex items-center gap-1 text-[10px] font-semibold text-gray-400 group-hover:text-blue-500 transition-colors">点击计算 <ChevronRight size={11} className="group-hover:translate-x-0.5 transition-transform"/></div>
    </button>
  );
}

function SmallCard({ icon, title, desc, color, active, onClick }: { icon: React.ReactNode; title: string; desc: string; color?: string; active: boolean; onClick?: () => void }) {
  return (
    <button onClick={onClick} disabled={!active}
      className={`group text-left w-full rounded-[16px] p-4 border transition-all duration-200 flex items-center gap-3 ${
        active
          ? 'bg-white dark:bg-[#151822] border-gray-100 dark:border-white/8 hover:border-blue-200 dark:hover:border-white/20 hover:shadow-md hover:shadow-blue-500/5 cursor-pointer'
          : 'bg-gray-50 dark:bg-white/3 border-gray-100 dark:border-white/5 opacity-40 cursor-not-allowed'
      }`}>
      <div className={`w-9 h-9 shrink-0 flex items-center justify-center rounded-[12px] transition-all duration-200 ${
        active ? `${color ?? 'text-blue-600'} bg-blue-50 dark:bg-blue-900/20 group-hover:scale-110` : 'text-gray-400 bg-gray-100 dark:bg-white/5'
      }`}>{icon}</div>
      <div className="min-w-0 flex-1">
        <h4 className={`text-[13px] font-semibold mb-0.5 truncate transition-colors ${
          active ? 'text-[#1F1F1F] dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400' : 'text-gray-400'
        }`}>{title}</h4>
        <p className="text-[11px] text-gray-400 dark:text-gray-500 leading-snug truncate">{desc}</p>
      </div>
      {active && <ChevronRight size={14} className="shrink-0 text-gray-300 group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all duration-200"/>}
    </button>
  );
}

const CATEGORY_ACCENTS: Record<string, { bar: string; text: string }> = {
  '赔偿与救济': { bar: 'bg-gradient-to-b from-orange-400 to-red-500',   text: 'text-orange-500 dark:text-orange-400' },
  '法律费用':   { bar: 'bg-gradient-to-b from-emerald-400 to-teal-500',  text: 'text-emerald-600 dark:text-emerald-400' },
  '财务与利息': { bar: 'bg-gradient-to-b from-violet-400 to-indigo-500', text: 'text-violet-600 dark:text-violet-400' },
};

function CategorySection({ title, children }: { title: string; children: React.ReactNode }) {
  const accent = CATEGORY_ACCENTS[title] ?? { bar: 'bg-gradient-to-b from-blue-400 to-blue-600', text: 'text-blue-500' };
  return (
    <div>
      <div className="flex items-center gap-2.5 mb-4 px-0.5">
        <span className={`w-1 h-5 rounded-full ${accent.bar} inline-block shrink-0`}/>
        <h3 className={`text-[12px] font-bold uppercase tracking-widest ${accent.text} transition-colors duration-300`}>{title}</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">{children}</div>
    </div>
  );
}

export default function LegalCalculatorsPage() {
  const router = useRouter();
  const [activeConfig, setActiveConfig] = useState<CalcConfig | null>(null);
  const open = (type: CalcType) => setActiveConfig(CALC_CONFIGS.find(c => c.type === type) ?? null);

  return (
    <main className="relative z-10 flex-1 flex flex-col overflow-y-auto transition-colors duration-300">
      <div className="flex-1 flex flex-col w-full px-6 pt-4 pb-2 lg:px-8 h-full">
        <header className="mb-5 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <button className="p-2 rounded-full hover:bg-[#F0F4F9] dark:hover:bg-white/10 text-[#444746] dark:text-gray-400 transition-colors" onClick={() => router.push('/tools')}><ArrowLeft size={18}/></button>
            <h1 className="text-2xl font-bold tracking-tight text-[#1F1F1F] dark:text-gray-100 flex items-center gap-2">法律计算器 🧮</h1>
          </div>
        </header>
        <section className="mb-10 shrink-0">
          <div className="flex items-center gap-2.5 mb-4 px-0.5">
            <span className="w-1 h-5 rounded-full bg-gradient-to-b from-blue-400 to-violet-500 inline-block shrink-0"/>
            <h2 className="text-[12px] font-bold uppercase tracking-widest text-blue-500 dark:text-blue-400">热门推荐</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {(['labor_compensation','litigation_fee','lpr_interest'] as CalcType[]).map(t => {
              const c = CALC_CONFIGS.find(x => x.type === t)!;
              return <FeaturedCard key={c.type} config={c} onClick={() => open(c.type)}/>;
            })}
          </div>
        </section>
        <div className="space-y-10 shrink-0">
          <CategorySection title="赔偿与救济">
            <SmallCard icon={<Briefcase size={16}/>} color="text-blue-600"   title="劳动补偿" desc="N/N+1/2N 经济补偿" active onClick={() => open('labor_compensation')}/>
            <SmallCard icon={<Scale size={16}/>}    color="text-orange-600" title="工伤赔偿" desc="伤残补助与医疗费测算" active onClick={() => open('work_injury')}/>
            <SmallCard icon={<Car size={16}/>}      color="text-red-600"    title="交通事故" desc="误工费及伤残赔偿测算" active onClick={() => open('traffic_accident')}/>
            <SmallCard icon={<UserRound size={16}/>} color="text-pink-600"   title="人身损害" desc="一般人身侵权赔偿计算" active onClick={() => open('personal_injury')}/>
            <SmallCard icon={<HeartCrack size={16}/>} color="text-rose-600"  title="离婚财产" desc="共同财产分配比例预估" active onClick={() => open('divorce_property')}/>
          </CategorySection>
          <CategorySection title="法律费用">
            <SmallCard icon={<Gavel size={16}/>}       color="text-emerald-600" title="诉讼费测算" desc="案件受理费自动计算" active onClick={() => open('litigation_fee')}/>
            <SmallCard icon={<Briefcase size={16}/>}  color="text-sky-600"     title="律师费标准" desc="基于各省市行业指导价" active onClick={() => open('lawyer_fee')}/>
            <SmallCard icon={<ShieldCheck size={16}/>} color="text-teal-600"    title="财产保全费" desc="保全申请费与担保金额" active onClick={() => open('property_preservation')}/>
            <SmallCard icon={<Stamp size={16}/>}       color="text-amber-600"  title="公证费" desc="各类民商事公证费用" active onClick={() => open('notary_fee')}/>
            <SmallCard icon={<Coins size={16}/>}       color="text-indigo-600" title="仲裁费" desc="商事仲裁及劳动仲裁费" active onClick={() => open('arbitration_fee')}/>
          </CategorySection>
          <CategorySection title="财务与利息">
            <SmallCard icon={<TrendingUp size={16}/>}  color="text-violet-600" title="逾期利息 (LPR)" desc="银行拆借中心实时利率" active onClick={() => open('lpr_interest')}/>
            <SmallCard icon={<Percent size={16}/>}     color="text-red-500"    title="违约金上限" desc="基于合同总额与实际损失" active onClick={() => open('default_penalty')}/>
            <SmallCard icon={<TrendingUp size={16}/>}  color="text-green-600"  title="借贷利息" desc="含年化利率与折息转换" active onClick={() => open('loan_interest')}/>
            <SmallCard icon={<Calculator size={16}/>}  color="text-yellow-600" title="欠薪补偿" desc="带薪年休假及工资测算" active onClick={() => open('unpaid_wages')}/>
          </CategorySection>
        </div>
        <footer className="mt-auto pt-4 pb-2 text-center shrink-0">
          <p className="text-xs text-gray-400 dark:text-gray-500 font-normal tracking-wide">AI 生成内容仅供参考，不构成正式法律意见</p>
        </footer>
      </div>
      {activeConfig && <CalcModal key={activeConfig.type} config={activeConfig} onClose={() => setActiveConfig(null)}/>}
    </main>
  );
}
