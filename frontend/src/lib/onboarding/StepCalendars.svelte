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
  <div class="intro">
    <h2>Connect a calendar first</h2>
    <p>
      Yaad creates prayer reminders as events in a calendar you own, so your phone can deliver
      its normal Calendar alarms. Connect iCloud, Google Calendar, or both to continue.
    </p>
    <p class="choice">Choose a calendar below, then enter its connection details.</p>
  </div>

  <Card>
    <div class="card-header">
      <h3>iCloud Calendar</h3>
      {#if hasIcloud}<span class="status saved">Connected</span>{/if}
    </div>
    {#if !hasIcloud}
      <p class="hint">
        Use an app-specific password — never your real Apple ID password. Generate one at
        appleid.apple.com, under Security → App-Specific Passwords.
        <a
          href="https://github.com/Elvin-Arrow/yaad-e-khuda/blob/main/docs/calendar-connections.md#connect-icloud-calendar"
          target="_blank"
          rel="noreferrer"
        >
          Read the step-by-step iCloud guide.
        </a>
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
      <h3>Google Calendar</h3>
      {#if hasGoogle}<span class="status saved">Connected</span>{/if}
    </div>
    {#if justConnectedGoogle && hasGoogle}<Toast kind="success">Connected</Toast>{/if}
    {#if !hasGoogle}
      <p class="hint">
        Create an OAuth client (type "Web application") in the Google Cloud Console, enable the
        Calendar API, and register this app's own address plus
        <code>/api/google/oauth/callback</code> as an authorized redirect URI.
        <a
          href="https://github.com/Elvin-Arrow/yaad-e-khuda/blob/main/docs/calendar-connections.md#connect-google-calendar"
          target="_blank"
          rel="noreferrer"
        >
          Read the step-by-step Google guide.
        </a>
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

  .intro {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: 0 var(--space-2);
  }

  .intro h2 {
    font-size: 22px;
    font-weight: 750;
    letter-spacing: -0.35px;
  }

  .intro p {
    color: var(--label-secondary);
    font-size: 15px;
    line-height: 1.45;
  }

  .intro .choice {
    color: var(--label-primary);
    font-weight: 600;
  }

  a {
    color: var(--accent);
    font-weight: 600;
  }

  code {
    font-size: 12px;
  }
</style>
