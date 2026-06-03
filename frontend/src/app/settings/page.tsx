'use client';

import { useMemo, useState } from 'react';
import {
  Check,
  CheckCircle,
  ChevronRight,
  LayoutGrid,
  Monitor,
  Moon,
  Palette,
  Settings2,
  SlidersHorizontal,
  Sun,
  Trash2,
  Type,
  UserRoundCog,
  Zap,
} from 'lucide-react';
import { useChatStore, PersonalityType } from '@/store/chatStore';
import { Density, FontSize, useSettings } from '@/hooks/useSettings';
import { Theme, useTheme } from '@/hooks/useTheme';

type Section = 'general' | 'appearance' | 'data';

const personalities: Array<{ value: PersonalityType; label: string; desc: string }> = [
  { value: 'empathy', label: '共情顾问', desc: '语气温和，适合日常咨询和初步判断。' },
  { value: 'machine', label: '严谨机器', desc: '结构直接，优先给出规则、要件和结论。' },
  { value: 'cost_expert', label: '成本专家', desc: '关注时间、费用、证据成本和执行路径。' },
  { value: 'aggressive', label: '进攻策略', desc: '更主动寻找抗辩点、谈判点和反击空间。' },
  { value: 'educator', label: '普法导师', desc: '解释更细，适合学习法律概念和流程。' },
];

const fontSizes: Array<{ value: FontSize; label: string; sample: string; desc: string }> = [
  { value: 'small', label: '小', sample: 'Aa', desc: '适合列表、工具页和高信息密度场景。' },
  { value: 'medium', label: '中', sample: 'Aa', desc: '默认阅读尺寸，兼顾舒适和效率。' },
  { value: 'large', label: '大', sample: 'Aa', desc: '更适合长文阅读和大屏展示。' },
];

const densities: Array<{ value: Density; label: string; desc: string; bars: number[] }> = [
  { value: 'compact', label: '紧凑', desc: '减少留白，更多内容同屏展示。', bars: [65, 90, 55] },
  { value: 'standard', label: '标准', desc: '默认间距，适合多数工作流。', bars: [75, 58, 88] },
  { value: 'relaxed', label: '宽松', desc: '增加呼吸感，适合演示和大屏。', bars: [90, 70, 52] },
];

const themes: Array<{ value: Theme; label: string; desc: string; icon: typeof Sun }> = [
  { value: 'light', label: '浅色', desc: '明亮背景，适合白天办公。', icon: Sun },
  { value: 'dark', label: '深色', desc: '降低亮度，适合夜间阅读。', icon: Moon },
  { value: 'system', label: '跟随系统', desc: '自动同步操作系统偏好。', icon: Monitor },
];

const sections: Array<{ value: Section; label: string; desc: string; icon: typeof Settings2 }> = [
  { value: 'general', label: '通用', desc: '默认回答风格', icon: Settings2 },
  { value: 'appearance', label: '外观', desc: '主题、字号、密度', icon: Palette },
  { value: 'data', label: '数据', desc: '本地对话记录', icon: LayoutGrid },
];

