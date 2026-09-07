<script>
  let { value = 0, min = 0, max = 120, step = 1, onchange } = $props()

  function dec() {
    onchange?.(Math.max(min, value - step))
  }
  function inc() {
    onchange?.(Math.min(max, value + step))
  }

  function commit(e) {
    const parsed = Number(e.target.value)
    if (Number.isNaN(parsed)) {
      e.target.value = value
      return
    }
    onchange?.(Math.min(max, Math.max(min, parsed)))
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') e.target.blur()
  }
</script>

<div class="stepper">
  <button class="step" onclick={dec} disabled={value <= min} aria-label="Decrease minutes">−</button>
  <span class="value-wrap">
    <input
      class="value tabular"
      type="number"
      inputmode="numeric"
      {min}
      {max}
      {step}
      {value}
      onchange={commit}
      onkeydown={handleKeydown}
      aria-label="Minutes before"
    />
    <span class="unit">min</span>
  </span>
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
    flex-shrink: 0;
  }

  .step:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .value-wrap {
    display: flex;
    align-items: baseline;
    gap: 3px;
  }

  .value {
    width: 32px;
    text-align: center;
    font-size: 14px;
    font-weight: 600;
    color: var(--label-primary);
    background: transparent;
    border: none;
    border-radius: var(--radius-standard);
    padding: 4px 0;
    font-family: inherit;
    -moz-appearance: textfield;
  }

  .value::-webkit-inner-spin-button,
  .value::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }

  .value:focus {
    outline: none;
    background: var(--surface-2);
  }

  .unit {
    font-size: 11px;
    font-weight: 600;
    color: var(--label-tertiary);
  }
</style>
