/**
 * Loading Skeleton Components
 * Display placeholder content while data is loading
 * Provides better visual feedback than spinners or blank screens
 */

import React from 'react'

/**
 * Generic skeleton loader - animated gray box
 */
export const SkeletonBox: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div
    className={`animate-pulse bg-gray-200 rounded ${className}`}
    style={{
      animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
    }}
  />
)

/**
 * Equipment card skeleton
 */
export const EquipmentCardSkeleton: React.FC = () => (
  <div className="bg-white rounded-lg shadow-sm p-4 space-y-3">
    <SkeletonBox className="h-6 w-3/4" />
    <SkeletonBox className="h-4 w-1/2" />
    <div className="flex gap-2 pt-2">
      <SkeletonBox className="h-8 w-20" />
      <SkeletonBox className="h-8 w-20" />
    </div>
  </div>
)

/**
 * List of equipment skeletons
 */
export const EquipmentListSkeleton: React.FC<{ count?: number }> = ({ count = 5 }) => (
  <div className="space-y-3">
    {Array.from({ length: count }).map((_, i) => (
      <EquipmentCardSkeleton key={i} />
    ))}
  </div>
)

/**
 * Alert item skeleton
 */
export const AlertItemSkeleton: React.FC = () => (
  <div className="border-b border-gray-200 p-4 space-y-2">
    <div className="flex justify-between items-start">
      <SkeletonBox className="h-5 w-2/3" />
      <SkeletonBox className="h-6 w-16 rounded-full" />
    </div>
    <SkeletonBox className="h-4 w-full" />
    <SkeletonBox className="h-4 w-3/4" />
  </div>
)

/**
 * Progress bar skeleton
 */
export const ProgressBarSkeleton: React.FC = () => (
  <div className="space-y-2">
    <div className="flex justify-between">
      <SkeletonBox className="h-4 w-1/4" />
      <SkeletonBox className="h-4 w-1/4" />
    </div>
    <SkeletonBox className="h-6 w-full rounded-full" />
    <div className="flex justify-between">
      <SkeletonBox className="h-3 w-12" />
      <SkeletonBox className="h-3 w-12" />
      <SkeletonBox className="h-3 w-12" />
    </div>
  </div>
)

/**
 * Dashboard header skeleton
 */
export const DashboardHeaderSkeleton: React.FC = () => (
  <div className="bg-white rounded-lg shadow-sm p-6 space-y-4">
    <SkeletonBox className="h-8 w-1/2" />
    <div className="grid grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="space-y-2">
          <SkeletonBox className="h-4 w-3/4" />
          <SkeletonBox className="h-6 w-1/2" />
        </div>
      ))}
    </div>
  </div>
)

/**
 * Full page skeleton for initial load
 */
export const FullPageSkeleton: React.FC = () => (
  <div className="space-y-6">
    <DashboardHeaderSkeleton />
    <div className="grid grid-cols-3 gap-6">
      <div className="col-span-1">
        <EquipmentListSkeleton count={3} />
      </div>
      <div className="col-span-2 space-y-4">
        <div className="bg-white rounded-lg shadow-sm p-6">
          <SkeletonBox className="h-64 w-full rounded" />
        </div>
        <div className="bg-white rounded-lg shadow-sm p-6">
          <SkeletonBox className="h-48 w-full rounded" />
        </div>
      </div>
    </div>
  </div>
)
