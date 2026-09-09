<script>
  import { onMount } from 'svelte'
  import { api } from '../api.js'
  import HomePage from './HomePage.svelte'
  import SettingsPage from './SettingsPage.svelte'
  import Toast from '../components/Toast.svelte'

  let config = $state(null)
  let todayData = $state(null)
  let loadErr = $state('')
  let page = $state('home')
  let googleConnectedToast = $state(false)

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
    if (new URLSearchParams(window.location.search).get('google') === 'connected') {
      page = 'settings'
      googleConnectedToast = true
      const url = new URL(window.location.href)
      url.searchParams.delete('google')
      window.history.replaceState({}, '', url)
      setTimeout(() => {
        googleConnectedToast = false
      }, 2500)
    }

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
    {#if googleConnectedToast}<Toast kind="success">Google Calendar connected</Toast>{/if}
    <SettingsPage {config} onBack={() => (page = 'home')} onSaved={loadAll} />
  {:else}
    <HomePage {config} {todayData} onOpenSettings={() => (page = 'settings')} onSaved={loadAll} />
  {/if}
</div>

<style>
  .shell {
    max-width: 480px;
    margin: 0 auto;
    padding: calc(var(--space-8) + env(safe-area-inset-top))
      calc(var(--space-5) + env(safe-area-inset-right))
      calc(var(--space-9) + env(safe-area-inset-bottom))
      calc(var(--space-5) + env(safe-area-inset-left));
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
