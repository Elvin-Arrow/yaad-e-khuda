<script>
  import Card from '../components/Card.svelte'
  import TextField from '../components/TextField.svelte'
  import Button from '../components/Button.svelte'
  import Toast from '../components/Toast.svelte'
  import { api, ApiError } from '../api.js'

  let { onDone } = $props()

  let slug = $state('')
  let submitting = $state(false)
  let error = $state('')

  async function submit() {
    error = ''
    submitting = true
    try {
      const result = await api.setupMosque({ slug })
      onDone(result)
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'Something went wrong.'
    } finally {
      submitting = false
    }
  }
</script>

<Card>
  <h2>Find your mosque</h2>
  <p class="hint">
    The slug is the last part of your mosque's Mawaqit page URL:
    mawaqit.net/en/&lt;slug&gt;
  </p>
  <TextField label="Mawaqit slug" bind:value={slug} placeholder="your-mosque-slug" hasError={!!error} />
  {#if error}<Toast kind="error">{error}</Toast>{/if}
  <Button variant="primary" full disabled={submitting || !slug} onclick={submit}>
    {submitting ? 'Looking it up…' : 'Continue'}
  </Button>
</Card>
