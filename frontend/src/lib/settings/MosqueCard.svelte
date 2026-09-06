<script>
  import Card from '../components/Card.svelte'
  import TextField from '../components/TextField.svelte'
  import Button from '../components/Button.svelte'
  import Toast from '../components/Toast.svelte'
  import { api, ApiError } from '../api.js'

  let { config, onSaved } = $props()

  // svelte-ignore state_referenced_locally -- deliberate: seed the editable
  // field once from the loaded config, don't let a background poll refresh
  // clobber an in-progress edit.
  let slug = $state(config.mosque.slug)
  let saving = $state(false)
  let error = $state('')
  let success = $state(false)

  async function save() {
    error = ''
    success = false
    saving = true
    try {
      await api.updateMosque({ slug })
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
  <h2>Mosque</h2>
  <TextField label="Mawaqit slug" bind:value={slug} hasError={!!error} />
  {#if error}<Toast kind="error">{error}</Toast>{/if}
  {#if success}<Toast kind="success">Saved</Toast>{/if}
  <Button variant="filled" disabled={saving || slug === config.mosque.slug} onclick={save}>
    {saving ? 'Checking…' : 'Save'}
  </Button>
</Card>
