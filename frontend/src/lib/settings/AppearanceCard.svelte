<script>
  import Card from '../components/Card.svelte'
  import Toggle from '../components/Toggle.svelte'
  import { applyTheme, currentTheme } from '../theme.js'

  let isLight = $state(currentTheme() === 'light')

  function toggle(value) {
    isLight = value
    applyTheme(value ? 'light' : 'dark')
  }
</script>

<Card>
  <h2>Appearance</h2>
  <div class="row">
    <span class="label">Light mode</span>
    <Toggle checked={isLight} ariaLabel="Light mode" onchange={toggle} />
  </div>
</Card>

<style>
  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .label {
    font-size: 17px;
    font-weight: 600;
  }
</style>
