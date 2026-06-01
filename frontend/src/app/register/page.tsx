'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useEffect, useState } from 'react';
import { Scale, UserPlus } from 'lucide-react';
import { getAuthStatus, registerAccount } from '@/lib/api';

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [registrationEnabled, setRegistrationEnabled] = useState(true);
  const [bootstrapRequired, setBootstrapRequired] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getAuthStatus()
      .then((status) => {
        setRegistrationEnabled(status.registration_enabled);
        setBootstrapRequired(status.bootstrap_required);
        if (status.authenticated) router.replace('/account');
      })
      .catch(() => setRegistrationEnabled(true));
  }, [router]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      await registerAccount({
        email,
        password,
        displayName: displayName || email.split('@')[0],
        inviteCode,
      });
      router.replace('/account');
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册失败，请稍后重试。');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F6F8FB] px-6 text-slate-900 dark:bg-[#0B0D14] dark:text-slate-100">
      <div className="w-full max-w-[460px] rounded-lg border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="mb-8">
          <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-lg bg-blue-600 text-white">
            <Scale size={22} />
          </div>
          <h1 className="text-2xl font-semibold tracking-normal">
            {bootstrapRequired ? '创建第一个管理员账号' : '注册 SparkLaw'}
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
            注册后即可使用服务端统一配置的 Groq 与 DeepSeek 额度。
          </p>
        </div>

        {!registrationEnabled ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
            当前站点暂未开放新用户注册。
          </div>
        ) : (
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
              <span className="text-sm font-medium">昵称</span>
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                type="text"
                autoComplete="name"
                className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-blue-950"
                placeholder="留空则使用邮箱前缀"
              />
            </label>

            <label className="block">
              <span className="text-sm font-medium">密码</span>
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="new-password"
                minLength={10}
                className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-blue-950"
                required
              />
              <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">至少 10 位。</span>
            </label>

            <label className="block">
              <span className="text-sm font-medium">邀请码</span>
              <input
                value={inviteCode}
                onChange={(event) => setInviteCode(event.target.value)}
                type="text"
                className="mt-2 w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-900 dark:focus:ring-blue-950"
                placeholder="未配置邀请码时可留空"
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
              <UserPlus size={16} />
              {loading ? '创建中' : '创建账号'}
            </button>
          </form>
        )}

        <div className="mt-6 text-sm">
          <Link href="/login" className="font-medium text-blue-600 hover:text-blue-700">
            已有账号，去登录
          </Link>
        </div>
      </div>
    </div>
  );
}
