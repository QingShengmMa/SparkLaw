import { Scale as LucideScale } from 'lucide-react';
import { useSettings } from '@/hooks/useSettings';

interface ScaleIconProps {
  size?: number;
  className?: string;
  withFire?: boolean; // 是否显示火焰效果
}

export default function ScaleIcon({ size = 24, className = '', withFire = false }: ScaleIconProps) {
  const { settings } = useSettings();
  
  // 如果全局禁用火焰效果，则不显示
  const shouldShowFire = withFire && settings.fireEffectEnabled;
  
  if (!shouldShowFire) {
    return <LucideScale size={size} className={className} strokeWidth={2.5} />;
  }

  // 根据尺寸调整火焰大小
  const isLarge = size >= 60;
  const particleSize = isLarge ? 8 : 4;
  const particleCount = isLarge ? 6 : 3;
  const blurClass = isLarge ? 'blur-xl' : 'blur-md';
  const glowClass = isLarge ? 'drop-shadow-[0_0_16px_rgba(251,146,60,0.8)]' : 'drop-shadow-[0_0_8px_rgba(251,146,60,0.5)]';

  // 带火焰效果的版本
  return (
    <div className="relative inline-flex items-center justify-center fire-scale-container">
      {/* 火焰光晕效果 - 增强版 */}
      <div className="absolute inset-0 fire-glow">
        <div className={`absolute inset-0 rounded-full bg-gradient-to-t from-orange-500/40 via-red-500/30 to-yellow-500/20 ${blurClass}`}></div>
      </div>
      
      {/* 火焰粒子 - 增强版 */}
      <div className="absolute inset-0">
        {[...Array(particleCount)].map((_, i) => (
          <div 
            key={i}
            className={`fire-particle ${isLarge ? 'fire-particle-large' : 'fire-particle-small'}`}
            style={{
              width: `${particleSize}px`,
              height: `${particleSize}px`,
              bottom: '-4px',
              left: `${20 + (i * (60 / (particleCount - 1)))}%`,
              animationDelay: `${i * (2 / particleCount)}s`
            }}
          ></div>
        ))}
      </div>
      
      {/* 天秤图标 */}
      <LucideScale 
        size={size} 
        className={`relative z-10 ${className} ${glowClass}`} 
        strokeWidth={2.5} 
      />
    </div>
  );
}
