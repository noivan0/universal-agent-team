import React, { useState, useEffect } from 'react'
import { Plus } from 'lucide-react'
import EquipmentList from '../components/EquipmentList'
import EquipmentForm from '../components/EquipmentForm'
import { useEquipments } from '../hooks/useEquipments'
import { useEquipmentStore } from '../store/equipmentStore'

interface Equipment {
  id?: number
  name: string
  description?: string
  status?: string
  location?: string
  model?: string
  created_at?: string
  updated_at?: string
}

export default function EquipmentManager() {
  const [showForm, setShowForm] = useState(false)
  const [editingEquipment, setEditingEquipment] = useState<Equipment | null>(null)

  const { equipments, isLoading, createEquipment, updateEquipment, deleteEquipment, isCreating, isUpdating } = useEquipments()
  const { selectedEquipmentId, setSelectedEquipmentId } = useEquipmentStore()

  // Sync store with fetched equipments
  useEffect(() => {
    useEquipmentStore.setState({ equipments })
  }, [equipments])

  const handleAddNew = () => {
    setEditingEquipment(null)
    setShowForm(true)
  }

  const handleEdit = (equipment: Equipment) => {
    setEditingEquipment(equipment)
    setShowForm(true)
  }

  const handleFormSubmit = (data: Equipment) => {
    if (editingEquipment?.id) {
      updateEquipment({ id: editingEquipment.id, data })
    } else {
      createEquipment(data)
    }
    setShowForm(false)
    setEditingEquipment(null)
  }

  const handleFormCancel = () => {
    setShowForm(false)
    setEditingEquipment(null)
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Equipment Management</h2>
            <p className="text-gray-600 mt-1">Manage your manufacturing equipment</p>
          </div>
          {!showForm && (
            <button
              onClick={handleAddNew}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition"
            >
              <Plus size={20} />
              Add Equipment
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Equipment List */}
          <div className="lg:col-span-1">
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="font-semibold text-gray-900 mb-4">Equipment List ({equipments.length})</h3>
              <EquipmentList
                equipments={equipments}
                selectedId={selectedEquipmentId}
                onSelect={setSelectedEquipmentId}
                onEdit={handleEdit}
                onDelete={deleteEquipment}
                isLoading={isLoading}
              />
            </div>
          </div>

          {/* Form or Details */}
          <div className="lg:col-span-2">
            {showForm ? (
              <EquipmentForm
                equipment={editingEquipment}
                onSubmit={handleFormSubmit}
                onCancel={handleFormCancel}
                isLoading={isCreating || isUpdating}
              />
            ) : (
              <div className="bg-gray-50 rounded-lg p-6">
                <div className="text-center py-12">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Select an Equipment
                  </h3>
                  <p className="text-gray-600">
                    Click on an equipment to view details, or click "Add Equipment" to create a new one.
                  </p>
                  <div className="mt-6 space-y-2">
                    <p className="text-sm text-gray-500">📋 Features coming soon:</p>
                    <ul className="text-sm text-gray-600 space-y-1">
                      <li>✓ Cycle time configuration</li>
                      <li>✓ Real-time monitoring dashboard</li>
                      <li>✓ Automatic cycle detection</li>
                      <li>✓ Alert management</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-3xl font-bold text-blue-600">{equipments.length}</div>
          <div className="text-sm text-gray-600 mt-1">Total Equipments</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-3xl font-bold text-green-600">
            {equipments.filter(e => e.status === 'active').length}
          </div>
          <div className="text-sm text-gray-600 mt-1">Active Equipments</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-3xl font-bold text-yellow-600">
            {equipments.filter(e => e.status === 'maintenance').length}
          </div>
          <div className="text-sm text-gray-600 mt-1">Under Maintenance</div>
        </div>
      </div>
    </div>
  )
}
