<template>
  <section v-if="result" class="result card">
    <div class="result__top">
      <div>
        <div class="result__label">Результат расчёта</div>
        <h3>{{ result.variant_name }}</h3>
      </div>
    </div>

    <div class="result__grid">
      <div>
        <span>Ставка базовая</span>
        <strong>{{ percent(result.base_nominal_rate) }}</strong>
      </div>

      <div>
        <span>Итоговая ставка</span>
        <strong>{{ percent(result.final_nominal_rate) }}</strong>
      </div>

      <div>
        <span>Начисленные проценты</span>
        <strong>{{ currency(result.total_interest) }}</strong>
      </div>

      <div>
        <span>Сумма на вкладе к концу срока</span>
        <strong>{{ currency(result.final_amount) }}</strong>
      </div>

      <div>
        <span>Общая сумма с учётом процентов</span>
        <strong>{{ currency(totalWithInterest) }}</strong>
      </div>
    </div>

    <div class="result__meta">
      <span>Выплата: {{ payoutLabel }}</span>
      <span>Капитализация: {{ result.capitalization_enabled ? 'Да' : 'Нет' }}</span>
      <span v-if="result.capitalization_frequency">
        Частота капитализации: {{ capitalizationFrequencyLabel }}
      </span>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useFormatters } from '../composables/useFormatters'

const props = defineProps({
  result: {
    type: Object,
    default: null
  }
})

const { currency, percent } = useFormatters()

const totalWithInterest = computed(() => {
  const finalAmount = Number(props.result?.final_amount || 0)
  const totalInterest = Number(props.result?.total_interest || 0)
  const capitalizationEnabled = Boolean(props.result?.capitalization_enabled)

  return capitalizationEnabled ? finalAmount : finalAmount + totalInterest
})

const payoutLabel = computed(() => {
  const value = props.result?.payout_type

  const map = {
    end_of_term: 'в конце срока',
    end: 'в конце срока',
    monthly: 'ежемесячно',
    quarterly: 'ежеквартально',
    yearly: 'ежегодно',
    daily: 'ежедневно'
  }

  return map[value] || value || 'не указано'
})

const capitalizationFrequencyLabel = computed(() => {
  const value = props.result?.capitalization_frequency

  const map = {
    monthly: 'ежемесячно',
    quarterly: 'ежеквартально',
    yearly: 'ежегодно',
    daily: 'ежедневно'
  }

  return map[value] || value
})
</script>

<style scoped>
.result {
  padding: 28px;
}

.result__top {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 22px;
}

.result__label {
  color: var(--text-soft);
  margin-bottom: 8px;
}

.result h3 {
  margin: 0;
  font-size: 28px;
}

.result__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.result__grid span {
  display: block;
  color: var(--text-soft);
  margin-bottom: 6px;
}

.result__grid strong {
  font-size: 20px;
}

.result__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 18px;
  color: var(--text-soft);
}

@media (max-width: 640px) {
  .result__grid {
    grid-template-columns: 1fr;
  }
}
</style>