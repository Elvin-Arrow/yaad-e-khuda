<script>
  import { onMount } from 'svelte'
  import { api } from './lib/api.js'
  import Onboarding from './lib/onboarding/Onboarding.svelte'
  import Settings from './lib/settings/Settings.svelte'

  let status = $state(null) // null = still loading
  let loadError = $state('')

  async function loadStatus() {
    try {
      status = await api.setupStatus()
      loadError = ''
    } catch (e) {
      loadError = e.message
    }
  }

  onMount(loadStatus)
</script>

<main>
  {#if loadError}
    <p class="error">Could not reach the server: {loadError}</p>
  {:else if status === null}
    <p class="loading">Loading…</p>
  {:else if !status.complete}
    <Onboarding onComplete={loadStatus} />
  {:else}
    <Settings />
  {/if}
</main>

<style>
  main {
    min-height: 100vh;
  }

  .loading,
  .error {
    padding: var(--space-9);
    color: var(--label-secondary);
    text-align: center;
  }

  .error {
    color: var(--error);
  }
</style>
