import type { MouseEventHandler, ReactNode, SubmitEventHandler } from 'react'
import { useRef } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'
import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
import { Button } from '@/shared/components/ui/button'
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import { Field, FieldLabel } from '@/shared/components/ui/field'
import { Label } from '@/shared/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { Separator } from '@/shared/components/ui/separator'
import { Switch } from '@/shared/components/ui/switch'
import { useAppForm } from '@/shared/contexts/form-context'
import type { NotificationChannelEnum } from '@/shared/lib/source/source-client'
import { SmtpSecurityEnum } from '@/shared/lib/source/source-client'
import { parseApiError } from '@/shared/lib/utils'
import {
  useNotificationSettingsUpdate,
  useNotificationTest,
} from '@/shared/queries/notifications'

import type { NotificationSettingsDialog as NotificationSettingsDialogType } from './notification-settings.types'

const SECURITY_OPTIONS: { value: SmtpSecurityEnum; label: string }[] = [
  {
    value: SmtpSecurityEnum.starttls,
    label: 'STARTTLS (általában 587-es port)',
  },
  { value: SmtpSecurityEnum.ssl, label: 'SSL/TLS (általában 465-ös port)' },
  { value: SmtpSecurityEnum.none, label: 'Nincs titkosítás' },
]

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function parseRecipients(value: string) {
  return value
    .split(/[,;\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

const percent = z.coerce
  .number<string>('Csak szám adható meg')
  .int('Csak egész szám adható meg')
  .min(1, 'Legalább 1% legyen')
  .max(99, 'Legfeljebb 99% lehet')

function createSchema(passwordSet: boolean, botTokenSet: boolean) {
  return z
    .object({
      serverName: z.string().max(100, 'Legfeljebb 100 karakter lehet'),
      diskEnabled: z.boolean(),
      warningPercent: percent,
      criticalPercent: percent,
      repeatHours: z.coerce
        .number<string>('Csak szám adható meg')
        .int('Csak egész szám adható meg')
        .min(0, 'Nem lehet negatív')
        .max(720, 'Legfeljebb 720 óra lehet'),
      notifyRecovery: z.boolean(),
      emailEnabled: z.boolean(),
      smtpHost: z.string(),
      smtpPort: z.coerce
        .number<string>('Csak szám adható meg')
        .int('Csak egész szám adható meg')
        .min(1, 'Érvénytelen port')
        .max(65535, 'Érvénytelen port'),
      security: z.enum(SmtpSecurityEnum),
      username: z.string(),
      password: z.string(),
      sender: z.string(),
      recipients: z.string(),
      telegramEnabled: z.boolean(),
      botToken: z.string(),
      chatId: z.string(),
    })
    .superRefine((value, ctx) => {
      if (Number(value.warningPercent) >= Number(value.criticalPercent)) {
        ctx.addIssue({
          code: 'custom',
          path: ['criticalPercent'],
          message: 'A kritikus szint legyen nagyobb a figyelmeztetésnél',
        })
      }

      if (value.emailEnabled) {
        if (!value.smtpHost.trim()) {
          ctx.addIssue({
            code: 'custom',
            path: ['smtpHost'],
            message: 'Az SMTP szerver megadása kötelező',
          })
        }
        if (!value.sender.trim()) {
          ctx.addIssue({
            code: 'custom',
            path: ['sender'],
            message: 'A feladó megadása kötelező',
          })
        }
        const recipients = parseRecipients(value.recipients)
        if (recipients.length === 0) {
          ctx.addIssue({
            code: 'custom',
            path: ['recipients'],
            message: 'Legalább egy címzett megadása kötelező',
          })
        } else if (recipients.some((item) => !EMAIL_REGEX.test(item))) {
          ctx.addIssue({
            code: 'custom',
            path: ['recipients'],
            message: 'Érvénytelen e-mail cím a címzettek között',
          })
        }
        if (value.username.trim() && !value.password && !passwordSet) {
          ctx.addIssue({
            code: 'custom',
            path: ['password'],
            message: 'Felhasználónévhez jelszó is szükséges',
          })
        }
      }

      if (value.telegramEnabled) {
        if (!value.botToken.trim() && !botTokenSet) {
          ctx.addIssue({
            code: 'custom',
            path: ['botToken'],
            message: 'A bot token megadása kötelező',
          })
        }
        if (!value.chatId.trim()) {
          ctx.addIssue({
            code: 'custom',
            path: ['chatId'],
            message: 'A chat ID megadása kötelező',
          })
        }
      }
    })
}

function SwitchRow(props: {
  id: string
  title: string
  description?: ReactNode
  checked: boolean
  onCheckedChange: (checked: boolean) => void
}) {
  const { id, title, description, checked, onCheckedChange } = props

  return (
    <div className="grid gap-1">
      <Label htmlFor={id} className="flex items-start gap-3">
        <p className="flex-1 text-sm leading-none font-medium">{title}</p>
        <Switch id={id} checked={checked} onCheckedChange={onCheckedChange} />
      </Label>
      {description && (
        <p className="text-muted-foreground text-sm">{description}</p>
      )}
    </div>
  )
}

export function NotificationSettingsDialog(
  dialog: OpenedDialog & NotificationSettingsDialogType,
) {
  const { settings } = dialog.options

  const dialogsStore = useDialogsStore()

  const { mutateAsync: updateSettings } = useNotificationSettingsUpdate()
  const { mutateAsync: sendTest } = useNotificationTest()

  const testChannelRef = useRef<NotificationChannelEnum | null>(null)

  const form = useAppForm({
    defaultValues: {
      serverName: settings.serverName,
      diskEnabled: settings.diskAlert.enabled,
      warningPercent: `${settings.diskAlert.warningPercent}`,
      criticalPercent: `${settings.diskAlert.criticalPercent}`,
      repeatHours: `${settings.diskAlert.repeatHours}`,
      notifyRecovery: settings.diskAlert.notifyRecovery,
      emailEnabled: settings.email.enabled,
      smtpHost: settings.email.smtpHost,
      smtpPort: `${settings.email.smtpPort}`,
      security: settings.email.security,
      username: settings.email.username,
      password: '',
      sender: settings.email.sender,
      recipients: settings.email.recipients.join(', '),
      telegramEnabled: settings.telegram.enabled,
      botToken: '',
      chatId: settings.telegram.chatId,
    },
    validators: {
      onChange: createSchema(
        settings.email.passwordSet,
        settings.telegram.botTokenSet,
      ),
    },
    onSubmit: async ({ value }) => {
      const testChannel = testChannelRef.current
      testChannelRef.current = null

      try {
        await updateSettings({
          serverName: value.serverName.trim(),
          diskAlert: {
            enabled: value.diskEnabled,
            warningPercent: Number(value.warningPercent),
            criticalPercent: Number(value.criticalPercent),
            repeatHours: Number(value.repeatHours),
            notifyRecovery: value.notifyRecovery,
          },
          email: {
            enabled: value.emailEnabled,
            smtpHost: value.smtpHost.trim(),
            smtpPort: Number(value.smtpPort),
            security: value.security,
            username: value.username.trim(),
            password: value.password === '' ? null : value.password,
            sender: value.sender.trim(),
            recipients: parseRecipients(value.recipients),
          },
          telegram: {
            enabled: value.telegramEnabled,
            botToken:
              value.botToken.trim() === '' ? null : value.botToken.trim(),
            chatId: value.chatId.trim(),
          },
        })
      } catch (error) {
        toast.error(parseApiError(error))
        return
      }

      if (testChannel) {
        try {
          await sendTest({ channel: testChannel })
          toast.success(
            'Beállítások mentve, a teszt értesítés elküldve. Nézd meg, megérkezett-e!',
          )
        } catch (error) {
          toast.error(parseApiError(error))
        }
        return
      }

      toast.success('Az értesítési beállítások mentve.')
      dialogsStore.closeDialog(dialog.id)
    },
  })

  const onSubmit: SubmitEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  const handleTest =
    (channel: NotificationChannelEnum): MouseEventHandler<HTMLButtonElement> =>
    async (e) => {
      e.preventDefault()
      e.stopPropagation()
      testChannelRef.current = channel
      await form.handleSubmit()
      testChannelRef.current = null
    }

  const handleClose: MouseEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()
    dialogsStore.closeDialog(dialog.id)
  }

  return (
    <Dialog open={dialog.open}>
      <DialogScrollContent
        className="md:max-w-lg"
        onEscapeKeyDown={() => dialogsStore.closeDialog(dialog.id)}
      >
        <form.AppForm>
          <form
            name="notification-settings"
            className="grid gap-5"
            onSubmit={onSubmit}
          >
            <DialogHeader>
              <DialogTitle>Értesítések és tárhely figyelés</DialogTitle>
              <DialogDescription>
                A szerver 5 percenként ellenőrzi a tárhelyet, és a beállított
                csatornákon szól, ha fogy a hely vagy betelt a lemez.
              </DialogDescription>
            </DialogHeader>

            <form.AppField name="serverName">
              {(field) => (
                <field.AppTextField
                  label="Szerver neve az üzenetekben"
                  description="Ha üresen hagyod, a szerver címe szerepel. Pl.: „Pisti otthoni szervere”"
                />
              )}
            </form.AppField>

            <Separator />

            {/* Tárhely riasztás */}
            <div className="grid gap-4">
              <form.Field name="diskEnabled">
                {(field) => (
                  <SwitchRow
                    id={field.name}
                    title="Tárhely figyelés"
                    description="Riasztás a lemez telítettsége alapján."
                    checked={field.state.value}
                    onCheckedChange={field.handleChange}
                  />
                )}
              </form.Field>

              <form.Subscribe selector={(state) => state.values.diskEnabled}>
                {(diskEnabled) =>
                  diskEnabled && (
                    <div className="grid gap-4">
                      <div className="grid grid-cols-2 gap-4">
                        <form.AppField name="warningPercent">
                          {(field) => (
                            <field.AppTextField
                              label="Figyelmeztetés (%)"
                              description="Előzetes jelzés"
                            />
                          )}
                        </form.AppField>
                        <form.AppField name="criticalPercent">
                          {(field) => (
                            <field.AppTextField
                              label="Kritikus (%)"
                              description="Sürgős jelzés"
                            />
                          )}
                        </form.AppField>
                      </div>
                      <p className="text-muted-foreground text-sm">
                        Betelt lemezről (kevesebb mint 1 GiB szabad hely)
                        mindenképp érkezik értesítés.
                      </p>
                      <form.AppField name="repeatHours">
                        {(field) => (
                          <field.AppTextField
                            label="Emlékeztető gyakorisága (óra)"
                            description="Ha a probléma fennáll, ennyi óránként újra szól. 0 = nincs emlékeztető."
                          />
                        )}
                      </form.AppField>
                      <form.Field name="notifyRecovery">
                        {(field) => (
                          <SwitchRow
                            id={field.name}
                            title="Értesítés helyreálláskor"
                            description="Szóljon, ha a tárhely újra rendben van."
                            checked={field.state.value}
                            onCheckedChange={field.handleChange}
                          />
                        )}
                      </form.Field>
                    </div>
                  )
                }
              </form.Subscribe>
            </div>

            <Separator />

            {/* E-mail */}
            <div className="grid gap-4">
              <form.Field name="emailEnabled">
                {(field) => (
                  <SwitchRow
                    id={field.name}
                    title="E-mail értesítés"
                    description="Küldés tetszőleges SMTP szerveren keresztül (pl. Gmail alkalmazásjelszóval)."
                    checked={field.state.value}
                    onCheckedChange={field.handleChange}
                  />
                )}
              </form.Field>

              <form.Subscribe selector={(state) => state.values.emailEnabled}>
                {(emailEnabled) =>
                  emailEnabled && (
                    <div className="grid gap-4">
                      <div className="grid grid-cols-[1fr_7rem] gap-4">
                        <form.AppField name="smtpHost">
                          {(field) => (
                            <field.AppTextField label="SMTP szerver" />
                          )}
                        </form.AppField>
                        <form.AppField name="smtpPort">
                          {(field) => <field.AppTextField label="Port" />}
                        </form.AppField>
                      </div>
                      <form.Field name="security">
                        {(field) => (
                          <Field>
                            <FieldLabel htmlFor={field.name}>
                              Titkosítás
                            </FieldLabel>
                            <Select
                              value={field.state.value}
                              name={field.name}
                              onValueChange={(value: SmtpSecurityEnum) =>
                                field.handleChange(value)
                              }
                            >
                              <SelectTrigger className="w-full">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {SECURITY_OPTIONS.map((option) => (
                                  <SelectItem
                                    key={option.value}
                                    value={option.value}
                                  >
                                    {option.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </Field>
                        )}
                      </form.Field>
                      <form.AppField name="username">
                        {(field) => (
                          <field.AppTextField label="Felhasználónév" />
                        )}
                      </form.AppField>
                      <form.AppField name="password">
                        {(field) => (
                          <field.AppTextField
                            label="Jelszó"
                            type="password"
                            description={
                              settings.email.passwordSet
                                ? 'Mentett jelszó van beállítva. Hagyd üresen, ha nem módosítod.'
                                : undefined
                            }
                          />
                        )}
                      </form.AppField>
                      <form.AppField name="sender">
                        {(field) => (
                          <field.AppTextField
                            label="Feladó"
                            description="Pl.: StremHU <szerver@example.hu>"
                          />
                        )}
                      </form.AppField>
                      <form.AppField name="recipients">
                        {(field) => (
                          <field.AppTextField
                            label="Címzettek"
                            description="Több címzett esetén vesszővel elválasztva."
                          />
                        )}
                      </form.AppField>
                      <div>
                        <form.SubscribeButton
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleTest('email')}
                        >
                          Mentés és teszt e-mail küldése
                        </form.SubscribeButton>
                      </div>
                    </div>
                  )
                }
              </form.Subscribe>
            </div>

            <Separator />

            {/* Telegram */}
            <div className="grid gap-4">
              <form.Field name="telegramEnabled">
                {(field) => (
                  <SwitchRow
                    id={field.name}
                    title="Telegram értesítés"
                    description={
                      <>
                        Hozz létre egy botot a{' '}
                        <a
                          href="https://t.me/BotFather"
                          target="_blank"
                          rel="noreferrer"
                          className="underline"
                        >
                          @BotFather
                        </a>{' '}
                        segítségével, írj neki egy üzenetet, majd a chat ID-t
                        pl. a{' '}
                        <a
                          href="https://t.me/userinfobot"
                          target="_blank"
                          rel="noreferrer"
                          className="underline"
                        >
                          @userinfobot
                        </a>{' '}
                        mutatja meg.
                      </>
                    }
                    checked={field.state.value}
                    onCheckedChange={field.handleChange}
                  />
                )}
              </form.Field>

              <form.Subscribe
                selector={(state) => state.values.telegramEnabled}
              >
                {(telegramEnabled) =>
                  telegramEnabled && (
                    <div className="grid gap-4">
                      <form.AppField name="botToken">
                        {(field) => (
                          <field.AppTextField
                            label="Bot token"
                            type="password"
                            description={
                              settings.telegram.botTokenSet
                                ? 'Mentett token van beállítva. Hagyd üresen, ha nem módosítod.'
                                : undefined
                            }
                          />
                        )}
                      </form.AppField>
                      <form.AppField name="chatId">
                        {(field) => (
                          <field.AppTextField
                            label="Chat ID"
                            description="Felhasználó, csoport vagy csatorna azonosítója (csoportnál negatív szám)."
                          />
                        )}
                      </form.AppField>
                      <div>
                        <form.SubscribeButton
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleTest('telegram')}
                        >
                          Mentés és teszt üzenet küldése
                        </form.SubscribeButton>
                      </div>
                    </div>
                  )
                }
              </form.Subscribe>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                Mégsem
              </Button>
              <form.SubscribeButton type="submit">Mentés</form.SubscribeButton>
            </DialogFooter>
          </form>
        </form.AppForm>
      </DialogScrollContent>
    </Dialog>
  )
}
