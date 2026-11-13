import { useQuery, useSuspenseQuery } from '@tanstack/react-query'
import { SettingsIcon } from 'lucide-react'

import { useDialogs } from '@/routes/-features/dialogs/dialogs-store'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/shared/components/ui/item'
import { Progress } from '@/shared/components/ui/progress'
import { Separator } from '@/shared/components/ui/separator'
import type { DiskAlertLevelEnum } from '@/shared/lib/source/source-client'
import { cn } from '@/shared/lib/utils'
import { formatFilesize } from '@/shared/utils/file.util'
import {
  getDiskStatus,
  getNotificationSettings,
} from '@/shared/queries/notifications'

const levelMap: Record<
  DiskAlertLevelEnum,
  { label: string; indicator: string }
> = {
  ok: { label: '🟢 Rendben', indicator: '' },
  warning: { label: '🟡 Fogy a hely', indicator: '[&>*]:bg-yellow-500' },
  critical: { label: '🟠 Kritikus', indicator: '[&>*]:bg-orange-500' },
  full: { label: '🔴 Betelt', indicator: '[&>*]:bg-destructive' },
}

export function DiskAlerts() {
  const dialogs = useDialogs()

  const { data: settings } = useSuspenseQuery(getNotificationSettings)
  const { data: diskStatus, isPending, isError } = useQuery(getDiskStatus)

  const channels = [
    settings.email.enabled && 'E-mail',
    settings.telegram.enabled && 'Telegram',
  ].filter(Boolean)

  let notificationInfo = 'Nincs bekapcsolt értesítési csatorna'
  if (!settings.diskAlert.enabled) {
    notificationInfo = 'A tárhely figyelés ki van kapcsolva'
  } else if (channels.length > 0) {
    notificationInfo = `${channels.join(' és ')} · figyelmeztetés ${settings.diskAlert.warningPercent}%, kritikus ${settings.diskAlert.criticalPercent}%`
  }

  const level = diskStatus ? levelMap[diskStatus.level] : null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Tárhely figyelés
          {level && <Badge variant="outline">{level.label}</Badge>}
        </CardTitle>
        <CardDescription>
          Értesítés e-mailben vagy Telegramon, mielőtt betelik a lemez.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {isPending && (
          <p className="text-muted-foreground text-sm">
            Tárhely lekérdezése...
          </p>
        )}
        {isError && (
          <p className="text-destructive text-sm">
            A tárhely adatai nem kérdezhetők le.
          </p>
        )}
        {diskStatus?.usages.map((usage) => (
          <div key={usage.path} className="grid gap-2">
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="font-mono break-all text-muted-foreground">
                {usage.path}
              </span>
              <span className="font-bold whitespace-nowrap">
                {usage.percent.toFixed(1)}%
              </span>
            </div>
            <Progress
              value={usage.percent}
              className={cn('h-2', level?.indicator)}
            />
            <p className="text-muted-foreground text-sm">
              {formatFilesize(usage.used)} / {formatFilesize(usage.total)}{' '}
              foglalt · {formatFilesize(usage.free)} szabad
            </p>
          </div>
        ))}
        <Separator />
        <Item className="p-0">
          <ItemContent>
            <ItemTitle>Értesítések</ItemTitle>
            <ItemDescription>{notificationInfo}</ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button
              size="icon-sm"
              className="rounded-full"
              onClick={() =>
                dialogs.openDialog({
                  type: 'NOTIFICATION_SETTINGS',
                  options: { settings },
                })
              }
            >
              <SettingsIcon />
            </Button>
          </ItemActions>
        </Item>
      </CardContent>
    </Card>
  )
}
