<script>
  import Card from '../components/Card.svelte'
  import TextField from '../components/TextField.svelte'
  import Button from '../components/Button.svelte'
  import Toast from '../components/Toast.svelte'
  import { api, ApiError } from '../api.js'

  let { config, onSaved } = $props()

  let clientId = $state(config.google.client_id || '')
  let clientSecret = $state('')
  let calendarName = $state(config.google.calendar_name)
  let saving = $state(false)
  let disconnecting = $state(false)
  let error = $state('')
  let success = $state(false)

  async function saveAndConnect() {
    error = ''
    success = false
    saving = true
    try {
      const body = { client_id: clientId, calendar_name: calendarName }
      if (clientSecret) body.client_secret = clientSecret
      await api.updateGoogle(body)
      window.location.href = api.googleOauthStartUrl()
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Something went wrong.'
      saving = false
    }
  }

  async function save() {
    error = ''
    success = false
    saving = true
    try {
      const body = { calendar_name: calendarName }
      await api.updateGoogle(body)
      success = true
      onSaved?.()
      setTimeout(() => {
        success = false
      }, 1500)
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Something went wrong.'
    } finally {
      saving = false
    }
  }

  async function disconnect() {
    error = ''
    disconnecting = true
    try {
      await api.disconnectGoogle()
      onSaved?.()
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Something went wrong.'
    } finally {
      disconnecting = false
    }
  }
</script>

<Card>
  <div class="card-header">
    <h2>Google Calendar</h2>
    {#if config.google.connected}<span class="status saved">Connected</span>{/if}
  </div>

  {#if !config.google.connected}
    <p class="hint">
      Create an OAuth client (type "Web application") in the Google Cloud Console, enable the
      Calendar API, and register this app's own address plus
      <code>/api/google/oauth/callback</code> as an authorized redirect URI.
    </p>
  {/if}

  <TextField label="Client ID" bind:value={clientId} />
  <TextField
    label="Client Secret"
    type="password"
    bind:value={clientSecret}
    placeholder={config.google.configured ? 'Leave blank to keep the current one' : ''}
  />
  <TextField label="Calendar name" bind:value={calendarName} />

  {#if error}<Toast kind="error">{error}</Toast>{/if}
  {#if success}<Toast kind="success">Saved</Toast>{/if}

  {#if config.google.connected}
    <div class="row">
      <Button variant="filled" disabled={saving} onclick={save}>
        {saving ? 'Saving…' : 'Save'}
      </Button>
      <Button variant="tinted" disabled={disconnecting} onclick={disconnect}>
        {disconnecting ? 'Disconnecting…' : 'Disconnect'}
      </Button>
    </div>
  {:else}
    <Button
      variant="filled"
      disabled={saving || !clientId || (!clientSecret && !config.google.configured)}
      onclick={saveAndConnect}
    >
      {saving ? 'Connecting…' : 'Connect Google Calendar'}
    </Button>
  {/if}
</Card>

<style>
  .row {
    display: flex;
    gap: var(--space-3);
  }

  code {
    font-size: 12px;
  }
</style>
