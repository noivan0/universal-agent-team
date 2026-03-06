/**
 * TypeScript type definitions for Cycle Time Monitoring System
 * Replaces all `any` types with explicit, type-safe interfaces
 */

// ============================================================================
// Equipment Types
// ============================================================================

export interface Equipment {
  id: number
  name: string
  description?: string
  status: EquipmentStatus
  location?: string
  model?: string
  created_at: string
  updated_at: string
}

export type EquipmentStatus = 'active' | 'inactive' | 'maintenance'

export interface CreateEquipmentRequest {
  name: string
  description?: string
  status: EquipmentStatus
  location?: string
  model?: string
}

export interface UpdateEquipmentRequest {
  name?: string
  description?: string
  status?: EquipmentStatus
  location?: string
  model?: string
}

// ============================================================================
// Product Type
// ============================================================================

export interface ProductType {
  id: number
  code: string
  name: string
  description?: string
  created_at: string
}

export interface CreateProductTypeRequest {
  code: string
  name: string
  description?: string
}

// ============================================================================
// Cycle Configuration
// ============================================================================

export interface CycleConfiguration {
  id: number
  equipment_id: number
  product_type_id: number
  target_cycle_time: number
  min_cycle_time: number
  max_cycle_time: number
  cycle_start_signal?: string
  cycle_end_signal?: string
  pattern_detection_enabled: boolean
  pattern_threshold: number
  status: ConfigurationStatus
  created_at: string
  updated_at: string
}

export type ConfigurationStatus = 'active' | 'inactive'

export interface CreateCycleConfigRequest {
  equipment_id: number
  product_type_id: number
  target_cycle_time: number
  min_cycle_time: number
  max_cycle_time: number
  cycle_start_signal?: string
  cycle_end_signal?: string
  pattern_detection_enabled?: boolean
  pattern_threshold?: number
  status?: ConfigurationStatus
}

export interface UpdateCycleConfigRequest {
  target_cycle_time?: number
  min_cycle_time?: number
  max_cycle_time?: number
  cycle_start_signal?: string
  cycle_end_signal?: string
  pattern_detection_enabled?: boolean
  pattern_threshold?: number
  status?: ConfigurationStatus
}

// ============================================================================
// Time Series Data
// ============================================================================

export interface TimeseriesData {
  id: number
  equipment_id: number
  timestamp: string
  data_point: number
  signal_name?: string
  signal_value?: number
  metadata?: Record<string, unknown>
  created_at: string
}

export interface CreateTimeseriesRequest {
  equipment_id: number
  timestamp: string
  data_point: number
  signal_name?: string
  signal_value?: number
  metadata?: Record<string, unknown>
}

export interface BatchTimeseriesRequest {
  data: CreateTimeseriesRequest[]
}

// ============================================================================
// Cycle Label (Detected Cycle)
// ============================================================================

export interface CycleLabel {
  id: number
  equipment_id: number
  product_type_id?: number
  start_time: string
  end_time: string
  cycle_duration: number
  detection_method: DetectionMethod
  confidence: number
  status: CycleStatus
  created_at: string
}

export type DetectionMethod = 'signal' | 'pattern'
export type CycleStatus = 'normal' | 'too_long' | 'too_short'

export interface CycleQueryParams {
  start_time?: string
  end_time?: string
  product_type_id?: number
  status?: CycleStatus
  limit?: number
  offset?: number
}

// ============================================================================
// Alert
// ============================================================================

export interface Alert {
  id: number
  equipment_id: number
  cycle_label_id?: number
  alert_type: AlertType
  severity: AlertSeverity
  message: string
  cycle_time: number
  threshold_min: number
  threshold_max: number
  is_acknowledged: boolean
  acknowledged_at?: string
  acknowledged_by?: string
  created_at: string
}

export type AlertType = 'cycle_too_long' | 'cycle_too_short' | 'equipment_error'
export type AlertSeverity = 'info' | 'warning' | 'critical'

export interface AcknowledgeAlertRequest {
  acknowledged_by: string
}

export interface AlertQueryParams {
  equipment_id?: number
  alert_type?: AlertType
  severity?: AlertSeverity
  unacknowledged_only?: boolean
  limit?: number
  offset?: number
}

// ============================================================================
// Alert Notification
// ============================================================================

export interface AlertNotification {
  id: number
  alert_id: number
  notification_method: NotificationMethod
  recipient: string
  status: NotificationStatus
  sent_at?: string
  error_message?: string
  created_at: string
}

export type NotificationMethod = 'email' | 'push' | 'sms'
export type NotificationStatus = 'pending' | 'sent' | 'failed'

// ============================================================================
// Dashboard Data
// ============================================================================

