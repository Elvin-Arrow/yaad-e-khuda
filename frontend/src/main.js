import { mount } from 'svelte'
import './lib/theme.css'
import { initTheme } from './lib/theme.js'
import App from './App.svelte'

initTheme() // set data-theme before first paint, avoids a flash of the wrong theme

const app = mount(App, {
  target: document.getElementById('app'),
})

export default app
