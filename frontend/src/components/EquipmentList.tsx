import React from 'react'
import { Trash2, Edit2 } from 'lucide-react'

interface Equipment {
  id: number
  name: string
  description?: string
  status: string
  location?: string
  model?: string
  created_at: string
  updated_at: string
}

interface EquipmentListProps {
  equipments: Equipment[]
  selectedId?: number | null
  onSelect: (id: number) => void
  onEdit?: (equipment: Equipment) => void
  onDelete?: (id: number) => void
  isLoading?: boolean
}

export default function EquipmentList({
  equipments,
  selectedId,
  onSelect,
  onEdit,
  onDelete,
  isLoading
}: EquipmentListProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'inactive':
        return 'bg-gray-100 text-gray-800'
      case 'maintenance':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusDot = (status: string) => {
    switch (status) {
      case 'active':
        return '🟢'
      case 'inactive':
        return '⚪'
      case 'maintenance':
        return '🟡'
      default:
        return '⚪'
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <p className="text-gray-500">Loading equipments...</p>
      </div>
    )
  }

  if (equipments.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No equipments found</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {equipments.map((equipment) => (
        <div
          key={equipment.id}
          onClick={() => onSelect(equipment.id)}
          className={`p-4 border rounded-lg cursor-pointer transition ${
            selectedId === equipment.id
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 bg-white hover:border-blue-300'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 flex-1">
              <span className="text-2xl">{getStatusDot(equipment.status)}</span>
              <div>
                <h3 className="font-semibold text-gray-900">{equipment.name}</h3>
                {equipment.location && (
                  <p className="text-sm text-gray-500">{equipment.location}</p>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`text-xs px-2 py-1 rounded-full font-semibold ${getStatusColor(equipment.status)}`}>
                {equipment.status}
              </span>
              {onEdit && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onEdit(equipment)
                  }}
                  className="p-2 hover:bg-gray-100 rounded"
                  title="Edit"
                >
                  <Edit2 size={16} />
                </button>
              )}
              {onDelete && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (window.confirm(`Delete equipment "${equipment.name}"?`)) {
                      onDelete(equipment.id)
                    }
                  }}
                  className="p-2 hover:bg-red-100 rounded text-red-600"
                  title="Delete"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