export interface DashboardSummary {
  total_equipments: number
  active_equipments: number
  equipments_with_alerts: number
  critical_alerts: number
  warning_alerts: number
  total_cycles_today: number
  normal_cycles_today: number
  anomalous_cycles_today: number
  average_cycle_time: number
}

export interface EquipmentDashboard {
  equipment: Equipment
  current_status: EquipmentStatus
  current_cycle?: CycleLabel
  last_completed_cycle?: CycleLabel
  active_alerts: Alert[]
  today_stats: EquipmentDailyStats
  recent_cycles: CycleLabel[]
}

export interface EquipmentDailyStats {
  total_cycles: number
  normal_cycles: number
  too_long_cycles: number
  too_short_cycles: number
  average_cycle_time: number
  min_cycle_time: number
  max_cycle_time: number
  standard_deviation: number
}

// ============================================================================
// WebSocket Messages
// ============================================================================

export interface WebSocketMessage<T = unknown> {
  type: WebSocketMessageType
  data: T
  timestamp: string
}

export type WebSocketMessageType =
  | 'cycle_complete'
  | 'cycle_in_progress'
  | 'alert_created'
  | 'alert_acknowledged'
  | 'status_update'
  | 'connection_established'
  | 'error'

export interface CycleCompleteMessage {
  equipment_id: number
  cycle: CycleLabel
  alert?: Alert
}

export interface CycleInProgressMessage {
  equipment_id: number
  progress_percent: number
  elapsed_time: number
  estimated_total_time: number
}

export interface AlertCreatedMessage {
  alert: Alert
  equipment_id: number
}

export interface StatusUpdateMessage {
  equipment_id: number
  status: EquipmentStatus
}

export interface WebSocketError {
  code: string
  message: string
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T> {
  data: T
  message?: string
  status: string
}

export interface ApiError {
  detail: string | ApiErrorDetail[]
  status?: number
}

export interface ApiErrorDetail {
  field: string
  message: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

// ============================================================================
// Form Data Types
// ============================================================================

export interface EquipmentFormData {
  name: string
  description: string
  status: EquipmentStatus
  location: string
  model: string
}

export interface CycleConfigFormData {
  equipment_id: number
  product_type_id: number
  target_cycle_time: number
  min_cycle_time: number
  max_cycle_time: number
  cycle_start_signal: string
  cycle_end_signal: string
  pattern_detection_enabled: boolean
  pattern_threshold: number
}

// ============================================================================
// Store State Types
// ============================================================================

export interface EquipmentStoreState {
  equipments: Equipment[]
  selectedEquipment: Equipment | null
  loading: boolean
  error: string | null
  lastUpdated: string | null
}

export interface AlertStoreState {
  alerts: Alert[]
  unacknowledgedCount: number
  criticalCount: number
  loading: boolean
  error: string | null
}

export interface RealtimeStoreState {
  cycles: Record<number, CycleLabel>
  inProgressCycles: Record<number, CycleInProgressMessage>
  equipmentStatus: Record<number, EquipmentStatus>
  lastUpdate: string | null
}

// ============================================================================
// Hook Return Types
// ============================================================================

export interface UseEquipmentsReturn {
  equipments: Equipment[]
  selectedEquipment: Equipment | null
  loading: boolean
  error: string | null
  selectEquipment: (equipment: Equipment) => void
  refetch: () => Promise<void>
}

export interface UseAlertsReturn {
  alerts: Alert[]
  unacknowledgedCount: number
  criticalCount: number
  loading: boolean
  error: string | null
  acknowledgeAlert: (alertId: number, acknowledgedBy: string) => Promise<void>
  refetch: () => Promise<void>
}

export interface UseRealtimeDataReturn {
  cycles: CycleLabel[]
  inProgress: CycleInProgressMessage | null
  connected: boolean
  reconnect: () => void
  subscribe: (equipmentId: number) => void
  unsubscribe: (equipmentId: number) => void
}

// ============================================================================
// Utility Types
// ============================================================================

export type Nullable<T> = T | null
export type Optional<T> = T | undefined
export type AsyncFn<T = void> = () => Promise<T>

export interface RequestConfig {
  timeout?: number
  retries?: number
  cacheTime?: number
}

export interface FilterOptions {
  skip?: number
  limit?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

// ============================================================================
// Validation Types
// ============================================================================

export interface ValidationError {
  field: string
  message: string
  code: string
}

export interface ValidationResult {
  isValid: boolean
  errors: ValidationError[]
}

// ============================================================================
// Status Types
// ============================================================================

export interface AsyncStatus {
  isLoading: boolean
  isError: boolean
  isSuccess: boolean
  error: Error | null
}

export interface RequestStatus {
  pending: boolean
  success: boolean
  error: Error | null
  lastUpdated: Date | null
}
