<script>
  // A single-ring nod to the Fitness rings motif: progress from the
  // previous enabled prayer's Iqama to the next one, Move-pink on a
  // 22%-opacity track, tabular countdown at center.
  let { nextPrayer } = $props()

  let now = $state(new Date())

  $effect(() => {
    const id = setInterval(() => {
      now = new Date()
    }, 1000)
    return () => clearInterval(id)
  })

  const SIZE = 208
  const STROKE = 14
  const RADIUS = (SIZE - STROKE) / 2
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS

  let progress = $derived(
    nextPrayer && !nextPrayer.resting && nextPrayer.progress != null ? nextPrayer.progress : 0,
  )
  let dashoffset = $derived(CIRCUMFERENCE * (1 - progress))

  function capitalize(name) {
    return name ? name[0].toUpperCase() + name.slice(1) : ''
  }

  let countdownLabel = $derived.by(() => {
    if (!nextPrayer?.iqama) return '—'
    const diffMs = new Date(nextPrayer.iqama) - now
    if (diffMs <= 0) return 'Now'
    const totalMinutes = Math.floor(diffMs / 60000)
    const hours = Math.floor(totalMinutes / 60)
    const minutes = totalMinutes % 60
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
  })

  let nextLabel = $derived.by(() => {
    if (!nextPrayer) return 'No prayers enabled'
    const name = capitalize(nextPrayer.name)
    if (!nextPrayer.iqama) return `Next: ${name} — tomorrow`
    const time = new Date(nextPrayer.iqama).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })
    return `Next: ${name} at ${time}`
  })
</script>

<div class="hero">
  <svg width={SIZE} height={SIZE} viewBox="0 0 {SIZE} {SIZE}">
    <circle
      cx={SIZE / 2}
      cy={SIZE / 2}
      r={RADIUS}
      fill="none"
      stroke="var(--accent-track)"
      stroke-width={STROKE}
    />
    <circle
      cx={SIZE / 2}
      cy={SIZE / 2}
      r={RADIUS}
      fill="none"
      stroke="var(--accent)"
      stroke-width={STROKE}
      stroke-linecap="round"
      stroke-dasharray={CIRCUMFERENCE}
      stroke-dashoffset={dashoffset}
      transform="rotate(-90 {SIZE / 2} {SIZE / 2})"
      class="progress"
    />
    <text x="50%" y="47%" text-anchor="middle" class="countdown tabular">{countdownLabel}</text>
    <text x="50%" y="60%" text-anchor="middle" class="sub">REMAINING</text>
  </svg>
  <p class="next-label">{nextLabel}</p>
</div>

<style>
  .hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-5);
    padding: var(--space-7) 0 var(--space-5);
  }

  .progress {
    filter: drop-shadow(0 0 10px rgba(255, 55, 95, 0.55));
    transition: stroke-dashoffset 600ms ease-out;
  }

  .countdown {
    fill: var(--label-primary);
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -0.5px;
  }

  .sub {
    fill: var(--label-tertiary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.4px;
  }

  .next-label {
    font-size: 15px;
    font-weight: 600;
    color: var(--label-secondary);
  }
</style>
