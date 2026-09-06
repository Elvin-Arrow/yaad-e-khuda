<script>
  import Card from '../components/Card.svelte'
  import Button from '../components/Button.svelte'
  import Toast from '../components/Toast.svelte'
  import { api, ApiError } from '../api.js'

  let { config, onSaved } = $props()

  // svelte-ignore state_referenced_locally -- deliberate: seed once, see MosqueCard.svelte
  let time = $state(config.schedule.time)
  let saving = $state(false)
  let error = $state('')
  let success = $state(false)

  async function save() {
    error = ''
    success = false
    saving = true
    try {
      await api.updateSchedule({ time })
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
  <h2>Daily sync time</h2>
  <p class="hint">The server fetches today's times and syncs the calendar automatically once a day.</p>
  <input type="time" bind:value={time} class="time-input tabular" />
  {#if error}<Toast kind="error">{error}</Toast>{/if}
  {#if success}<Toast kind="success">Saved</Toast>{/if}
  <Button variant="filled" disabled={saving} onclick={save}>
    {saving ? 'Saving…' : 'Save'}
  </Button>
</Card>

<style>
  .time-input {
    background: var(--surface-2);
    border: 1px solid transparent;
    border-radius: var(--radius-comfortable);
    padding: 10px 14px;
    color: var(--label-primary);
    font-size: 17px;
    color-scheme: var(--color-scheme);
    align-self: flex-start;
  }
</style>
