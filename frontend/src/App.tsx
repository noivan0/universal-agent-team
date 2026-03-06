import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Settings, BarChart3, Wrench } from 'lucide-react'
import ErrorBoundary from './components/ErrorBoundary'
import ToastProvider from './components/Toast'
import { ThemeProvider } from './hooks/useTheme'
import ThemeToggle from './components/ThemeToggle'
import EquipmentManager from './pages/EquipmentManager'
import Dashboard from './pages/Dashboard'
import './App.css'

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')

  return (
    <ErrorBoundary>
      <ToastProvider>
        <ThemeProvider>
          <BrowserRouter>
            <div className="min-h-screen bg-gray-100 dark:bg-gray-900 transition-colors">
              {/* Navigation */}
              <nav className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-50 transition-colors">
                <div className="max-w-7xl mx-auto px-4 py-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Cycle Time Monitoring System</h1>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Real-time equipment monitoring and alerting</p>
                    </div>

                    <div className="flex gap-2 items-center">
                      <Link
                        to="/dashboard"
                        onClick={() => setCurrentPage('dashboard')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
                          currentPage === 'dashboard'
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                      >
                        <BarChart3 size={20} />
                        Dashboard
                      </Link>

                      <Link
                        to="/equipment"
                        onClick={() => setCurrentPage('equipment')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
                          currentPage === 'equipment'
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                      >
                        <Wrench size={20} />
                        Equipment
                      </Link>

                      <Link
                        to="/settings"
                        onClick={() => setCurrentPage('settings')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
                          currentPage === 'settings'
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }`}
                      >
                        <Settings size={20} />
                        Settings
                      </Link>

                      {/* Theme Toggle */}
                      <div className="ml-4 pl-4 border-l border-gray-200 dark:border-gray-700">
                        <ThemeToggle />
                      </div>
                    </div>
                  </div>
                </div>
              </nav>

              {/* Main Content */}
              <main className="max-w-7xl mx-auto px-4 py-8">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/equipment" element={<EquipmentManager />} />
                  <Route path="/settings" element={
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 transition-colors">
                      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Settings</h2>
                      <p className="text-gray-600 dark:text-gray-400">Settings page coming soon...</p>
                    </div>
                  } />
                </Routes>
              </main>
            </div>
          </BrowserRouter>
        </ThemeProvider>
      </ToastProvider>
    </ErrorBoundary>
  )
}

export default App
