import axios, { AxiosResponse } from 'axios'
import {
  Equipment,
  CreateEquipmentRequest,
  UpdateEquipmentRequest,
  ProductType,
  CreateProductTypeRequest,
  CycleConfiguration,
  CreateCycleConfigRequest,
  UpdateCycleConfigRequest,
  TimeseriesData,
  CreateTimeseriesRequest,
  BatchTimeseriesRequest,
  CycleLabel,
  Alert,
  AcknowledgeAlertRequest,
  DashboardSummary,
} from '../types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  }
})

// ============================================================================
// Request/Response Interceptors
// ============================================================================

/**
 * Response error interceptor
 * Handles standard error responses from the API
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle different error types
    if (error.response) {
      // Server responded with error status
      const status = error.response.status
      const data = error.response.data

      // Create standardized error object
      const appError = new Error(
        data?.error?.message ||
        data?.message ||
        `HTTP Error ${status}`
      )

      // Attach additional context
      ;(appError as any).code = data?.error?.code || `HTTP_${status}`
      ;(appError as any).status = status
      ;(appError as any).details = data?.error?.details || null

      return Promise.reject(appError)
    } else if (error.request) {
      // Request made but no response received
      const netError = new Error('Network error - no response from server')
      ;(netError as any).code = 'NETWORK_ERROR'
      ;(netError as any).status = 0
      return Promise.reject(netError)
    } else {
      // Error in request setup
      const setupError = new Error(error.message || 'Error setting up request')
      ;(setupError as any).code = 'REQUEST_ERROR'
      return Promise.reject(setupError)
    }
  }
)

// ============================================================================
// Equipments API
// ============================================================================

export const equipmentApi = {
  list: (skip = 0, limit = 100): Promise<AxiosResponse<Equipment[]>> =>
    apiClient.get('/equipments', { params: { skip, limit } }),
  create: (data: CreateEquipmentRequest): Promise<AxiosResponse<Equipment>> =>
    apiClient.post('/equipments', data),
  get: (id: number): Promise<AxiosResponse<Equipment>> =>
    apiClient.get(`/equipments/${id}`),
  update: (id: number, data: UpdateEquipmentRequest): Promise<AxiosResponse<Equipment>> =>
    apiClient.put(`/equipments/${id}`, data),
  delete: (id: number): Promise<AxiosResponse<void>> =>
    apiClient.delete(`/equipments/${id}`),
}

// ============================================================================
// Product Types API
// ============================================================================

export const productTypeApi = {
  list: (skip = 0, limit = 100): Promise<AxiosResponse<ProductType[]>> =>
    apiClient.get('/product-types', { params: { skip, limit } }),
  create: (data: CreateProductTypeRequest): Promise<AxiosResponse<ProductType>> =>
    apiClient.post('/product-types', data),
  get: (id: number): Promise<AxiosResponse<ProductType>> =>
    apiClient.get(`/product-types/${id}`),
}

// ============================================================================
// Cycle Configurations API
// ============================================================================

export const cycleConfigApi = {
  list: (equipmentId?: number, skip = 0, limit = 100): Promise<AxiosResponse<CycleConfiguration[]>> =>
    apiClient.get('/cycle-configs', { params: { equipment_id: equipmentId, skip, limit } }),
  create: (data: CreateCycleConfigRequest): Promise<AxiosResponse<CycleConfiguration>> =>
    apiClient.post('/cycle-configs', data),
  get: (id: number): Promise<AxiosResponse<CycleConfiguration>> =>
    apiClient.get(`/cycle-configs/${id}`),
  update: (id: number, data: UpdateCycleConfigRequest): Promise<AxiosResponse<CycleConfiguration>> =>
    apiClient.put(`/cycle-configs/${id}`, data),
  delete: (id: number): Promise<AxiosResponse<void>> =>
    apiClient.delete(`/cycle-configs/${id}`),
}

// ============================================================================
// Timeseries Data API
// ============================================================================

export const timeseriesApi = {
  create: (data: CreateTimeseriesRequest): Promise<AxiosResponse<TimeseriesData>> =>
    apiClient.post('/timeseries', data),
  batch: (data: BatchTimeseriesRequest): Promise<AxiosResponse<TimeseriesData[]>> =>
    apiClient.post('/timeseries/batch', data),
  get: (equipmentId: number, startTime: string, endTime: string, limit = 1000): Promise<AxiosResponse<TimeseriesData[]>> =>
    apiClient.get(`/timeseries/${equipmentId}`, { params: { start_time: startTime, end_time: endTime, limit } }),
  getLatest: (equipmentId: number): Promise<AxiosResponse<TimeseriesData>> =>
    apiClient.get(`/timeseries/${equipmentId}/latest`),
}

// ============================================================================
// Cycles API
// ============================================================================

export const cyclesApi = {
  get: (equipmentId: number, startTime?: string, endTime?: string, limit = 100): Promise<AxiosResponse<CycleLabel[]>> =>
    apiClient.get(`/cycles/${equipmentId}`, { params: { start_time: startTime, end_time: endTime, limit } }),
}

// ============================================================================
// Alerts API
// ============================================================================

export const alertsApi = {
  list: (limit = 100, offset = 0): Promise<AxiosResponse<Alert[]>> =>
    apiClient.get('/alerts', { params: { limit, offset } }),
  getForEquipment: (equipmentId: number): Promise<AxiosResponse<Alert[]>> =>
    apiClient.get(`/alerts/${equipmentId}`),
  acknowledge: (alertId: number, data: AcknowledgeAlertRequest): Promise<AxiosResponse<Alert>> =>
    apiClient.put(`/alerts/${alertId}/acknowledge`, data),
  delete: (alertId: number): Promise<AxiosResponse<void>> =>
    apiClient.delete(`/alerts/${alertId}`),
}

// ============================================================================
// Dashboard API
// ============================================================================

export const dashboardApi = {
  getSummary: (): Promise<AxiosResponse<DashboardSummary>> =>
    apiClient.get('/dashboard/summary'),
  getEquipmentDashboard: (equipmentId: number): Promise<AxiosResponse<DashboardSummary>> =>
    apiClient.get(`/dashboard/equipment/${equipmentId}`),
}

// ============================================================================
// Health Check API
// ============================================================================

export const healthApi = {
  check: (): Promise<AxiosResponse<{ status: string }>> =>
    apiClient.get('/health'),
}

export default apiClient
