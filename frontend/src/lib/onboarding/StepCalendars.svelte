<script>
  import { onMount } from 'svelte'
  import Card from '../components/Card.svelte'
  import TextField from '../components/TextField.svelte'
  import Button from '../components/Button.svelte'
  import Toast from '../components/Toast.svelte'
  import { api, ApiError } from '../api.js'

  let { onDone } = $props()

  let hasIcloud = $state(false)
  let hasGoogle = $state(false)
  let statusLoaded = $state(false)
  let justConnectedGoogle = $state(false)

  let appleId = $state('')
  let icloudPassword = $state('')
  let icloudSubmitting = $state(false)
  let icloudError = $state('')

  let googleClientId = $state('')
  let googleClientSecret = $state('')
  let googleSubmitting = $state(false)
  let googleError = $state('')

  async function loadStatus() {
    const status = await api.setupStatus()
    hasIcloud = status.has_icloud
    hasGoogle = status.has_google
    statusLoaded = true
  }

  onMount(() => {
    if (new URLSearchParams(window.location.search).get('google') === 'connected') {
      justConnectedGoogle = true
      const url = new URL(window.location.href)
      url.searchParams.delete('google')
      window.history.replaceState({}, '', url)
    }
    loadStatus()
  })

  async function connectIcloud() {
    icloudError = ''
    icloudSubmitting = true
    try {
      await api.setupIcloud({ apple_id: appleId, app_specific_password: icloudPassword })
      hasIcloud = true
    } catch (e) {
      icloudError = e instanceof ApiError ? e.message : 'Something went wrong.'
    } finally {
      icloudSubmitting = false
    }
  }

  async function connectGoogle() {
    googleError = ''
    googleSubmitting = true
    try {
      await api.updateGoogle({ client_id: googleClientId, client_secret: googleClientSecret })
      window.location.href = api.googleOauthStartUrl()
    } catch (e) {
      googleError = e instanceof ApiError ? e.message : 'Something went wrong.'
      googleSubmitting = false
    }
  }
</script>

<div class="steps">
  <Card>
    <div class="card-header">
      <h2>Connect iCloud</h2>
      {#if hasIcloud}<span class="status saved">Connected</span>{/if}
    </div>
    {#if !hasIcloud}
      <p class="hint">
        Use an app-specific password — never your real Apple ID password. Generate one at
        appleid.apple.com, under Security → App-Specific Passwords.
      </p>
      <TextField label="Apple ID" type="email" bind:value={appleId} placeholder="you@icloud.com" />
      <TextField
        label="App-Specific Password"
        type="password"
        bind:value={icloudPassword}
        placeholder="xxxx-xxxx-xxxx-xxxx"
        hasError={!!icloudError}
      />
      {#if icloudError}<Toast kind="error">{icloudError}</Toast>{/if}
      <Button
        variant="filled"
        full
        disabled={icloudSubmitting || !appleId || !icloudPassword}
        onclick={connectIcloud}
      >
        {icloudSubmitting ? 'Connecting…' : 'Connect iCloud'}
      </Button>
    {/if}
  </Card>

  <Card>
    <div class="card-header">
      <h2>Connect Google Calendar</h2>
      {#if hasGoogle}<span class="status saved">Connected</span>{/if}
    </div>
    {#if justConnectedGoogle && hasGoogle}<Toast kind="success">Connected</Toast>{/if}
    {#if !hasGoogle}
      <p class="hint">
        Create an OAuth client (type "Web application") in the Google Cloud Console, enable the
        Calendar API, and register this app's own address plus
        <code>/api/google/oauth/callback</code> as an authorized redirect URI.
      </p>
      <TextField label="Client ID" bind:value={googleClientId} />
      <TextField label="Client Secret" type="password" bind:value={googleClientSecret} />
      {#if googleError}<Toast kind="error">{googleError}</Toast>{/if}
      <Button
        variant="filled"
        full
        disabled={googleSubmitting || !googleClientId || !googleClientSecret}
        onclick={connectGoogle}
      >
        {googleSubmitting ? 'Connecting…' : 'Connect Google Calendar'}
      </Button>
    {/if}
  </Card>

  {#if statusLoaded}
    <Button variant="primary" full disabled={!hasIcloud && !hasGoogle} onclick={onDone}>
      Continue
    </Button>
  {/if}
</div>

<style>
  .steps {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
  }

  code {
    font-size: 12px;
  }
</style>
