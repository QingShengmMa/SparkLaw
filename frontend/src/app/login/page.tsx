'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useEffect, useState } from 'react';
import { ArrowRight, LockKeyhole, Scale } from 'lucide-react';
import { getAuthStatus, login } from '@/lib/api';

function safeNextPath(value: string | null): string {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return '/tools';
  return value;
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nextPath, setNextPath] = useState('/tools');
  const [registrationEnabled, setRegistrationEnabled] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const next = safeNextPath(params.get('next'));
    setNextPath(next);
    getAuthStatus()
      .then((status) => {
        setRegistrationEnabled(status.registration_enabled);
        if (status.authenticated) router.replace(next);
      })
      .catch(() => setRegistrationEnabled(true));
  }, [router]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      router.replace(nextPath);
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败，请稍后重试。');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F6F8FB] px-6 text-slate-900 dark:bg-[#0B0D14] dark:text-slate-100">
      <div className="w-full max-w-[420px] rounded-lg border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="mb-8">
          <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-lg bg-blue-600 text-white">
            <Scale size={22} />
          </div>
          <h1 className="text-2xl font-semibold tracking-normal">登录 SparkLaw</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
            使用站点账号后，所有大模型调用都会走服务端统一额度。
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium">邮箱</span>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              autoComplete="email"
              className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-blue-950"
              required
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium">密码</span>
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              autoComplete="current-password"
              className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-blue-950"
              required
            />
          </label>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <LockKeyhole size={16} />
            {loading ? '登录中' : '登录'}
          </button>
        </form>

        <div className="mt-6 flex items-center justify-between text-sm">
          <Link href="/" className="text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white">
            返回首页
          </Link>
          {registrationEnabled && (
            <Link href="/register" className="inline-flex items-center gap-1 font-medium text-blue-600 hover:text-blue-700">
              注册账号 <ArrowRight size={14} />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
