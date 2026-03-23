import { useState, useEffect } from 'react';

export type FontSize = 'small' | 'medium' | 'large';
export type Density = 'compact' | 'standard' | 'relaxed';

interface Settings {
  fontSize: FontSize;
  density: Density;
  animationsEnabled: boolean;
  fireEffectEnabled: boolean;
}

const defaultSettings: Settings = {
  fontSize: 'medium',
  density: 'standard',
  animationsEnabled: true,
  fireEffectEnabled: true,
};

export function useSettings() {
  const [settings, setSettingsState] = useState<Settings>(defaultSettings);

  useEffect(() => {
    // 从 localStorage 读取设置
    const savedFontSize = localStorage.getItem('sparklaw_font_size') as FontSize;
    const savedDensity = localStorage.getItem('sparklaw_density') as Density;
    const savedAnimations = localStorage.getItem('sparklaw_animations');
    const savedFireEffect = localStorage.getItem('sparklaw_fire_effect');

    setSettingsState({
      fontSize: savedFontSize || 'medium',
      density: savedDensity || 'standard',
      animationsEnabled: savedAnimations !== 'false',
      fireEffectEnabled: savedFireEffect !== 'false',
    });

    // 应用设置到 DOM
    applySettings({
      fontSize: savedFontSize || 'medium',
      density: savedDensity || 'standard',
      animationsEnabled: savedAnimations !== 'false',
      fireEffectEnabled: savedFireEffect !== 'false',
    });
  }, []);

  const applySettings = (newSettings: Settings) => {
    const root = document.documentElement;

    // 应用字体大小
    root.classList.remove('font-small', 'font-medium', 'font-large');
    root.classList.add(`font-${newSettings.fontSize}`);

    // 应用界面密度
    root.classList.remove('density-compact', 'density-standard', 'density-relaxed');
    root.classList.add(`density-${newSettings.density}`);

    // 应用动画设置
    if (newSettings.animationsEnabled) {
      root.classList.remove('no-animations');
    } else {
      root.classList.add('no-animations');
    }

    // 应用火焰效果设置
    if (newSettings.fireEffectEnabled) {
      root.classList.remove('no-fire-effect');
    } else {
      root.classList.add('no-fire-effect');
    }
  };

  const setFontSize = (fontSize: FontSize) => {
    const newSettings = { ...settings, fontSize };
    setSettingsState(newSettings);
    localStorage.setItem('sparklaw_font_size', fontSize);
    applySettings(newSettings);
  };

  const setDensity = (density: Density) => {
    const newSettings = { ...settings, density };
    setSettingsState(newSettings);
    localStorage.setItem('sparklaw_density', density);
    applySettings(newSettings);
  };

  const setAnimationsEnabled = (enabled: boolean) => {
    const newSettings = { ...settings, animationsEnabled: enabled };
    setSettingsState(newSettings);
    localStorage.setItem('sparklaw_animations', enabled.toString());
    applySettings(newSettings);
  };

  const setFireEffectEnabled = (enabled: boolean) => {
    const newSettings = { ...settings, fireEffectEnabled: enabled };
    setSettingsState(newSettings);
    localStorage.setItem('sparklaw_fire_effect', enabled.toString());
    applySettings(newSettings);
  };

  return {
    settings,
    setFontSize,
    setDensity,
    setAnimationsEnabled,
    setFireEffectEnabled,
  };
}
