/**
 * Theme Hook - Dark Mode Support
 * Manages application theme state and persistence
 */

import { useEffect, useState, useCallback, createContext, useContext, ReactNode } from 'react'

export type Theme = 'light' | 'dark' | 'system'

interface ThemeContextType {
  theme: Theme
  isDark: boolean
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

/**
 * Hook to use theme context
 * Must be used within ThemeProvider
 */
export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider')
  }
  return context
}

/**
 * Determine if dark mode should be active
 */
const isDarkMode = (theme: Theme): boolean => {
  if (theme === 'dark') return true
  if (theme === 'light') return false

  // System preference
  if (typeof window !== 'undefined') {
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  }

  return false
}

export interface ThemeProviderProps {
  children: ReactNode
  storageKey?: string
}

/**
 * Theme Provider Component
 * Wraps the app to provide theme context
 */
export const ThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  storageKey = 'theme-preference',
}) => {
  const [theme, setThemeState] = useState<Theme>('system')
  const [isDark, setIsDark] = useState(false)
  const [mounted, setMounted] = useState(false)

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    try {
      // Get stored preference or default to system
      const stored = localStorage.getItem(storageKey) as Theme | null
      const initialTheme = stored || 'system'

      setThemeState(initialTheme)
      setIsDark(isDarkMode(initialTheme))

      // Apply theme to DOM
      applyTheme(initialTheme)

      // Listen for system theme changes
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handleChange = (e: MediaQueryListEvent) => {
        if (initialTheme === 'system') {
          setIsDark(e.matches)
          document.documentElement.classList.toggle('dark', e.matches)
        }
      }

      mediaQuery.addEventListener('change', handleChange)
      setMounted(true)

      return () => mediaQuery.removeEventListener('change', handleChange)
    } catch (error) {
      console.error('Error initializing theme:', error)
      setMounted(true)
    }
  }, [storageKey])

  const applyTheme = useCallback((newTheme: Theme) => {
    const isDarkMode_ = isDarkMode(newTheme)

    // Update DOM
    if (isDarkMode_) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }

    // Update meta theme-color
    const metaThemeColor = document.querySelector('meta[name="theme-color"]')
    if (metaThemeColor) {
      metaThemeColor.setAttribute(
        'content',
        isDarkMode_ ? '#1f2937' : '#ffffff'
      )
    }
  }, [])

  const setTheme = useCallback(
    (newTheme: Theme) => {
      setThemeState(newTheme)
      setIsDark(isDarkMode(newTheme))
      applyTheme(newTheme)

      // Persist preference
      try {
        localStorage.setItem(storageKey, newTheme)
      } catch (error) {
        console.error('Error saving theme preference:', error)
      }
    },
    [applyTheme, storageKey]
  )

  const toggleTheme = useCallback(() => {
    setTheme(isDark ? 'light' : 'dark')
  }, [isDark, setTheme])

  // Prevent flash of wrong theme (during hydration)
  if (!mounted) {
    return <>{children}</>
  }

  return (
    <ThemeContext.Provider
      value={{
        theme,
        isDark,
        setTheme,
        toggleTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export default useTheme
