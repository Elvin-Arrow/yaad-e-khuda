<script>
  import { onMount } from 'svelte'
  import { api } from '../api.js'
  import HomePage from './HomePage.svelte'
  import SettingsPage from './SettingsPage.svelte'

  let config = $state(null)
  let todayData = $state(null)
  let loadErr = $state('')
  let page = $state('home')

  async function loadAll() {
    try {
      const [c, t] = await Promise.all([api.getConfig(), api.todayPrayerTimes()])
      config = c
      todayData = t
      loadErr = ''
    } catch (e) {
      loadErr = e.message
    }
  }

  onMount(() => {
    loadAll()
    const id = setInterval(loadAll, 60_000)
    return () => clearInterval(id)
  })
</script>

<div class="shell">
  {#if loadErr}
    <p class="error">Could not reach the server: {loadErr}</p>
  {:else if !config || !todayData}
    <p class="loading">Loading…</p>
  {:else if page === 'settings'}
    <SettingsPage {config} onBack={() => (page = 'home')} onSaved={loadAll} />
  {:else}
    <HomePage {config} {todayData} onOpenSettings={() => (page = 'settings')} onSaved={loadAll} />
  {/if}
</div>

<style>
  .shell {
    max-width: 480px;
    margin: 0 auto;
    padding: var(--space-8) var(--space-5) var(--space-9);
  }

  .loading,
  .error {
    color: var(--label-secondary);
    padding: var(--space-6) 0;
  }

  .error {
    color: var(--error);
  }
</style>
