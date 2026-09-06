<script>
  let { checked = false, disabled = false, ariaLabel = 'Toggle', onchange } = $props()
</script>

<button
  class="toggle"
  class:on={checked}
  {disabled}
  role="switch"
  aria-checked={checked}
  aria-label={ariaLabel}
  onclick={() => onchange?.(!checked)}
>
  <span class="knob"></span>
</button>

<style>
  .toggle {
    width: 51px;
    height: 31px;
    border-radius: var(--radius-pill);
    background: var(--fill-neutral);
    border: none;
    padding: 2px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    transition: background-color 150ms ease;
    flex-shrink: 0;
  }

  .toggle.on {
    background: var(--accent);
  }

  .toggle:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .knob {
    display: block;
    width: 27px;
    height: 27px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
    transition: transform 150ms ease;
  }

  .toggle.on .knob {
    transform: translateX(20px);
  }
</style>
