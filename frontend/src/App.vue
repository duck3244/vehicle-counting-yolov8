<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app">
    <header class="nav">
      <RouterLink to="/" class="brand">🚗 Vehicle Counting</RouterLink>
      <nav>
        <RouterLink to="/">Home</RouterLink>
      </nav>
    </header>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<style>
:root {
  color-scheme: light;
  font-family: system-ui, -apple-system, sans-serif;
}
html, body, #app { margin: 0; padding: 0; min-height: 100%; background: #fafafa; color: #222; }
.app { display: flex; flex-direction: column; min-height: 100vh; }
.nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1.5rem; background: #fff; border-bottom: 1px solid #eee;
}
.nav .brand { font-weight: 600; font-size: 1.1rem; text-decoration: none; color: #222; }
.nav nav a {
  margin-left: 1rem; text-decoration: none; color: #555;
}
.nav nav a.router-link-active { color: #0066cc; font-weight: 500; }
.main { flex: 1; max-width: 960px; margin: 0 auto; padding: 2rem 1rem; width: 100%; box-sizing: border-box; }
.panel {
  background: #fff; border: 1px solid #e5e5e5; border-radius: 8px;
  padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;
}
.panel h2 { margin-top: 0; font-size: 1.05rem; }
label { display: block; font-size: 0.9rem; color: #555; margin-bottom: 0.25rem; }
input[type="number"], input[type="text"], input[type="file"] {
  width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;
  font-size: 0.95rem;
}
button {
  padding: 0.5rem 1rem; border: none; background: #0066cc; color: #fff; border-radius: 4px;
  cursor: pointer; font-size: 0.95rem;
}
button:disabled { background: #999; cursor: not-allowed; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.err { color: #c00; }
.muted { color: #888; font-size: 0.85rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #eee; }
th { color: #666; font-weight: 500; }
.badge {
  display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px;
  font-size: 0.75rem; font-weight: 500;
}
.badge-queued { background: #eee; color: #555; }
.badge-running { background: #fff3cd; color: #856404; }
.badge-done { background: #d4edda; color: #155724; }
.badge-error { background: #f8d7da; color: #721c24; }
progress { width: 100%; height: 12px; }
</style>
