<template>
  <div>
    <HeroSection />
    <HowItWorksSection />
    <HomeStatsSection :stats="store.stats" />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useDepositsStore } from '../stores/deposits'
import HeroSection from '../components/HeroSection.vue'
import HomeStatsSection from '../components/HomeStatsSection.vue'
import HowItWorksSection from '../components/HowItWorksSection.vue'

const store = useDepositsStore()

onMounted(async () => {
  console.log('HomePage mounted')
  await store.loadStats()
  console.log('Stats loaded:', store.stats)
})
</script>