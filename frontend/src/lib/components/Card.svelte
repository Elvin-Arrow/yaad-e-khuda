<script>
  let { children } = $props()
</script>

<div class="card">
  {@render children()}
</div>

<style>
  .card {
    background: var(--surface-1);
    border-radius: var(--radius-hero);
    padding: var(--space-6);
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
  }

  .card :global(h2) {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.3px;
  }

  .card :global(.hint) {
    font-size: 13px;
    color: var(--label-secondary);
    line-height: 1.35;
  }

  .card :global(.card-header) {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .card :global(.status) {
    font-size: 12px;
    font-weight: 600;
    color: var(--label-tertiary);
  }

  .card :global(.status.saved) {
    color: var(--success);
  }
</style>
