'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** @deprecated 模拟法庭已迁移至顶级路由 /court，此页面自动重定向。 */
export default function MockCourtRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/court'); }, [router]);
  return null;
}
