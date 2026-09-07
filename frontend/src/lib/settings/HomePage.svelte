<script>
  import NextPrayerRing from '../components/NextPrayerRing.svelte'
  import PrayersCard from './PrayersCard.svelte'
  import SyncStatusCard from './SyncStatusCard.svelte'

  let { config, todayData, onOpenSettings, onSaved } = $props()
</script>

<div class="page">
  <header>
    <div>
      <p class="eyebrow">TODAY</p>
      <h1>Prayer Reminders</h1>
      {#if todayData.mosque_name}
        <p class="mosque-name">{todayData.mosque_name}</p>
      {/if}
    </div>
    <button class="icon-btn" onclick={onOpenSettings} aria-label="Open settings">
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <circle cx="12" cy="12" r="3" />
        <path
          d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
        />
      </svg>
    </button>
  </header>

  <NextPrayerRing nextPrayer={todayData.next_prayer} />

  <div class="cards">
    <PrayersCard {config} {todayData} {onSaved} />
    <SyncStatusCard onSynced={onSaved} />
  </div>
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
  }

  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
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

  .mosque-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--label-secondary);
    margin-top: 2px;
  }

  .icon-btn {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: none;
    background: var(--fill-neutral);
    color: var(--label-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .icon-btn:active {
    background: var(--fill-neutral-pressed);
  }

  .cards {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }
</style>
