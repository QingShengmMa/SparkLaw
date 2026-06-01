'use client';

import { useEffect, useMemo, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Scale } from 'lucide-react';
import { getAuthStatus } from '@/lib/api';

const PUBLIC_ROUTES = new Set(['/', '/login', '/register']);

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const isPublicRoute = useMemo(() => PUBLIC_ROUTES.has(pathname), [pathname]);

  useEffect(() => {
    let cancelled = false;

    async function verify() {
      if (isPublicRoute) {
        setChecking(false);
        return;
      }

      try {
        const status = await getAuthStatus();
        if (!cancelled && !status.authenticated) {
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
          return;
        }
      } catch {
        if (!cancelled) {
          router.replace(`/login?next=${encodeURIComponent(pathname)}`);
          return;
        }
      }

      if (!cancelled) setChecking(false);
    }

    setChecking(true);
    verify();
    return () => {
      cancelled = true;
    };
  }, [isPublicRoute, pathname, router]);

  if (checking && !isPublicRoute) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-[#FDFDFF] text-slate-600 dark:bg-[#0B0D14] dark:text-slate-300">
        <div className="flex items-center gap-3 text-sm">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white">
            <Scale size={18} />
          </span>
          正在确认登录状态
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
