<script>
  import AppearanceCard from './AppearanceCard.svelte'
  import MosqueCard from './MosqueCard.svelte'
  import ICloudCard from './ICloudCard.svelte'
  import ScheduleCard from './ScheduleCard.svelte'

  let { config, onBack, onSaved } = $props()
</script>

<div class="page">
  <header>
    <button class="icon-btn" onclick={onBack} aria-label="Back">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path
          d="M15 5l-7 7 7 7"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>
    <h1>Settings</h1>
    <span class="spacer"></span>
  </header>

  <div class="cards">
    <AppearanceCard />
    <MosqueCard {config} {onSaved} />
    <ICloudCard {config} {onSaved} />
    <ScheduleCard {config} {onSaved} />
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
    align-items: center;
    gap: var(--space-3);
  }

  h1 {
    flex: 1;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.4px;
  }

  .spacer {
    width: 40px;
    flex-shrink: 0;
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
