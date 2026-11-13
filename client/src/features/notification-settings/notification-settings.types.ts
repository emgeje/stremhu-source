import type { NotificationSettingsResponse } from '@/shared/lib/source/source-client'

export type NotificationSettingsOptions = {
  settings: NotificationSettingsResponse
}

export type NotificationSettingsDialog = {
  type: 'NOTIFICATION_SETTINGS'
  options: NotificationSettingsOptions
}
