import type { StrategyKey } from '@/components/debate-types';

export interface StrategyOption {
  key: StrategyKey;
  title: string;
  subtitle: string;
  icon: string;
  ring: string;
}

export const STRATEGY_OPTIONS: StrategyOption[] = [
  {
    key: 'aggressive',
    title: '激进施压 (Aggressive)',
    subtitle: '寻找逻辑漏洞，语言锋利，主动出击。',
    icon: '🗡️',
    ring: 'data-[active=true]:border-rose-400 data-[active=true]:bg-rose-50 dark:data-[active=true]:border-rose-500 dark:data-[active=true]:bg-rose-950/35',
  },
  {
    key: 'conservative',
    title: '死磕法条 (Conservative)',
    subtitle: '保守防御，强调程序正义与法条严谨。',
    icon: '🛡️',
    ring: 'data-[active=true]:border-blue-400 data-[active=true]:bg-blue-50 dark:data-[active=true]:border-blue-500 dark:data-[active=true]:bg-blue-950/35',
  },
  {
    key: 'mediator',
    title: '商业调解 (Mediator)',
    subtitle: '注重协作背景，推动减损与和解。',
    icon: '🤝',
    ring: 'data-[active=true]:border-emerald-400 data-[active=true]:bg-emerald-50 dark:data-[active=true]:border-emerald-500 dark:data-[active=true]:bg-emerald-950/35',
  },
];

export const EXAMPLE_CASES = [
  '员工张三因拒绝周末加班被公司以严重违反规章制度为由辞退。张三认为公司要求的加班不合理，且未支付加班费，公司辞退行为违法。公司则认为张三多次拒绝工作安排，严重影响工作进度，符合公司规章制度规定的辞退条件。',
  '租客李四租住房屋期间，因楼上漏水导致家具损坏。李四要求房东赔偿损失并减免租金，房东认为漏水是楼上住户责任，与自己无关，拒绝赔偿。李四认为房东有维修义务，应承担连带责任。',
  '外包程序员王五完成项目后，公司以代码质量不达标为由拒绝支付尾款。王五认为已按合同要求完成所有功能，公司应支付全款。公司则认为代码存在多处bug，需要返工，不符合验收标准。',
];
