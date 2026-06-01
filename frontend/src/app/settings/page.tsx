'use client';

import { useState } from 'react';
import { CheckCircle, Monitor, Moon, Palette, Settings2, Sun, Type, Zap } from 'lucide-react';
import { useChatStore, PersonalityType } from '@/store/chatStore';
import { Density, FontSize, useSettings } from '@/hooks/useSettings';
import { Theme, useTheme } from '@/hooks/useTheme';

type Section = 'general' | 'appearance';

const personalities: Array<{ value: PersonalityType; label: string; desc: string }> = [
  { value: 'empathy', label: '共情顾问', desc: '语气温和，适合日常咨询。' },
  { value: 'machine', label: '严谨机器', desc: '结构直接，优先给出规则和结论。' },
  { value: 'cost_expert', label: '成本专家', desc: '更关注成本、收益和执行路径。' },
  { value: 'aggressive', label: '进攻策略', desc: '尽量寻找抗辩点和反击空间。' },
  { value: 'educator', label: '普法导师', desc: '解释更细，适合学习法律概念。' },
];

const fontSizes: Array<{ value: FontSize; label: string; desc: string }> = [
  { value: 'small', label: '小', desc: '信息密度更高。' },
  { value: 'medium', label: '中', desc: '默认阅读尺寸。' },
  { value: 'large', label: '大', desc: '更舒适的阅读体验。' },
];

const densities: Array<{ value: Density; label: string; desc: string }> = [
  { value: 'compact', label: '紧凑', desc: '减少留白。' },
  { value: 'standard', label: '标准', desc: '平衡内容与留白。' },
  { value: 'relaxed', label: '宽松', desc: '更适合大屏。' },
];

const themes: Array<{ value: Theme; label: string; icon: typeof Sun }> = [
  { value: 'light', label: '浅色', icon: Sun },
  { value: 'dark', label: '深色', icon: Moon },
  { value: 'system', label: '跟随系统', icon: Monitor },
];

