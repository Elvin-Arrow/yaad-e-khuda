<script>
  import { onMount } from 'svelte'
  import { api } from '../api.js'
  import NextPrayerRing from '../components/NextPrayerRing.svelte'
  import PrayersCard from './PrayersCard.svelte'
  import MosqueCard from './MosqueCard.svelte'
  import ICloudCard from './ICloudCard.svelte'
  import ScheduleCard from './ScheduleCard.svelte'
  import SyncStatusCard from './SyncStatusCard.svelte'

  let config = $state(null)
  let todayData = $state(null)
  let loadErr = $state('')

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
    const id = setInterval(loadAll, 60_000) // keep the ring/times fresh
    return () => clearInterval(id)
  })
</script>

<div class="settings">
  <header>
    <p class="eyebrow">TODAY</p>
    <h1>Prayer Reminders</h1>
  </header>

  {#if loadErr}
    <p class="error">Could not reach the server: {loadErr}</p>
  {:else if !config || !todayData}
    <p class="loading">Loading…</p>
  {:else}
    <NextPrayerRing nextPrayer={todayData.next_prayer} />
    <div class="cards">
      <PrayersCard {config} {todayData} onSaved={loadAll} />
      <SyncStatusCard onSynced={loadAll} />
      <MosqueCard {config} onSaved={loadAll} />
      <ICloudCard {config} onSaved={loadAll} />
      <ScheduleCard {config} onSaved={loadAll} />
    </div>
  {/if}
</div>

<style>
  .settings {
    max-width: 480px;
    margin: 0 auto;
    padding: var(--space-8) var(--space-5) var(--space-9);
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
  }

  header {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .eyebrow {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.4px;
    color: var(--accent);
  }

  h1 {
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -0.8px;
  }

  .cards {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
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
