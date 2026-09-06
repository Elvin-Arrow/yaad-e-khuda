<script>
  let { value = 0, min = 0, max = 120, step = 1, onchange } = $props()

  function dec() {
    onchange?.(Math.max(min, value - step))
  }
  function inc() {
    onchange?.(Math.min(max, value + step))
  }
</script>

<div class="stepper">
  <button class="step" onclick={dec} disabled={value <= min} aria-label="Decrease minutes">−</button>
  <span class="value tabular">{value}m</span>
  <button class="step" onclick={inc} disabled={value >= max} aria-label="Increase minutes">+</button>
</div>

<style>
  .stepper {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    background: var(--fill-neutral);
    border-radius: var(--radius-comfortable);
    padding: 4px;
    flex-shrink: 0;
  }

  .step {
    width: 30px;
    height: 30px;
    border-radius: var(--radius-standard);
    border: none;
    background: var(--surface-3);
    color: var(--label-primary);
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .step:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .value {
    min-width: 40px;
    text-align: center;
    font-size: 14px;
    font-weight: 600;
    color: var(--label-primary);
  }
</style>