function SwitchControl({ checked }: { checked: boolean }) {
  return (
    <span className={`flex h-6 w-11 rounded-full p-0.5 transition ${checked ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
      <span className={`h-5 w-5 rounded-full bg-white shadow-sm transition ${checked ? 'translate-x-5' : ''}`} />
    </span>
  );
}

export default function SettingsPage() {
  const [section, setSection] = useState<Section>('general');
  const { personality, setPersonality, sessions, deleteSession } = useChatStore();
  const ui = useSettings();
  const { theme, resolvedTheme, setTheme } = useTheme();

  const pinnedCount = useMemo(() => sessions.filter((session) => session.isPinned).length, [sessions]);

  function clearHistory() {
    if (!window.confirm(`确定清除 ${sessions.length} 条本地对话记录吗？`)) return;
    sessions.forEach((session) => deleteSession(session.id));
  }

  return (
    <div className="min-h-full bg-[#F6F8FC] px-5 py-6 text-slate-950 dark:bg-[#0B0D14] dark:text-slate-100 md:px-8">
      <div className="mx-auto w-full max-w-7xl">
        <header className="mb-6 flex flex-col gap-4 border-b border-slate-200 pb-5 pr-20 dark:border-slate-800 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
              <SlidersHorizontal size={22} />
            </div>
            <h1 className="text-2xl font-semibold tracking-normal md:text-3xl">设置</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500 dark:text-slate-400">
              管理回答风格、界面显示和本地数据偏好。
            </p>
          </div>
          <div className="grid grid-cols-3 gap-2 rounded-lg border border-slate-200 bg-white p-2 text-center shadow-sm dark:border-slate-800 dark:bg-slate-950">
            <div className="min-w-20 px-3 py-2">
              <p className="text-lg font-semibold">{sessions.length}</p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">对话</p>
            </div>
            <div className="min-w-20 border-x border-slate-100 px-3 py-2 dark:border-slate-800">
              <p className="text-lg font-semibold">{pinnedCount}</p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">置顶</p>
            </div>
            <div className="min-w-20 px-3 py-2">
              <p className="text-lg font-semibold">{resolvedTheme === 'dark' ? '深色' : '浅色'}</p>
              <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">当前主题</p>
            </div>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[17rem_minmax(0,1fr)]">
          <aside className="lg:sticky lg:top-6 lg:self-start">
            <nav className="grid gap-2 rounded-lg border border-slate-200 bg-white p-2 shadow-sm dark:border-slate-800 dark:bg-slate-950 sm:grid-cols-3 lg:grid-cols-1">
              {sections.map((item) => {
                const Icon = item.icon;
                const active = section === item.value;
                return (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setSection(item.value)}
                    className={`flex min-h-16 items-center gap-3 rounded-md px-3 py-3 text-left transition ${
                      active
                        ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-200'
                        : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-900'
                    }`}
                  >
                    <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${active ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-500 dark:bg-slate-900 dark:text-slate-400'}`}>
                      <Icon size={17} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold">{item.label}</span>
                      <span className="mt-0.5 block truncate text-xs opacity-75">{item.desc}</span>
                    </span>
                    <ChevronRight size={15} className="hidden shrink-0 lg:block" />
                  </button>
                );
              })}
            </nav>
          </aside>

          <main className="min-w-0 space-y-5">
            {section === 'general' && (
              <>
                <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
                  <div className="flex items-start gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-200">
                      <UserRoundCog size={18} />
                    </span>
                    <div>
                      <h2 className="text-base font-semibold">默认律师人格</h2>
                      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">新对话会优先使用这里选择的回答风格。</p>
                    </div>
                  </div>
                  <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-3">
                    {personalities.map((item) => (
                      <button
                        key={item.value}
                        type="button"
                        onClick={() => setPersonality(item.value)}
                        className={`min-h-32 rounded-lg border p-4 text-left transition ${
                          personality === item.value
                            ? 'border-blue-500 bg-blue-50 shadow-sm dark:bg-blue-950/30'
                            : 'border-slate-200 hover:border-blue-200 hover:bg-slate-50 dark:border-slate-800 dark:hover:border-blue-900/70 dark:hover:bg-slate-900'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-semibold">{item.label}</span>
                          {personality === item.value && <CheckCircle size={17} className="text-blue-600" />}
                        </div>
                        <p className="mt-3 text-sm leading-6 text-slate-500 dark:text-slate-400">{item.desc}</p>
                      </button>
                    ))}
                  </div>
                </section>
              </>
            )}

            {section === 'appearance' && (
              <>
                <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
                  <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
                    <h2 className="flex items-center gap-2 text-base font-semibold">
                      <Palette size={18} />
                      主题
                    </h2>
                  </div>
                  <div className="grid gap-3 p-5 md:grid-cols-3">
                    {themes.map((item) => {
                      const Icon = item.icon;
                      const active = theme === item.value;
                      return (
                        <button
                          key={item.value}
                          type="button"
                          onClick={() => setTheme(item.value)}
                          className={`rounded-lg border p-4 text-left transition ${
                            active
                              ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30'
                              : 'border-slate-200 hover:border-blue-200 dark:border-slate-800 dark:hover:border-blue-900/70'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="flex items-center gap-2 text-sm font-semibold">
                              <Icon size={17} />
                              {item.label}
                            </span>
                            {active && <Check size={17} className="text-blue-600" />}
                          </div>
                          <p className="mt-3 text-sm leading-6 text-slate-500 dark:text-slate-400">{item.desc}</p>
                        </button>
                      );
                    })}
                  </div>
                </section>

                <section className="grid gap-5 xl:grid-cols-2">
                  <div className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
                    <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
                      <h2 className="flex items-center gap-2 text-base font-semibold">
                        <Type size={18} />
                        字体大小
                      </h2>
                    </div>
                    <div className="grid gap-3 p-5 sm:grid-cols-3 xl:grid-cols-1">
                      {fontSizes.map((item) => (
                        <button
                          key={item.value}
                          type="button"
                          onClick={() => ui.setFontSize(item.value)}
                          className={`flex min-h-24 items-center gap-4 rounded-lg border p-4 text-left transition ${
                            ui.settings.fontSize === item.value
                              ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30'
                              : 'border-slate-200 hover:border-blue-200 dark:border-slate-800 dark:hover:border-blue-900/70'
                          }`}
                        >
                          <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-slate-100 font-semibold dark:bg-slate-900 ${item.value === 'small' ? 'text-base' : item.value === 'large' ? 'text-2xl' : 'text-xl'}`}>
                            {item.sample}
                          </span>
                          <span className="min-w-0">
                            <span className="flex items-center gap-2 font-semibold">
                              {item.label}
                              {ui.settings.fontSize === item.value && <Check size={16} className="text-blue-600" />}
                            </span>
                            <span className="mt-1 block text-sm leading-5 text-slate-500 dark:text-slate-400">{item.desc}</span>
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
                    <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
                      <h2 className="text-base font-semibold">界面密度</h2>
                    </div>
                    <div className="grid gap-3 p-5 sm:grid-cols-3 xl:grid-cols-1">
                      {densities.map((item) => (
                        <button
                          key={item.value}
                          type="button"
                          onClick={() => ui.setDensity(item.value)}
                          className={`rounded-lg border p-4 text-left transition ${
                            ui.settings.density === item.value
                              ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30'
                              : 'border-slate-200 hover:border-blue-200 dark:border-slate-800 dark:hover:border-blue-900/70'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-semibold">{item.label}</p>
                              <p className="mt-1 text-sm leading-5 text-slate-500 dark:text-slate-400">{item.desc}</p>
                            </div>
                            {ui.settings.density === item.value && <Check size={16} className="text-blue-600" />}
                          </div>
                          <div className="mt-4 space-y-1.5">
                            {item.bars.map((width, index) => (
                              <span key={index} className="block h-1.5 rounded-full bg-slate-200 dark:bg-slate-800" style={{ width: `${width}%` }} />
                            ))}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </section>

                <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
                  <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
                    <h2 className="flex items-center gap-2 text-base font-semibold">
                      <Zap size={18} />
                      动效
                    </h2>
                  </div>
                  <div className="divide-y divide-slate-100 dark:divide-slate-800">
                    <button
                      type="button"
                      onClick={() => ui.setAnimationsEnabled(!ui.settings.animationsEnabled)}
                      className="flex w-full items-center justify-between gap-5 px-5 py-4 text-left transition hover:bg-slate-50 dark:hover:bg-slate-900"
                    >
                      <span>
                        <span className="block font-semibold">界面动画</span>
                        <span className="mt-1 block text-sm text-slate-500 dark:text-slate-400">控制页面过渡、消息淡入和按钮动效。</span>
                      </span>
                      <SwitchControl checked={ui.settings.animationsEnabled} />
                    </button>
                    <button
                      type="button"
                      onClick={() => ui.setFireEffectEnabled(!ui.settings.fireEffectEnabled)}
                      className="flex w-full items-center justify-between gap-5 px-5 py-4 text-left transition hover:bg-slate-50 dark:hover:bg-slate-900"
                    >
                      <span>
                        <span className="block font-semibold">Logo 特效</span>
                        <span className="mt-1 block text-sm text-slate-500 dark:text-slate-400">控制首页和侧边栏标识上的动态效果。</span>
                      </span>
                      <SwitchControl checked={ui.settings.fireEffectEnabled} />
                    </button>
                  </div>
                </section>
              </>
            )}

            {section === 'data' && (
              <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
                <div className="flex flex-col gap-4 border-b border-slate-100 px-5 py-4 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-base font-semibold">本地对话记录</h2>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">历史对话保存在当前浏览器，不会同步到其他设备。</p>
                  </div>
                  <button
                    type="button"
                    onClick={clearHistory}
                    disabled={sessions.length === 0}
                    className="inline-flex items-center justify-center gap-2 rounded-md border border-red-200 px-3.5 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-900/60 dark:text-red-300 dark:hover:bg-red-950/30"
                  >
                    <Trash2 size={16} />
                    清除记录
                  </button>
                </div>
                <div className="grid gap-0 divide-y divide-slate-100 dark:divide-slate-800">
                  <div className="grid gap-3 px-5 py-4 sm:grid-cols-[10rem_1fr]">
                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">记录数量</p>
                    <p className="font-semibold">{sessions.length} 条</p>
                  </div>
                  <div className="grid gap-3 px-5 py-4 sm:grid-cols-[10rem_1fr]">
                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">置顶会话</p>
                    <p className="font-semibold">{pinnedCount} 条</p>
                  </div>
                  <div className="grid gap-3 px-5 py-4 sm:grid-cols-[10rem_1fr]">
                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">存储位置</p>
                    <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">浏览器 localStorage</p>
                  </div>
                </div>
              </section>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
