'use client';

import { useState, useEffect } from 'react';
import { Save, Loader2, CheckCircle, AlertCircle, User, Sliders, Palette, Trash2 } from 'lucide-react';
import { useChatStore, PersonalityType } from '@/store/chatStore';
import { useTheme } from '@/hooks/useTheme';
import { useSettings } from '@/hooks/useSettings';

type SettingSection = 'general' | 'model' | 'appearance';

// 五大人格配置
const personalities = [
  {
    id: 'machine' as PersonalityType,
    name: '冰冷机器',
    icon: '🤖',
    description: '纯粹理性，只给法条和判例，不带任何情感色彩',
    color: 'text-gray-800 dark:text-gray-200',
  },
  {
    id: 'empathy' as PersonalityType,
    name: '共情守护',
    icon: '💙',
    description: '温暖体贴，理解你的处境，提供情感支持和法律建议',
    color: 'text-blue-700 dark:text-blue-300',
  },
  {
    id: 'cost_expert' as PersonalityType,
    name: '成本专家',
    icon: '💰',
    description: '精打细算，帮你算清每一分钱，追求性价比最优解',
    color: 'text-green-700 dark:text-green-300',
  },
  {
    id: 'aggressive' as PersonalityType,
    name: '激进斗士',
    icon: '⚔️',
    description: '寸土必争，帮你找到所有可能的反击点和进攻策略',
    color: 'text-red-700 dark:text-red-300',
  },
  {
    id: 'educator' as PersonalityType,
    name: '普法导师',
    icon: '📚',
    description: '耐心讲解，用通俗语言帮你理解复杂的法律概念',
    color: 'text-purple-700 dark:text-purple-300',
  },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState<SettingSection>('general');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('https://api.groq.com/openai/v1');
  const [model, setModel] = useState('llama-3.1-70b-versatile');
  const [temperature, setTemperature] = useState(0.3);
  const [maxTokens, setMaxTokens] = useState(2048);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  
  const { personality, setPersonality, sessions } = useChatStore();
  const { theme, setTheme } = useTheme();
  const { settings, setFontSize, setDensity, setAnimationsEnabled, setFireEffectEnabled } = useSettings();

  // 从 localStorage 加载配置
  useEffect(() => {
    const savedApiKey = localStorage.getItem('sparklaw_api_key');
    const savedBaseUrl = localStorage.getItem('sparklaw_base_url');
    const savedModel = localStorage.getItem('sparklaw_model');
    const savedTemperature = localStorage.getItem('sparklaw_temperature');
    const savedMaxTokens = localStorage.getItem('sparklaw_max_tokens');

    if (savedApiKey) setApiKey(savedApiKey);
    if (savedBaseUrl) setBaseUrl(savedBaseUrl);
    if (savedModel) setModel(savedModel);
    if (savedTemperature) setTemperature(parseFloat(savedTemperature));
    if (savedMaxTokens) setMaxTokens(parseInt(savedMaxTokens));
  }, []);

  // 保存配置
  const handleSave = async () => {
    if (!apiKey.trim()) {
      setMessage({ type: 'error', text: '请输入 API Key' });
      return;
    }

    setSaving(true);
    setMessage(null);

    try {
      localStorage.setItem('sparklaw_api_key', apiKey);
      localStorage.setItem('sparklaw_base_url', baseUrl);
      localStorage.setItem('sparklaw_model', model);
      localStorage.setItem('sparklaw_temperature', temperature.toString());
      localStorage.setItem('sparklaw_max_tokens', maxTokens.toString());

      setMessage({ type: 'success', text: '配置已保存！刷新页面后生效。' });
    } catch (error: any) {
      setMessage({ type: 'error', text: `保存失败：${error.message}` });
    } finally {
      setSaving(false);
    }
  };

  // 清除所有历史记录
  const handleClearHistory = () => {
    sessions.forEach(session => {
      useChatStore.getState().deleteSession(session.id);
    });
    setShowClearConfirm(false);
    setMessage({ type: 'success', text: '所有历史记录已清除' });
  };

  // 脱敏显示 API Key
  const maskApiKey = (key: string) => {
    if (!key || key.length < 8) return key;
    return `${key.slice(0, 3)}***...***${key.slice(-3)}`;
  };

  // 预设配置
  const presets = [
    {
      name: 'Groq',
      baseUrl: 'https://api.groq.com/openai/v1',
      model: 'llama-3.1-70b-versatile',
      description: '免费、快速、强大',
    },
    {
      name: 'DeepSeek',
      baseUrl: 'https://api.deepseek.com/v1',
      model: 'deepseek-chat',
      description: '国内访问快，价格便宜',
    },
    {
      name: 'OpenAI',
      baseUrl: 'https://api.openai.com/v1',
      model: 'gpt-4o-mini',
      description: '经典选择',
    },
  ];

  const sections = [
    { id: 'general' as SettingSection, label: '通用', icon: User },
    { id: 'model' as SettingSection, label: '模型配置', icon: Sliders },
    { id: 'appearance' as SettingSection, label: '外观', icon: Palette },
  ];

  return (
    <div className="flex h-screen overflow-hidden">
      {/* 左侧导航 */}
      <aside className="w-56 border-r border-border bg-card">
        <div className="p-4">
          <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            设置
          </h2>
          <nav className="space-y-1">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`
                  flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-smooth
                  ${activeSection === section.id
                    ? 'bg-accent text-accent-foreground'
                    : 'text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground'
                  }
                `}
              >
                <section.icon size={16} />
                {section.label}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* 右侧内容 */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl p-8">
          {/* 通用设置 */}
          {activeSection === 'general' && (
            <div className="space-y-6">
              <div>
                <h1 className="text-lg font-semibold font-serif">通用</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  选择 AI 的回答风格和人格特征
                </p>
              </div>

              {/* 人格选择 */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium">AI 律师人格</h3>
                <div className="space-y-2">
                  {personalities.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setPersonality(p.id)}
                      className={`
                        w-full rounded-lg border p-4 text-left transition-smooth
                        ${personality === p.id
                          ? 'border-primary bg-accent ring-2 ring-primary/20'
                          : 'border-border bg-card hover:bg-accent/50'
                        }
                      `}
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-2xl">{p.icon}</span>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className={`text-sm font-medium ${p.color}`}>
                              {p.name}
                            </h4>
                            {personality === p.id && (
                              <CheckCircle size={14} className="text-primary" />
                            )}
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {p.description}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* 清除历史记录 */}
              <div className="border-t border-border pt-6">
                <h3 className="text-sm font-medium mb-3">数据管理</h3>
                {!showClearConfirm ? (
                  <button
                    onClick={() => setShowClearConfirm(true)}
                    className="flex items-center gap-2 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm font-medium text-destructive transition-smooth hover:bg-destructive/20"
                  >
                    <Trash2 size={16} />
                    清除所有历史记录
                  </button>
                ) : (
                  <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
                    <p className="text-sm text-destructive mb-3">
                      确定要清除所有 {sessions.length} 条历史记录吗？此操作不可恢复！
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={handleClearHistory}
                        className="flex-1 rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground transition-smooth hover:bg-destructive/90"
                      >
                        确认清除
                      </button>
                      <button
                        onClick={() => setShowClearConfirm(false)}
                        className="flex-1 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium transition-smooth hover:bg-accent"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* 关于 */}
              <div className="border-t border-border pt-6">
                <div className="rounded-lg border border-border bg-card p-4">
                  <h3 className="text-sm font-medium">关于 SparkLaw</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    版本：1.0.0
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    开源智能法律助手
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 模型配置 */}
          {activeSection === 'model' && (
            <div className="space-y-6">
              <div>
                <h1 className="text-lg font-semibold font-serif">模型配置</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  配置 LLM API 和模型参数
                </p>
              </div>

              <div className="space-y-4">
                {/* API Key */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    API Key
                  </label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="输入你的 API Key"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-smooth"
                  />
                  {apiKey && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      当前：{maskApiKey(apiKey)}
                    </p>
                  )}
                  <p className="mt-1 text-xs text-muted-foreground">
                    你的 API Key 将保存在浏览器本地，不会上传到服务器
                  </p>
                </div>

                {/* Base URL */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    API Base URL
                  </label>
                  <input
                    type="text"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="https://api.groq.com/openai/v1"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-smooth"
                  />
                </div>

                {/* Model */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    模型名称
                  </label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="llama-3.1-70b-versatile"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-smooth"
                  />
                </div>

                {/* Temperature */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Temperature（创作随机性）
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => setTemperature(parseFloat(e.target.value))}
                      className="flex-1"
                    />
                    <span className="text-sm font-mono text-foreground w-12 text-right">
                      {temperature.toFixed(1)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    0 = 严谨精确，1 = 创意发散
                  </p>
                </div>

                {/* Max Tokens */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Max Tokens（最大输出长度）
                  </label>
                  <input
                    type="number"
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                    placeholder="2048"
                    min="512"
                    max="8192"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-smooth"
                  />
                  <p className="mt-1 text-xs text-muted-foreground">
                    推荐：2048-4096
                  </p>
                </div>

                {/* 保存按钮 */}
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-smooth hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {saving ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      保存中...
                    </>
                  ) : (
                    <>
                      <Save size={16} />
                      保存配置
                    </>
                  )}
                </button>

                {/* 消息提示 */}
                {message && (
                  <div
                    className={`rounded-md p-3 flex items-start gap-2 text-sm ${
                      message.type === 'success'
                        ? 'bg-green-50 text-green-900 border border-green-200 dark:bg-green-950/30 dark:text-green-200 dark:border-green-800/50'
                        : 'bg-red-50 text-red-900 border border-red-200 dark:bg-red-950/30 dark:text-red-200 dark:border-red-800/50'
                    }`}
                  >
                    {message.type === 'success' ? (
                      <CheckCircle size={16} className="mt-0.5 flex-shrink-0 text-green-600 dark:text-green-400" />
                    ) : (
                      <AlertCircle size={16} className="mt-0.5 flex-shrink-0 text-red-600 dark:text-red-400" />
                    )}
                    <p>{message.text}</p>
                  </div>
                )}
              </div>

              {/* 预设配置 */}
              <div className="border-t border-border pt-6">
                <h3 className="text-sm font-medium mb-3">快速配置</h3>
                <div className="grid grid-cols-1 gap-2">
                  {presets.map((preset) => (
                    <button
                      key={preset.name}
                      onClick={() => {
                        setBaseUrl(preset.baseUrl);
                        setModel(preset.model);
                      }}
                      className="rounded-md border border-border bg-card p-3 text-left transition-smooth hover:bg-accent"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="text-sm font-medium text-foreground">{preset.name}</h4>
                          <p className="text-xs text-muted-foreground">{preset.description}</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* 使用说明 */}
              <div className="rounded-md border border-blue-200 bg-blue-50 p-4 dark:border-blue-800/50 dark:bg-blue-950/30">
                <h4 className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-2">
                  💡 使用说明
                </h4>
                <ul className="space-y-1 text-xs text-blue-800 dark:text-blue-200">
                  <li>• Groq：免费且快速，推荐使用</li>
                  <li>• DeepSeek：国内访问快，价格便宜</li>
                  <li>• OpenAI：需要国际网络访问</li>
                </ul>
              </div>
            </div>
          )}

          {/* 外观设置 */}
          {activeSection === 'appearance' && (
            <div className="space-y-6">
              <div>
                <h1 className="text-lg font-semibold font-serif">外观</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  自定义界面主题和显示设置
                </p>
              </div>

              <div className="space-y-6">
                {/* 主题选择 */}
                <div>
                  <h3 className="text-sm font-medium mb-3">主题</h3>
                  <div className="grid grid-cols-3 gap-3">
                    <button
                      onClick={() => setTheme('light')}
                      className={`group relative rounded-lg border-2 p-4 transition-smooth hover:border-primary ${
                        theme === 'light' ? 'border-primary bg-accent' : 'border-border bg-card'
                      }`}
                    >
                      <div className="mb-3 flex h-16 items-center justify-center rounded-md bg-white border border-gray-200">
                        <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500"></div>
                      </div>
                      <p className="text-center text-sm font-medium text-foreground">浅色</p>
                      {theme === 'light' && (
                        <div className="absolute top-2 right-2">
                          <CheckCircle size={16} className="text-primary" />
                        </div>
                      )}
                    </button>

                    <button
                      onClick={() => setTheme('dark')}
                      className={`group relative rounded-lg border-2 p-4 transition-smooth hover:border-primary ${
                        theme === 'dark' ? 'border-primary bg-accent' : 'border-border bg-card'
                      }`}
                    >
                      <div className="mb-3 flex h-16 items-center justify-center rounded-md bg-slate-900">
                        <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-400 to-purple-400"></div>
                      </div>
                      <p className="text-center text-sm font-medium text-foreground">深色</p>
                      {theme === 'dark' && (
                        <div className="absolute top-2 right-2">
                          <CheckCircle size={16} className="text-primary" />
                        </div>
                      )}
                    </button>

                    <button
                      onClick={() => setTheme('system')}
                      className={`group relative rounded-lg border-2 p-4 transition-smooth hover:border-primary ${
                        theme === 'system' ? 'border-primary bg-accent' : 'border-border bg-card'
                      }`}
                    >
                      <div className="mb-3 flex h-16 items-center justify-center rounded-md bg-gradient-to-r from-white via-gray-400 to-slate-900">
                        <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500"></div>
                      </div>
                      <p className="text-center text-sm font-medium text-foreground">跟随系统</p>
                      {theme === 'system' && (
                        <div className="absolute top-2 right-2">
                          <CheckCircle size={16} className="text-primary" />
                        </div>
                      )}
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    也可以使用侧边栏底部的主题切换按钮（快速切换浅色/深色）
                  </p>
                </div>

                {/* 字体大小 */}
                <div>
                  <h3 className="text-sm font-medium mb-3">字体大小</h3>
                  <div className="space-y-2">
                    <button 
                      onClick={() => setFontSize('small')}
                      className={`w-full rounded-lg border-2 p-3 text-left transition-smooth ${
                        settings.fontSize === 'small' 
                          ? 'border-primary bg-accent' 
                          : 'border-border bg-card hover:bg-accent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">小</p>
                          <p className="text-xs text-muted-foreground">紧凑显示，适合小屏幕或显示更多内容</p>
                          <p className="text-xs text-muted-foreground mt-1">基准：12px，按钮/输入框：11px</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground font-mono">12px</span>
                          {settings.fontSize === 'small' && (
                            <CheckCircle size={16} className="text-primary" />
                          )}
                        </div>
                      </div>
                    </button>

                    <button 
                      onClick={() => setFontSize('medium')}
                      className={`w-full rounded-lg border-2 p-3 text-left transition-smooth ${
                        settings.fontSize === 'medium' 
                          ? 'border-primary bg-accent' 
                          : 'border-border bg-card hover:bg-accent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">中（推荐）</p>
                          <p className="text-xs text-muted-foreground">平衡的阅读体验，适合大多数场景</p>
                          <p className="text-xs text-muted-foreground mt-1">基准：14px，按钮/输入框：14px</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground font-mono">14px</span>
                          {settings.fontSize === 'medium' && (
                            <CheckCircle size={16} className="text-primary" />
                          )}
                        </div>
                      </div>
                    </button>

                    <button 
                      onClick={() => setFontSize('large')}
                      className={`w-full rounded-lg border-2 p-3 text-left transition-smooth ${
                        settings.fontSize === 'large' 
                          ? 'border-primary bg-accent' 
                          : 'border-border bg-card hover:bg-accent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">大</p>
                          <p className="text-xs text-muted-foreground">舒适阅读，适合大屏幕或视力较弱用户</p>
                          <p className="text-xs text-muted-foreground mt-1">基准：16px，按钮/输入框：16px</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground font-mono">16px</span>
                          {settings.fontSize === 'large' && (
                            <CheckCircle size={16} className="text-primary" />
                          )}
                        </div>
                      </div>
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    💡 字体大小会影响所有文字、按钮、输入框等元素，立即生效
                  </p>
                </div>

                {/* 界面密度 */}
                <div>
                  <h3 className="text-sm font-medium mb-3">界面密度</h3>
                  <div className="space-y-2">
                    <button 
                      onClick={() => setDensity('compact')}
                      className={`w-full rounded-lg border-2 p-3 text-left transition-smooth ${
                        settings.density === 'compact' 
                          ? 'border-primary bg-accent' 
                          : 'border-border bg-card hover:bg-accent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">紧凑</p>
                          <p className="text-xs text-muted-foreground">更多内容，更少空白，适合小屏幕</p>
                          <p className="text-xs text-muted-foreground mt-1">间距：0.5rem，按钮内边距减小</p>
                        </div>
                        {settings.density === 'compact' && (
                          <CheckCircle size={16} className="text-primary" />
                        )}
                      </div>
                    </button>

                    <button 
                      onClick={() => setDensity('standard')}
                      className={`w-full rounded-lg border-2 p-3 text-left transition-smooth ${
                        settings.density === 'standard' 
                          ? 'border-primary bg-accent' 
                          : 'border-border bg-card hover:bg-accent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">标准（推荐）</p>
                          <p className="text-xs text-muted-foreground">平衡的视觉体验，适合大多数场景</p>
                          <p className="text-xs text-muted-foreground mt-1">间距：1rem，默认内边距</p>
                        </div>
                        {settings.density === 'standard' && (
                          <CheckCircle size={16} className="text-primary" />
                        )}
                      </div>
                    </button>

                    <button 
                      onClick={() => setDensity('relaxed')}
                      className={`w-full rounded-lg border-2 p-3 text-left transition-smooth ${
                        settings.density === 'relaxed' 
                          ? 'border-primary bg-accent' 
                          : 'border-border bg-card hover:bg-accent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-foreground">宽松</p>
                          <p className="text-xs text-muted-foreground">更多空白，更舒适，适合大屏幕</p>
                          <p className="text-xs text-muted-foreground mt-1">间距：1.5rem，按钮内边距增大</p>
                        </div>
                        {settings.density === 'relaxed' && (
                          <CheckCircle size={16} className="text-primary" />
                        )}
                      </div>
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    💡 界面密度会影响按钮、卡片、间距等元素，立即生效
                  </p>
                </div>

                {/* 动画效果 */}
                <div>
                  <h3 className="text-sm font-medium mb-3">动画效果</h3>
                  <div className="rounded-lg border border-border bg-card p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-foreground">启用动画</p>
                        <p className="text-xs text-muted-foreground">包括过渡、淡入淡出等效果</p>
                      </div>
                      <button
                        onClick={() => setAnimationsEnabled(!settings.animationsEnabled)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          settings.animationsEnabled ? 'bg-primary' : 'bg-muted'
                        }`}
                      >
                        <span
                          className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                            settings.animationsEnabled ? 'translate-x-5' : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    关闭动画可以提升性能
                  </p>
                </div>

                {/* 火焰效果 */}
                <div>
                  <h3 className="text-sm font-medium mb-3">特效</h3>
                  <div className="rounded-lg border border-border bg-card p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-foreground">火焰天秤效果 🔥⚖️</p>
                        <p className="text-xs text-muted-foreground">在 Logo 上显示动态火焰效果</p>
                      </div>
                      <button
                        onClick={() => setFireEffectEnabled(!settings.fireEffectEnabled)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          settings.fireEffectEnabled ? 'bg-primary' : 'bg-muted'
                        }`}
                      >
                        <span
                          className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                            settings.fireEffectEnabled ? 'translate-x-5' : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                </div>

                {/* 预览 */}
                <div className="border-t border-border pt-6">
                  <h3 className="text-sm font-medium mb-3">实时预览</h3>
                  <div className="rounded-lg border border-border bg-card p-6">
                    <div className="flex items-center gap-4 mb-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-legal shadow-lg">
                        <span className="text-2xl">⚖️</span>
                      </div>
                      <div>
                        <h4 className="font-semibold text-foreground">SparkLaw 智能法律助手</h4>
                        <p className="text-muted-foreground">开源 · 免费 · 强大</p>
                      </div>
                    </div>
                    <div className="rounded-md border border-border bg-background p-4 space-y-3">
                      <div>
                        <h3 className="font-medium text-foreground mb-2">当前设置</h3>
                        <div className="space-y-1 text-muted-foreground">
                          <p>• 字体大小：{settings.fontSize === 'small' ? '小 (12px)' : settings.fontSize === 'medium' ? '中 (14px)' : '大 (16px)'}</p>
                          <p>• 界面密度：{settings.density === 'compact' ? '紧凑' : settings.density === 'standard' ? '标准' : '宽松'}</p>
                          <p>• 动画效果：{settings.animationsEnabled ? '已启用' : '已禁用'}</p>
                          <p>• 火焰特效：{settings.fireEffectEnabled ? '已启用' : '已禁用'}</p>
                        </div>
                      </div>
                      <div className="border-t border-border pt-3">
                        <p className="text-foreground">
                          这是一段示例文本，用于预览当前的字体大小和界面密度设置。您可以在上方调整设置，实时查看效果变化。
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-smooth hover:bg-primary/90 no-density">
                          示例按钮
                        </button>
                        <input 
                          type="text" 
                          placeholder="示例输入框" 
                          className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground"
                          readOnly
                        />
                      </div>
                    </div>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    💡 预览区域会实时反映您的设置变化
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
