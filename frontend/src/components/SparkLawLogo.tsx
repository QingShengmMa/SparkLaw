'use client';

import { useEffect, useState } from 'react';

interface SparkLawLogoProps {
  size?: number;
  className?: string;
}

export default function SparkLawLogo({ size = 40, className = '' }: SparkLawLogoProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className={`relative ${className}`} style={{ width: size, height: size }}>
      {/* 火焰动画 SVG */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="animate-pulse"
      >
        {/* 天平底座 */}
        <rect
          x="45"
          y="75"
          width="10"
          height="20"
          fill="url(#gradient1)"
          className="transition-all duration-300"
        />
        
        {/* 天平横梁 */}
        <rect
          x="20"
          y="70"
          width="60"
          height="4"
          fill="url(#gradient1)"
          className="transition-all duration-300"
        />
        
        {/* 左侧天平盘 */}
        <ellipse
          cx="30"
          cy="65"
          rx="12"
          ry="4"
          fill="url(#gradient2)"
          className="transition-all duration-300"
        />
        
        {/* 右侧天平盘 */}
        <ellipse
          cx="70"
          cy="65"
          rx="12"
          ry="4"
          fill="url(#gradient2)"
          className="transition-all duration-300"
        />
        
        {/* 火焰 1 - 中心 */}
        <path
          d="M 50 60 Q 45 45 50 30 Q 55 45 50 60 Z"
          fill="url(#flameGradient1)"
          className="animate-flame-flicker"
        >
          <animateTransform
            attributeName="transform"
            type="scale"
            values="1;1.1;1"
            dur="2s"
            repeatCount="indefinite"
          />
        </path>
        
        {/* 火焰 2 - 左侧 */}
        <path
          d="M 40 55 Q 37 45 40 35 Q 43 45 40 55 Z"
          fill="url(#flameGradient2)"
          className="animate-flame-flicker"
          style={{ animationDelay: '0.3s' }}
        >
          <animateTransform
            attributeName="transform"
            type="scale"
            values="1;1.15;1"
            dur="1.8s"
            repeatCount="indefinite"
          />
        </path>
        
        {/* 火焰 3 - 右侧 */}
        <path
          d="M 60 55 Q 57 45 60 35 Q 63 45 60 55 Z"
          fill="url(#flameGradient2)"
          className="animate-flame-flicker"
          style={{ animationDelay: '0.6s' }}
        >
          <animateTransform
            attributeName="transform"
            type="scale"
            values="1;1.15;1"
            dur="2.2s"
            repeatCount="indefinite"
          />
        </path>
        
        {/* 火花粒子 */}
        <circle cx="35" cy="40" r="1.5" fill="#FCD34D" className="animate-spark">
          <animate
            attributeName="opacity"
            values="0;1;0"
            dur="1.5s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="cy"
            values="40;25;40"
            dur="1.5s"
            repeatCount="indefinite"
          />
        </circle>
        
        <circle cx="65" cy="45" r="1.5" fill="#FCD34D" className="animate-spark" style={{ animationDelay: '0.5s' }}>
          <animate
            attributeName="opacity"
            values="0;1;0"
            dur="1.8s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="cy"
            values="45;30;45"
            dur="1.8s"
            repeatCount="indefinite"
          />
        </circle>
        
        {/* 渐变定义 */}
        <defs>
          {/* 天平渐变 */}
          <linearGradient id="gradient1" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#D97706" />
          </linearGradient>
          
          <linearGradient id="gradient2" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FBBF24" />
            <stop offset="100%" stopColor="#F59E0B" />
          </linearGradient>
          
          {/* 火焰渐变 1 - 中心火焰 */}
          <linearGradient id="flameGradient1" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FEF3C7" />
            <stop offset="30%" stopColor="#FCD34D" />
            <stop offset="60%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#DC2626" />
          </linearGradient>
          
          {/* 火焰渐变 2 - 侧面火焰 */}
          <linearGradient id="flameGradient2" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FCD34D" />
            <stop offset="50%" stopColor="#F97316" />
            <stop offset="100%" stopColor="#DC2626" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}
