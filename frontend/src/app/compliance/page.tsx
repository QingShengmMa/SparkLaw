'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** @deprecated 已迁移至 /tools/compliance，此页面自动重定向。 */
export default function ComplianceRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/tools/compliance'); }, [router]);
  return null;
}
