<script>
  import Card from '../components/Card.svelte'
  import Toggle from '../components/Toggle.svelte'
  import Stepper from '../components/Stepper.svelte'
  import { api } from '../api.js'

  let { config, todayData, onSaved } = $props()

  const PRAYER_NAMES = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']

  let prayers = $state($state.snapshot(config.prayers))

  let saveState = $state('idle')
  let saveTimer

  function scheduleSave() {
    saveState = 'saving'
    clearTimeout(saveTimer)
    saveTimer = setTimeout(async () => {
      try {
        await api.updatePrayers(prayers)
        saveState = 'saved'
        onSaved?.()
        setTimeout(() => {
          saveState = 'idle'
        }, 1500)
      } catch {
        saveState = 'idle'
      }
    }, 500)
  }

  function setEnabled(name, value) {
    prayers[name] = { ...prayers[name], enabled: value }
    scheduleSave()
  }

  function setMinutes(name, value) {
    prayers[name] = { ...prayers[name], minutes_before: value }
    scheduleSave()
  }

  function capitalize(name) {
    return name[0].toUpperCase() + name.slice(1)
  }

  function formatTime(iso) {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
</script>

<Card>
  <div class="card-header">
    <h2>Prayers</h2>
    {#if saveState === 'saving'}<span class="status">Saving…</span>{/if}
    {#if saveState === 'saved'}<span class="status saved">Saved</span>{/if}
  </div>

  {#each PRAYER_NAMES as name (name)}
    <div class="row">
      <div class="info">
        <span class="name">{capitalize(name)}</span>
        <span class="times tabular">
          {formatTime(todayData.prayers[name].adhan)} adhan · {formatTime(
            todayData.prayers[name].iqama,
          )} iqama
        </span>
      </div>
      <Stepper value={prayers[name].minutes_before} onchange={(v) => setMinutes(name, v)} />
      <Toggle
        checked={prayers[name].enabled}
        ariaLabel="Enable {capitalize(name)}"
        onchange={(v) => setEnabled(name, v)}
      />
    </div>
  {/each}
</Card>

<style>
  .row {
    display: flex;
    align-items: center;
    gap: var(--space-5);
    padding: var(--space-3) 0;
    border-bottom: 1px solid var(--separator);
  }

  .row:last-child {
    border-bottom: none;
  }

  .info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    min-width: 0;
  }

  .name {
    font-size: 17px;
    font-weight: 600;
  }

  .times {
    font-size: 12px;
    color: var(--label-tertiary);
  }
</style>
