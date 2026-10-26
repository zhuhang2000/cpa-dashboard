<template>
  <svg class="role-icon" width="18" height="18" viewBox="0 0 24 24" role="img" :aria-label="label">
    <title>{{ label }}</title>
    <defs>
      <linearGradient :id="uid" x1="0" y1="0" x2="1" y2="1">
        <stop :stop-color="metal.light" />
        <stop offset="0.55" :stop-color="metal.mid" />
        <stop offset="1" :stop-color="metal.deep" />
      </linearGradient>
    </defs>
    <path
      :fill="`url(#${uid})`"
      :stroke="metal.edge"
      stroke-linejoin="round"
      d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"
    />
    <path
      fill="none"
      stroke="#fff"
      stroke-width="2.4"
      stroke-linecap="round"
      stroke-linejoin="round"
      d="m9 12 2 2 4-4"
    />
  </svg>
</template>

<script setup>
import { computed, useId } from 'vue'
import { ROLES, Role } from '@/constants'

// `role` is a staff role; regular users carry no icon.
const props = defineProps({ role: { type: String, required: true } })

// Lucide's badge-check (ISC licence), filled with metal instead of outlined: gold for the system
// administrator, silver for tag managers. The fill shades from `light` to `deep` inside an `edge`.
const METALS = {
  [Role.ADMIN]: { light: '#fde68a', mid: '#f5a524', deep: '#b45309', edge: '#a1560a' },
  [Role.MANAGER]: { light: '#e6e9ee', mid: '#aab2bd', deep: '#5d6673', edge: '#717a87' },
}

// A list shows many of these icons, so each one needs its own gradient id.
const uid = useId()
const metal = computed(() => METALS[props.role])
const label = computed(() => ROLES[props.role].label)
</script>

<style scoped>
.role-icon {
  flex: none;
}
</style>
