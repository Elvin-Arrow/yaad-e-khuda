<script>
  let {
    label = '',
    value = $bindable(''),
    type = 'text',
    placeholder = '',
    hasError = false,
  } = $props()
</script>

<label class="field">
  <span class="label">{label}</span>
  <input {type} {placeholder} bind:value class:has-error={hasError} autocomplete="off" />
</label>

<style>
  .field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .label {
    font-size: 13px;
    font-weight: 600;
    color: var(--label-secondary);
  }

  input {
    background: var(--surface-2);
    border: 1px solid transparent;
    border-radius: var(--radius-comfortable);
    padding: 12px 14px;
    color: var(--label-primary);
    font-size: 17px;
    font-family: inherit;
  }

  input::placeholder {
    color: var(--label-tertiary);
  }

  input:focus {
    outline: none;
    border-color: var(--accent);
  }

  input.has-error {
    border-color: var(--error);
  }
</style>
