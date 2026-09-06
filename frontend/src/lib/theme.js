// Theme persistence: a per-browser preference (localStorage), not a
// server-side config value -- this is how *you* like to look at the
// app, not something that belongs in config.yaml.

const STORAGE_KEY = 'prayer-sync-theme' // 'light' | 'dark'

function getStoredTheme() {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null // private browsing / storage disabled -- fall through to system preference
  }
}

function systemPrefersLight() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: light)').matches
}

export function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme)
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // ignore -- theme still applies for this page load, just won't persist
  }
}

/** Call once at startup, before mounting, to avoid a flash of the wrong theme. */
export function initTheme() {
  const theme = getStoredTheme() ?? (systemPrefersLight() ? 'light' : 'dark')
  document.documentElement.setAttribute('data-theme', theme)
  return theme
}

export function currentTheme() {
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'
}
