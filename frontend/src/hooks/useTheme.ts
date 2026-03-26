import { useState, useEffect, useCallback } from 'react';

export type Theme = 'light' | 'dark' | 'system';

const THEME_STORAGE_KEY = 'sparklaw_theme';
const THEME_EVENT = 'sparklaw-theme-change';

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>('system');
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('dark');

  const applyTheme = useCallback((newTheme: Theme) => {
    const actualTheme: 'light' | 'dark' =
      newTheme === 'system'
        ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
        : newTheme;

    setResolvedTheme(actualTheme);

    if (actualTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []);

  useEffect(() => {
    const savedTheme = (localStorage.getItem(THEME_STORAGE_KEY) as Theme) || 'system';
    setThemeState(savedTheme);
    applyTheme(savedTheme);
  }, [applyTheme]);

  useEffect(() => {
    applyTheme(theme);
  }, [theme, applyTheme]);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemThemeChange = () => {
      if (theme === 'system') {
        applyTheme('system');
      }
    };

    mediaQuery.addEventListener('change', handleSystemThemeChange);
    return () => mediaQuery.removeEventListener('change', handleSystemThemeChange);
  }, [theme, applyTheme]);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== THEME_STORAGE_KEY) return;
      const nextTheme = (event.newValue as Theme) || 'system';
      setThemeState(nextTheme);
      applyTheme(nextTheme);
    };

    const handleThemeEvent = (event: Event) => {
      const customEvent = event as CustomEvent<Theme>;
      const nextTheme = customEvent.detail || 'system';
      setThemeState(nextTheme);
      applyTheme(nextTheme);
    };

    window.addEventListener('storage', handleStorage);
    window.addEventListener(THEME_EVENT, handleThemeEvent as EventListener);

    return () => {
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener(THEME_EVENT, handleThemeEvent as EventListener);
    };
  }, [applyTheme]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    applyTheme(newTheme);
    window.dispatchEvent(new CustomEvent<Theme>(THEME_EVENT, { detail: newTheme }));
  };

  return { theme, resolvedTheme, setTheme };
}
