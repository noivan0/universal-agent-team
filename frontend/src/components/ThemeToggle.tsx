/**
 * Theme Toggle Button Component
 * Allows users to switch between light/dark/system themes
 */

import React, { useState } from 'react'
import { Moon, Sun, Monitor } from 'lucide-react'
import { useTheme, type Theme } from '../hooks/useTheme'

export const ThemeToggle: React.FC = () => {
  const { theme, isDark, setTheme } = useTheme()
  const [isOpen, setIsOpen] = useState(false)

  const themes: { value: Theme; label: string; icon: React.ReactNode }[] = [
    { value: 'light', label: 'Light', icon: <Sun size={18} /> },
    { value: 'dark', label: 'Dark', icon: <Moon size={18} /> },
    { value: 'system', label: 'System', icon: <Monitor size={18} /> },
  ]

  return (
    <div className="relative">
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        aria-label="Toggle theme menu"
        title="Theme settings"
      >
        {isDark ? (
          <Moon size={20} className="text-yellow-500" />
        ) : (
          <Sun size={20} className="text-orange-500" />
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg z-50 border border-gray-200 dark:border-gray-700">
          <div className="p-2 space-y-1">
            {themes.map(({ value, label, icon }) => (
              <button
                key={value}
                onClick={() => {
                  setTheme(value)
                  setIsOpen(false)
                }}
                className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-colors text-left ${
                  theme === value
                    ? 'bg-blue-100 text-blue-900 dark:bg-blue-900 dark:text-blue-100'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100'
                }`}
              >
                {icon}
                <span className="flex-1">{label}</span>
                {theme === value && (
                  <div className="w-2 h-2 bg-blue-600 dark:bg-blue-400 rounded-full" />
                )}
              </button>
            ))}
          </div>

          {/* Divider */}
          <div className="border-t border-gray-200 dark:border-gray-700" />

          {/* Info */}
          <div className="px-4 py-2 text-xs text-gray-600 dark:text-gray-400">
            {theme === 'system'
              ? `Using ${isDark ? 'dark' : 'light'} mode`
              : `Using ${theme} mode`}
          </div>
        </div>
      )}

      {/* Close dropdown when clicking outside */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}

export default ThemeToggle
