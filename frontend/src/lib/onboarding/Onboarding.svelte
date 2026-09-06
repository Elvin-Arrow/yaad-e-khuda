<script>
  import StepIcloud from './StepIcloud.svelte'
  import StepMosque from './StepMosque.svelte'
  import Card from '../components/Card.svelte'

  let { onComplete } = $props()

  let step = $state(1)
  let preview = $state(null)

  function handleIcloudDone() {
    step = 2
  }

  function handleMosqueDone(result) {
    preview = result
    step = 3
    setTimeout(onComplete, 1800)
  }

  function formatTime(iso) {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
</script>

<div class="onboarding">
  <div class="brand">
    <div class="mark"></div>
    <h1>Prayer Reminders</h1>
    <p class="step-label">Step {Math.min(step, 2)} of 2</p>
  </div>

  <div class="content">
    {#if step === 1}
      <StepIcloud onDone={handleIcloudDone} />
    {:else if step === 2}
      <StepMosque onDone={handleMosqueDone} />
    {:else}
      <Card>
        <h2>All set!</h2>
        <p class="hint">Here's what we found for today:</p>
        {#if preview}
          <ul class="preview-list">
            {#each Object.entries(preview.preview) as [name, times]}
              <li>
                <span class="name">{name[0].toUpperCase() + name.slice(1)}</span>
                <span class="time tabular">{formatTime(times.iqama)}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </Card>
    {/if}
  </div>
</div>

<style>
  .onboarding {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--space-9) var(--space-5);
    gap: var(--space-8);
  }

  .brand {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
    text-align: center;
  }

  .mark {
    width: 56px;
    height: 56px;
    border-radius: var(--radius-hero);
    background: radial-gradient(circle at 35% 35%, var(--accent), var(--accent-pressed));
    box-shadow: 0 0 24px rgba(255, 55, 95, 0.45);
  }

  h1 {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.5px;
  }

  .step-label {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    color: var(--accent);
  }

  .content {
    width: 100%;
    max-width: 420px;
  }

  .preview-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .preview-list li {
    display: flex;
    justify-content: space-between;
    font-size: 15px;
    padding: var(--space-3) 0;
    border-bottom: 1px solid var(--separator);
  }

  .preview-list li:last-child {
    border-bottom: none;
  }

  .preview-list .name {
    font-weight: 600;
  }

  .preview-list .time {
    color: var(--label-secondary);
  }
</style>
