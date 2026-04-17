<template>
  <button
    v-if="visible"
    class="back-to-top"
    type="button"
    @click="scrollToTop"
  >
    ↑ Наверх
  </button>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const visible = ref(false)

function handleScroll() {
  visible.value = window.scrollY > 500
}

function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  })
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
  handleScroll()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.back-to-top {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 50;
  border: none;
  border-radius: 999px;
  padding: 14px 18px;
  background: linear-gradient(135deg, #99d0ee 0%, #4da8d8 100%);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(77, 168, 216, 0.28);
  transition: 0.2s ease;
}

.back-to-top:hover {
  transform: translateY(-2px);
}

@media (max-width: 768px) {
  .back-to-top {
    right: 16px;
    bottom: 16px;
    padding: 12px 16px;
  }
}
</style>