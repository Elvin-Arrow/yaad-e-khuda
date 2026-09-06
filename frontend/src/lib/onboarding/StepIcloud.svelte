<script>
  import Card from '../components/Card.svelte'
  import TextField from '../components/TextField.svelte'
  import Button from '../components/Button.svelte'
  import Toast from '../components/Toast.svelte'
  import { api, ApiError } from '../api.js'

  let { onDone } = $props()

  let appleId = $state('')
  let password = $state('')
  let submitting = $state(false)
  let error = $state('')

  async function submit() {
    error = ''
    submitting = true
    try {
      await api.setupIcloud({ apple_id: appleId, app_specific_password: password })
      onDone()
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Something went wrong.'
    } finally {
      submitting = false
    }
  }
</script>

<Card>
  <h2>Connect iCloud</h2>
  <p class="hint">
    Use an app-specific password — never your real Apple ID password. Generate one at
    appleid.apple.com, under Security → App-Specific Passwords.
  </p>
  <TextField label="Apple ID" type="email" bind:value={appleId} placeholder="you@icloud.com" />
  <TextField
    label="App-Specific Password"
    type="password"
    bind:value={password}
    placeholder="xxxx-xxxx-xxxx-xxxx"
    hasError={!!error}
  />
  {#if error}<Toast kind="error">{error}</Toast>{/if}
  <Button variant="primary" full disabled={submitting || !appleId || !password} onclick={submit}>
    {submitting ? 'Connecting…' : 'Continue'}
  </Button>
</Card>
