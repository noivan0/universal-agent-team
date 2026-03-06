import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Activity, AlertCircle, TrendingUp, WifiOff } from 'lucide-react'
import { useEquipments } from '../hooks/useEquipments'
import { useRealtimeData } from '../hooks/useRealtimeData'
import EquipmentList from '../components/EquipmentList'
import AlertPanel from '../components/AlertPanel'
import CycleProgressBar from '../components/CycleProgressBar'
import { equipmentApi, cycleConfigApi, alertsApi } from '../services/api'
import { Equipment, CycleConfiguration, Alert } from '../types'

interface EquipmentWithDetails extends Equipment {
  config?: CycleConfiguration
  stats?: EquipmentStats
}

interface EquipmentStats {
  totalCycles: number
  normalCycles: number
  alertCount: number
}

/**
 * Dashboard Component - Main monitoring interface
 * Optimizations:
 * - useCallback for stable function references
 * - useMemo for computed values
 * - Memoized child components
 * - Efficient dependency management
 */
export default function Dashboard() {
  const { equipments, isLoading: equipmentsLoading } = useEquipments()
  const [selectedEquipmentId, setSelectedEquipmentId] = useState<number | null>(null)
  const [selectedEquipmentDetails, setSelectedEquipmentDetails] = useState<EquipmentWithDetails | null>(null)
  const [equipmentConfig, setEquipmentConfig] = useState<CycleConfiguration | null>(null)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)

  const {
    connectionStatus,
    lastCycle,
    alerts,
    isConnected,
    requestAlerts
  } = useRealtimeData(selectedEquipmentId || undefined)

  // Load equipment details when selection changes
  useEffect(() => {
    if (!selectedEquipmentId) {
      setSelectedEquipmentDetails(null)
      setEquipmentConfig(null)
      return
    }

    const loadDetails = async () => {
      setIsLoadingDetails(true)
      try {
        const selected = equipments.find(e => e.id === selectedEquipmentId)
        if (!selected) return

        setSelectedEquipmentDetails(selected)

        // Load cycle configuration (only fetch first config)
        const configResp = await cycleConfigApi.list(selectedEquipmentId, 0, 1)
        if (configResp.data.length > 0) {
          setEquipmentConfig(configResp.data[0])
        }

        // Request alerts
        requestAlerts()
      } catch (error) {
        console.error('Failed to load equipment details:', error)
      } finally {
        setIsLoadingDetails(false)
      }
    }

    loadDetails()
  }, [selectedEquipmentId, equipments, requestAlerts])

  // Memoized computed values to prevent recalculation on every render
  const activeEquipmentCount = useMemo(
    () => equipments.filter(e => e.status === 'active').length,
    [equipments]
  )

  const unacknowledgedAlertCount = useMemo(
    () => alerts.filter(a => !a.is_acknowledged).length,
    [alerts]
  )

  // Stable callback for equipment selection
  const handleSelectEquipment = useCallback((equipmentId: number) => {
    setSelectedEquipmentId(equipmentId)
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Real-time Monitoring Dashboard
            </h1>
            <p className="text-gray-600 mt-1">Track equipment cycle times and alerts</p>
          </div>

          {/* Connection Status */}
          <div className="flex items-center gap-2">
            {isConnected ? (
              <div className="flex items-center gap-1 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
                Connected
              </div>
            ) : (
              <div className="flex items-center gap-1 px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm">
                <WifiOff className="w-4 h-4" />
                Disconnected
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Total Equipment</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{equipments.length}</p>
            </div>
            <Activity className="w-8 h-8 text-blue-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Active</p>
              <p className="text-3xl font-bold text-green-600 mt-1">{activeEquipmentCount}</p>
            </div>
            <TrendingUp className="w-8 h-8 text-green-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Alerts</p>
              <p className={`text-3xl font-bold mt-1 ${unacknowledgedAlertCount > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                {unacknowledgedAlertCount}
              </p>
            </div>
            <AlertCircle className="w-8 h-8 text-red-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Connection</p>
              <p className={`text-sm font-bold mt-2 ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                {connectionStatus === 'connected' ? 'Live' :
                 connectionStatus === 'connecting' ? 'Connecting...' : 'Offline'}
              </p>
            </div>
            <div className="w-2 h-2 rounded-full" style={{
              backgroundColor: isConnected ? '#10b981' : '#ef4444',
              boxShadow: isConnected ? '0 0 8px #10b981' : 'none'
            }} />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Equipment List (Left) */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Equipment ({equipments.length})</h2>

            <EquipmentList
              equipments={equipments}
              selectedId={selectedEquipmentId}
              onSelect={setSelectedEquipmentId}
              isLoading={equipmentsLoading}
            />
          </div>
        </div>

        {/* Equipment Details (Center/Right) */}
        <div className="lg:col-span-3">
          {isLoadingDetails ? (
            <div className="bg-white rounded-lg shadow-sm p-6 flex items-center justify-center h-64">
              <p className="text-gray-500">Loading details...</p>
            </div>
          ) : selectedEquipmentDetails ? (
            <div className="space-y-6">
              {/* Equipment Header */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">
                      {selectedEquipmentDetails.name}
                    </h2>
                    {selectedEquipmentDetails.location && (
                      <p className="text-gray-600 mt-1">📍 {selectedEquipmentDetails.location}</p>
                    )}
                  </div>

                  <div className="text-right">
                    <div className="text-sm font-medium text-gray-600">Status</div>
                    <div className={`text-lg font-bold mt-1 ${
                      selectedEquipmentDetails.status === 'active' ? 'text-green-600' :
                      selectedEquipmentDetails.status === 'maintenance' ? 'text-yellow-600' :
                      'text-gray-600'
                    }`}>
                      {selectedEquipmentDetails.status.charAt(0).toUpperCase() + selectedEquipmentDetails.status.slice(1)}
                    </div>
                  </div>
                </div>

                {/* Cycle Configuration */}
                {equipmentConfig && (
                  <div className="space-y-4 pt-4 border-t">
                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 mb-2">
                        Current Cycle Configuration
                      </h3>
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <p className="text-xs text-gray-600">Minimum</p>
                          <p className="text-lg font-semibold text-blue-600">
                            {equipmentConfig.min_cycle_time.toFixed(1)}s
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-600">Target</p>
                          <p className="text-lg font-semibold text-green-600">
                            {equipmentConfig.target_cycle_time.toFixed(1)}s
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-600">Maximum</p>
                          <p className="text-lg font-semibold text-red-600">
                            {equipmentConfig.max_cycle_time.toFixed(1)}s
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Cycle Progress */}
                    {lastCycle && (
                      <div className="pt-4 border-t">
                        <h3 className="text-sm font-semibold text-gray-700 mb-3">
                          Last Completed Cycle
                        </h3>
                        <CycleProgressBar
                          currentTime={lastCycle.cycle_duration}
                          targetTime={equipmentConfig.target_cycle_time}
                          minTime={equipmentConfig.min_cycle_time}
                          maxTime={equipmentConfig.max_cycle_time}
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Alerts Section */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <AlertPanel
                  alerts={alerts}
                  equipmentName={selectedEquipmentDetails.name}
                  isLoading={isLoadingDetails}
                />
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-sm p-12 text-center">
              <p className="text-gray-500 text-lg">
                Select an equipment to view details
              </p>
              <p className="text-gray-400 mt-2">
                Choose from the list on the left to get started
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
