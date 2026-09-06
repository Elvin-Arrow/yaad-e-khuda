<script>
  import Card from '../components/Card.svelte'
  import TextField from '../components/TextField.svelte'
  import Button from '../components/Button.svelte'
  import Toast from '../components/Toast.svelte'
  import { api, ApiError } from '../api.js'

  let { config, onSaved } = $props()

  // svelte-ignore state_referenced_locally -- deliberate: seed once, see MosqueCard.svelte
  let appleId = $state(config.icloud.apple_id)
  // svelte-ignore state_referenced_locally
  let calendarName = $state(config.icloud.calendar_name)
  let password = $state('')
  let saving = $state(false)
  let error = $state('')
  let success = $state(false)

  async function save() {
    error = ''
    success = false
    saving = true
    try {
      const body = { apple_id: appleId, calendar_name: calendarName }
      if (password) body.app_specific_password = password
      await api.updateIcloud(body)
      password = ''
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
</script>

<Card>
  <h2>iCloud</h2>
  <TextField label="Apple ID" type="email" bind:value={appleId} />
  <TextField label="Calendar name" bind:value={calendarName} />
  <TextField
    label="App-Specific Password"
    type="password"
    bind:value={password}
    placeholder="Leave blank to keep the current one"
    hasError={!!error}
  />
  {#if error}<Toast kind="error">{error}</Toast>{/if}
  {#if success}<Toast kind="success">Saved</Toast>{/if}
  <Button variant="filled" disabled={saving} onclick={save}>
    {saving ? 'Checking…' : 'Save'}
  </Button>
</Card>
