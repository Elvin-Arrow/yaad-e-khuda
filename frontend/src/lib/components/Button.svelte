<script>
  let {
    variant = 'primary',
    disabled = false,
    full = false,
    type = 'button',
    onclick,
    children,
  } = $props()
</script>

<button class="btn {variant}" class:full {type} {disabled} onclick={disabled ? undefined : onclick}>
  {@render children()}
</button>

<style>
  .btn {
    border: none;
    cursor: pointer;
    border-radius: var(--radius-card);
    transition:
      background-color 120ms ease,
      transform 120ms ease,
      color 120ms ease;
  }

  .btn:active {
    transform: scale(0.98);
  }

  .btn:disabled {
    cursor: default;
    transform: none;
  }

  .btn.full {
    width: 100%;
  }

  .btn.primary {
    background: var(--accent);
    color: #fff;
    font-size: 17px;
    font-weight: 600;
    letter-spacing: -0.2px;
    padding: 15px 30px;
  }
  .btn.primary:active {
    background: var(--accent-pressed);
  }
  .btn.primary:disabled {
    background: var(--fill-neutral);
    color: var(--label-tertiary);
  }

  .btn.tinted {
    background: var(--accent-tint);
    color: var(--accent);
    font-size: 15px;
    font-weight: 600;
    border-radius: var(--radius-comfortable);
    padding: 10px 18px;
  }
  .btn.tinted:active {
    background: var(--accent-tint-pressed);
  }
  .btn.tinted:disabled {
    color: var(--label-tertiary);
    background: var(--fill-neutral);
  }

  .btn.filled {
    background: var(--fill-neutral);
    color: var(--label-primary);
    font-size: 15px;
    font-weight: 600;
    border-radius: var(--radius-comfortable);
    padding: 10px 18px;
  }
  .btn.filled:active {
    background: var(--fill-neutral-pressed);
  }
  .btn.filled:disabled {
    color: var(--label-tertiary);
  }

  .btn.plain {
    background: none;
    color: var(--accent);
    font-size: 17px;
    font-weight: 600;
    padding: 0;
  }
  .btn.plain:disabled {
    color: var(--label-tertiary);
  }
</style>
