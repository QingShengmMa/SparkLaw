'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * @deprecated 此页面已由 /tools/calculators 取代。
 * 保留此文件仅为防止旧链接 404，访问时自动重定向。
 */
export default function CalculatorPageRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/tools/calculators'); }, [router]);
  return null;
}
