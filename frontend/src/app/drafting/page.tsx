'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** @deprecated 已迁移至 /tools/drafting，此页面自动重定向。 */
export default function DraftingRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/tools/drafting'); }, [router]);
  return null;
}
