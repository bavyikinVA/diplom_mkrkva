<template>
  <section class="hero container">
    <div class="hero__content card">
      <div class="hero__text">
        <h1>Подберите вклад по сумме, сроку и условиям</h1>
        <p>
          Удобный каталог банковских вкладов с фильтрами и калькулятором доходности.
        </p>
        <div class="hero__actions">
          <RouterLink :to="{ name: 'catalog' }" class="btn btn-primary">
            Смотреть предложения
          </RouterLink>

          <RouterLink :to="{ name: 'calculator' }" class="btn btn-secondary">
            Открыть калькулятор
          </RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>

<style scoped>
.hero {
  padding: 28px 0 10px;
}

.hero__content {
  display: grid;
  grid-template-columns: 1.3fr 0.9fr;
  gap: 24px;
  padding: 34px;
}

.hero h1 {
  margin: 0 0 14px;
  font-size: 44px;
  line-height: 1.1;
}

.hero p {
  margin: 0;
  font-size: 18px;
  color: var(--text-soft);
  line-height: 1.6;
  max-width: 640px;
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 24px;
}

@media (max-width: 900px) {
  .hero__content {
    grid-template-columns: 1fr;
  }

  .hero h1 {
    font-size: 34px;
  }
}
</style>