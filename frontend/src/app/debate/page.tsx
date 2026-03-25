'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** @deprecated 已迁移至 /tools/mock-court，此页面自动重定向。 */
export default function DebateRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/tools/mock-court'); }, [router]);
  return null;
}
