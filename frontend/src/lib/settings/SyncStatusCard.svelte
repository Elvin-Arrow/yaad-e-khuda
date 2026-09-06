<script>
  import { onMount } from 'svelte'
  import Card from '../components/Card.svelte'
  import Button from '../components/Button.svelte'
  import { api } from '../api.js'

  let { onSynced } = $props()

  let status = $state(null)
  let running = $state(false)

  async function load() {
    try {
      status = await api.syncStatus()
    } catch {
      // leave status as-is; the card just shows nothing extra
    }
  }

  async function runNow() {
    running = true
    try {
      status = await api.syncRun()
      onSynced?.()
    } finally {
      running = false
    }
  }

  onMount(load)

  function formatWhen(iso) {
    if (!iso) return 'Never run yet'
    return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
  }
</script>

<Card>
  <div class="card-header">
    <h2>Sync</h2>
  </div>
  {#if status}
    <p class="last-run">Last run: <span class="tabular">{formatWhen(status.ran_at)}</span></p>
    {#if status.ok === false}
      <p class="fail-text">{status.fetch?.message || status.sync?.message}</p>
    {:else if status.ok === true}
      <p class="ok-text">Succeeded</p>
    {/if}
  {/if}
  <Button variant="tinted" disabled={running} onclick={runNow}>
    {running ? 'Syncing…' : 'Sync Now'}
  </Button>
</Card>

<style>
  .last-run {
    font-size: 14px;
    color: var(--label-secondary);
  }

  .fail-text {
    font-size: 13px;
    color: var(--error);
  }

  .ok-text {
    font-size: 13px;
    color: var(--success);
  }
</style>
