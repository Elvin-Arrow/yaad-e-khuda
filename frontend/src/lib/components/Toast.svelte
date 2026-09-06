<script>
  let { kind = 'error', children } = $props()
</script>

<div class="toast {kind}">
  {@render children()}
</div>

<style>
  .toast {
    padding: 10px 14px;
    border-radius: var(--radius-comfortable);
    font-size: 13px;
    font-weight: 600;
    line-height: 1.35;
  }

  .toast.error {
    background: rgba(255, 69, 58, 0.15);
    color: var(--error);
  }

  .toast.success {
    background: rgba(48, 209, 88, 0.15);
    color: var(--success);
  }
</style>
