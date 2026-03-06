import { create } from 'zustand'

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

interface EquipmentStore {
  equipments: Equipment[]
  selectedEquipmentId: number | null
  setEquipments: (equipments: Equipment[]) => void
  setSelectedEquipmentId: (id: number | null) => void
  addEquipment: (equipment: Equipment) => void
  removeEquipment: (id: number) => void
  updateEquipment: (id: number, equipment: Partial<Equipment>) => void
}

export const useEquipmentStore = create<EquipmentStore>((set) => ({
  equipments: [],
  selectedEquipmentId: null,

  setEquipments: (equipments) => set({ equipments }),

  setSelectedEquipmentId: (id) => set({ selectedEquipmentId: id }),

  addEquipment: (equipment) =>
    set((state) => ({
      equipments: [...state.equipments, equipment],
    })),

  removeEquipment: (id) =>
    set((state) => ({
      equipments: state.equipments.filter((e) => e.id !== id),
      selectedEquipmentId: state.selectedEquipmentId === id ? null : state.selectedEquipmentId,
    })),

  updateEquipment: (id, updates) =>
    set((state) => ({
      equipments: state.equipments.map((e) =>
        e.id === id ? { ...e, ...updates } : e
      ),
    })),
}))
