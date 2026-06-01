'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { LogOut, RefreshCw, Scale, WalletCards } from 'lucide-react';
import { AuthResponse, UsageBucket, getCurrentUser, logout } from '@/lib/api';

function formatTokens(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value || 0);
}

function formatUsd(value: number): string {
  return `$${Number(value || 0).toFixed(6)}`;
}

function UsageStat({ label, bucket }: { label: string; bucket: UsageBucket }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
      <div className="text-sm text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-3 text-2xl font-semibold text-slate-900 dark:text-white">
        {formatTokens(bucket.total_tokens)}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-xs text-slate-500 dark:text-slate-400">
        <span>调用 {bucket.calls || 0} 次</span>
        <span className="text-right">{formatUsd(bucket.total_cost_usd)}</span>
        <span>输入 {formatTokens(bucket.input_tokens)}</span>
        <span className="text-right">输出 {formatTokens(bucket.output_tokens)}</span>
      </div>
    </div>
  );
}

export default function AccountPage() {
  const router = useRouter();
  const [data, setData] = useState<AuthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const providerRows = useMemo(() => data?.usage.by_provider ?? [], [data]);

  async function load() {
    setLoading(true);
    setError('');
    try {
      setData(await getCurrentUser());
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法加载账号信息。');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleLogout() {
    await logout();
    router.replace('/login');
  }

  if (loading && !data) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500 dark:text-slate-400">
        正在加载个人中心
      </div>
    );
  }

  return (
    <div className="min-h-full bg-[#F7F9FC] px-8 py-8 text-slate-900 dark:bg-[#0B0D14] dark:text-slate-100">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 flex flex-col gap-4 border-b border-slate-200 pb-6 dark:border-slate-800 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600 text-white">
              <Scale size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">个人中心</h1>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                查看登录账号、模型路由用量和估算成本。
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200 dark:hover:bg-slate-900"
            >
              <RefreshCw size={15} />
              刷新
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
            >
              <LogOut size={15} />
              退出
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300">
            {error}
          </div>
        )}

        {data && (
          <div className="space-y-6">
            <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-300">
                  <WalletCards size={20} />
                </div>
                <div>
                  <div className="font-medium">{data.user.display_name}</div>
                  <div className="text-sm text-slate-500 dark:text-slate-400">{data.user.email}</div>
                </div>
                <span className="ml-auto rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-900 dark:text-slate-300">
                  {data.user.role}
                </span>
              </div>
            </section>

            <section className="grid gap-4 md:grid-cols-3">
              <UsageStat label="今日用量" bucket={data.usage.today} />
              <UsageStat label="本月用量" bucket={data.usage.month} />
              <UsageStat label="累计用量" bucket={data.usage.total} />
            </section>

            <section className="rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
              <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
                <h2 className="text-sm font-semibold">供应商明细</h2>
              </div>
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {providerRows.length === 0 ? (
                  <div className="px-5 py-8 text-sm text-slate-500 dark:text-slate-400">
                    还没有大模型调用记录。
                  </div>
                ) : (
                  providerRows.map((row) => (
                    <div key={`${row.provider}-${row.model}`} className="grid gap-3 px-5 py-4 text-sm md:grid-cols-[1.2fr_1fr_1fr_1fr] md:items-center">
                      <div>
                        <div className="font-medium">{row.provider}</div>
                        <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{row.model}</div>
                      </div>
                      <div>调用 {row.calls} 次</div>
                      <div>{formatTokens(row.total_tokens)} tokens</div>
                      <div className="md:text-right">{formatUsd(row.total_cost_usd)}</div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
