'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** @deprecated 已迁移至 /tools/evidence，此页面自动重定向。 */
export default function EvidenceRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/tools/evidence'); }, [router]);
  return null;
}
