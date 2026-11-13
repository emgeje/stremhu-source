import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  NotificationSettingsUpdateRequest,
  NotificationTestRequest,
} from '../lib/source/source-client'
import {
  notificationsGetDiskStatus,
  notificationsGetSettings,
  notificationsSendTest,
  notificationsUpdateSettings,
} from '../lib/source/source-client'

export const getNotificationSettings = queryOptions({
  queryKey: ['notifications', 'settings'],
  queryFn: async () => {
    const response = await notificationsGetSettings()
    return response
  },
})

export const getDiskStatus = queryOptions({
  queryKey: ['notifications', 'disk'],
  refetchInterval: 60 * 1000,
  queryFn: async () => {
    const response = await notificationsGetDiskStatus()
    return response
  },
})

export function useNotificationSettingsUpdate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: NotificationSettingsUpdateRequest) => {
      const response = await notificationsUpdateSettings(payload)
      return response
    },
    onSuccess: async (data) => {
      queryClient.setQueryData(getNotificationSettings.queryKey, data)
      await queryClient.invalidateQueries({ queryKey: getDiskStatus.queryKey })
    },
  })
}

export function useNotificationTest() {
  return useMutation({
    mutationFn: async (payload: NotificationTestRequest) => {
      const response = await notificationsSendTest(payload)
      return response
    },
  })
}
