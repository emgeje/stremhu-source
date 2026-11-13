import { Outlet, createFileRoute } from '@tanstack/react-router'

import { getIndexers } from '@/shared/queries/indexers'
import { getNotificationSettings } from '@/shared/queries/notifications'
import { getSystemSettings } from '@/shared/queries/system'
import { getUsers } from '@/shared/queries/users'

export const DASHBOARD_SYSTEM_NAME = 'Rendszer'

const RouteComponent = () => <Outlet />

export const Route = createFileRoute('/_protected/dashboard/system')({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(getSystemSettings),
      context.queryClient.ensureQueryData(getIndexers),
      context.queryClient.ensureQueryData(getUsers),
      context.queryClient.ensureQueryData(getNotificationSettings),
    ])
  },
  loader: () => {
    return { breadcrumb: DASHBOARD_SYSTEM_NAME }
  },
})
