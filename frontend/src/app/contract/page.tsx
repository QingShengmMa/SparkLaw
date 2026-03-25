'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** @deprecated 已迁移至 /tools/contract-review，此页面自动重定向。 */
export default function ContractRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/tools/contract-review'); }, [router]);
  return null;
}
