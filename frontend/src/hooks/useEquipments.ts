import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { equipmentApi } from '../services/api'

export function useEquipments() {
  const queryClient = useQueryClient()

  // List equipments
  const query = useQuery({
    queryKey: ['equipments'],
    queryFn: () => equipmentApi.list().then(res => res.data),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Create equipment
  const createMutation = useMutation({
    mutationFn: (data: any) => equipmentApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['equipments'] })
    }
  })

  // Update equipment
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      equipmentApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['equipments'] })
    }
  })

  // Delete equipment
  const deleteMutation = useMutation({
    mutationFn: (id: number) => equipmentApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['equipments'] })
    }
  })

  return {
    equipments: query.data || [],
    isLoading: query.isLoading,
    error: query.error,
    createEquipment: createMutation.mutate,
    updateEquipment: updateMutation.mutate,
    deleteEquipment: deleteMutation.mutate,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  }
}