export default function SettingsPage() {
  const [section, setSection] = useState<Section>('general');
  const { personality, setPersonality, sessions, deleteSession } = useChatStore();
  const ui = useSettings();
  const { theme, setTheme } = useTheme();

  function clearHistory() {
    if (!window.confirm(`确定清除 ${sessions.length} 条本地对话记录吗？`)) return;
    sessions.forEach((session) => deleteSession(session.id));
  }

  return (
    <div className="min-h-full bg-[#F7F9FC] text-slate-900 dark:bg-[#0B0D14] dark:text-slate-100">
      <div className="mx-auto flex max-w-6xl gap-8 px-8 py-8">
        <aside className="w-56 shrink-0">
          <div className="mb-5">
            <h1 className="text-2xl font-semibold tracking-normal">设置</h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">偏好保存在当前浏览器。</p>
          </div>
          <nav className="space-y-2">
            <button
              type="button"
              onClick={() => setSection('general')}
              className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${
                section === 'general'
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-200'
                  : 'text-slate-600 hover:bg-white dark:text-slate-300 dark:hover:bg-slate-950'
              }`}
            >
              <Settings2 size={16} />
              通用
            </button>
            <button
              type="button"
              onClick={() => setSection('appearance')}
              className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${
                section === 'appearance'
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-200'
                  : 'text-slate-600 hover:bg-white dark:text-slate-300 dark:hover:bg-slate-950'
              }`}
            >
              <Palette size={16} />
              外观
            </button>
          </nav>
        </aside>

        <main className="min-w-0 flex-1">
          {section === 'general' && (
            <div className="space-y-6">
              <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
                <h2 className="text-base font-semibold">默认律师人格</h2>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {personalities.map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      onClick={() => setPersonality(item.value)}
                      className={`rounded-lg border p-4 text-left transition ${
                        personality === item.value
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30'
                          : 'border-slate-200 hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium">{item.label}</span>
                        {personality === item.value && <CheckCircle size={16} className="text-blue-600" />}
                      </div>
                      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{item.desc}</p>
                    </button>
                  ))}
                </div>
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h2 className="text-base font-semibold">本地对话记录</h2>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      当前浏览器保存了 {sessions.length} 条对话。
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={clearHistory}
                    disabled={sessions.length === 0}
                    className="rounded-md border border-red-200 px-3 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-900/60 dark:text-red-300 dark:hover:bg-red-950/30"
                  >
                    清除记录
                  </button>
                </div>
              </section>
            </div>
          )}

          {section === 'appearance' && (
            <div className="space-y-6">
              <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
                <h2 className="text-base font-semibold">主题</h2>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  {themes.map((item) => {
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.value}
                        type="button"
                        onClick={() => setTheme(item.value)}
                        className={`flex items-center justify-between rounded-lg border p-4 text-left transition ${
                          theme === item.value
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30'
                            : 'border-slate-200 hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700'
                        }`}
                      >
                        <span className="flex items-center gap-2 text-sm font-medium">
                          <Icon size={16} />
                          {item.label}
                        </span>
                        {theme === item.value && <CheckCircle size={16} className="text-blue-600" />}
                      </button>
                    );
                  })}
                </div>
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
                <h2 className="flex items-center gap-2 text-base font-semibold">
                  <Type size={17} />
                  字体大小
                </h2>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  {fontSizes.map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      onClick={() => ui.setFontSize(item.value)}
                      className={`rounded-lg border p-4 text-left transition ${
                        ui.settings.fontSize === item.value
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30'
                          : 'border-slate-200 hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{item.label}</span>
                        {ui.settings.fontSize === item.value && <CheckCircle size={16} className="text-blue-600" />}
                      </div>
                      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{item.desc}</p>
                    </button>
                  ))}
                </div>
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
                <h2 className="text-base font-semibold">界面密度</h2>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  {densities.map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      onClick={() => ui.setDensity(item.value)}
                      className={`rounded-lg border p-4 text-left transition ${
                        ui.settings.density === item.value
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30'
                          : 'border-slate-200 hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{item.label}</span>
                        {ui.settings.density === item.value && <CheckCircle size={16} className="text-blue-600" />}
                      </div>
                      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{item.desc}</p>
                    </button>
                  ))}
                </div>
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
                <h2 className="flex items-center gap-2 text-base font-semibold">
                  <Zap size={17} />
                  动效
                </h2>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => ui.setAnimationsEnabled(!ui.settings.animationsEnabled)}
                    className="flex items-center justify-between rounded-lg border border-slate-200 p-4 text-left transition hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700"
                  >
                    <span>
                      <span className="block font-medium">界面动画</span>
                      <span className="mt-1 block text-sm text-slate-500 dark:text-slate-400">控制过渡和淡入效果。</span>
                    </span>
                    <span className={`h-5 w-10 rounded-full p-0.5 transition ${ui.settings.animationsEnabled ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
                      <span className={`block h-4 w-4 rounded-full bg-white transition ${ui.settings.animationsEnabled ? 'translate-x-5' : ''}`} />
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => ui.setFireEffectEnabled(!ui.settings.fireEffectEnabled)}
                    className="flex items-center justify-between rounded-lg border border-slate-200 p-4 text-left transition hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700"
                  >
                    <span>
                      <span className="block font-medium">Logo 特效</span>
                      <span className="mt-1 block text-sm text-slate-500 dark:text-slate-400">控制首页和标识上的动态效果。</span>
                    </span>
                    <span className={`h-5 w-10 rounded-full p-0.5 transition ${ui.settings.fireEffectEnabled ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-700'}`}>
                      <span className={`block h-4 w-4 rounded-full bg-white transition ${ui.settings.fireEffectEnabled ? 'translate-x-5' : ''}`} />
                    </span>
                  </button>
                </div>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
