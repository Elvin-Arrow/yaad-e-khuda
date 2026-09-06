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
    </div>
    <button class="icon-btn" onclick={onOpenSettings} aria-label="Open settings">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path
          d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"
          stroke="currentColor"
          stroke-width="1.8"
        />
        <path
          d="M19.4 13.5a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V19.5a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H4.5a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 6.1 8.6a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H10.5a1.65 1.65 0 0 0 1-1.51V2.5a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V8.5a1.65 1.65 0 0 0 1.51 1h.09a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"
          stroke="currentColor"
          stroke-width="1.4"
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
