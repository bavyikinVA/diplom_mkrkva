<template>
  <article class="deposit card">
    <div class="deposit__top">
      <div class="deposit__bank-wrap">
        <div class="deposit__bank">{{ bankName }}</div>
        <h3>{{ depositName }}</h3>
        <p v-if="depositDescription" class="deposit__description">
          {{ depositDescription }}
        </p>
      </div>
    </div>

    <div class="deposit__features">
      <span class="deposit__feature" :class="{ 'is-active': allowTopup }">
        Пополнение: {{ allowTopup ? 'Да' : 'Нет' }}
      </span>

      <span class="deposit__feature" :class="{ 'is-active': allowPartialWithdraw }">
        Частичное снятие: {{ allowPartialWithdraw ? 'Да' : 'Нет' }}
      </span>

      <span class="deposit__feature" :class="{ 'is-active': autoProlongation }">
        Автопролонгация: {{ autoProlongation ? 'Да' : 'Нет' }}
      </span>

      <span class="deposit__feature" :class="{ 'is-active': hasCapitalization }">
        Капитализация: {{ hasCapitalization ? 'Есть' : 'Нет' }}
      </span>

      <span class="deposit__feature">
        Валюта: {{ currencyCode }}
      </span>
    </div>

    <div class="deposit__grid">
      <div class="deposit__metric">
        <span>Сумма</span>
        <strong>{{ amountRangeLabel }}</strong>
      </div>

      <div class="deposit__metric">
        <span>Срок</span>
        <strong>{{ termRangeLabel }}</strong>
      </div>

      <div class="deposit__metric">
        <span>Номинальная ставка</span>
        <strong>{{ nominalRateLabel }}</strong>
      </div>

      <div class="deposit__metric">
        <span>Способы открытия</span>
        <strong>{{ openMethodsLabel }}</strong>
      </div>

      <div class="deposit__metric">
        <span>Начисление процентов</span>
        <strong>{{ interestSchemesLabel }}</strong>
      </div>
    </div>

    <div class="deposit__footer">
      <div class="deposit__footer-info">
        <div class="deposit__hint">Выберите вклад и сразу перейдите к расчёту</div>
      </div>

      <div class="deposit__actions">
        <RouterLink
          class="btn btn-secondary"
          :to="calculatorLink"
          @click="selectVariant"
        >
          В калькулятор
        </RouterLink>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useDepositsStore } from '../stores/deposits'

const props = defineProps({
  item: {
    type: Object,
    required: true
  }
})

const store = useDepositsStore()
const itemModel = computed(() => props.item || {})

const depositId = computed(() => itemModel.value.id ?? '')
const depositName = computed(() => itemModel.value.name || 'Вклад')
const depositDescription = computed(() => itemModel.value.description || '')

const allowTopup = computed(() => Boolean(itemModel.value.allow_topup))
const allowPartialWithdraw = computed(() => Boolean(itemModel.value.allow_partial_withdraw))
const autoProlongation = computed(() => Boolean(itemModel.value.auto_prolongation))

const minAmount = computed(() => itemModel.value.min_amount ?? null)
const maxAmount = computed(() => itemModel.value.max_amount ?? null)
const minTermDays = computed(() => itemModel.value.min_term_days ?? null)
const maxTermDays = computed(() => itemModel.value.max_term_days ?? null)

const currencyCode = computed(() => itemModel.value.product?.currency || 'RUB')

const bankName = computed(() => {
  return (
    itemModel.value.bank?.name ||
    itemModel.value.product?.bank?.name ||
    itemModel.value.product?.bank_name ||
    'Банк'
  )
})

const hasCapitalization = computed(() => {
  const schemes = itemModel.value.interest_schemes || []
  return schemes.some((scheme) => scheme?.capitalization_enabled === true)
})

function formatIntegerAmount(value) {
  if (value == null || value === '') return null

  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return null

  return new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(numericValue)
}

function currencySymbol(code) {
  const map = {
    RUB: '₽',
    USD: '$',
    EUR: '€',
    CNY: '¥',
    JPY: '¥'
  }

  return map[code] || code
}

function formatMoneyWhole(value, code) {
  const formatted = formatIntegerAmount(value)
  if (!formatted) return '—'
  return `${formatted} ${currencySymbol(code)}`
}

function daysToWholeMonths(days) {
  if (days == null) return null
  const numericDays = Number(days)
  if (!Number.isFinite(numericDays)) return null
  return Math.max(1, Math.round(numericDays / 30.4375))
}

function pluralizeMonths(months) {
  const value = Math.abs(Number(months))
  const mod10 = value % 10
  const mod100 = value % 100

  if (mod10 === 1 && mod100 !== 11) return 'мес.'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'мес.'
  return 'мес.'
}

function formatMonthsLabel(days) {
  const months = daysToWholeMonths(days)
  if (months == null) return null
  return `${months} ${pluralizeMonths(months)}`
}

function formatPercentValue(value) {
  if (value == null || value === '') return null

  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return null

  return `${new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1
  }).format(numericValue)}%`
}

const amountRangeLabel = computed(() => {
  const min = minAmount.value
  const max = maxAmount.value

  if (min != null && max != null) {
    return `от ${formatMoneyWhole(min, currencyCode.value)} до ${formatMoneyWhole(max, currencyCode.value)}`
  }

  if (min != null) {
    return `от ${formatMoneyWhole(min, currencyCode.value)}`
  }

  if (max != null) {
    return `до ${formatMoneyWhole(max, currencyCode.value)}`
  }

  return 'Не указано'
})

const termRangeLabel = computed(() => {
  const min = minTermDays.value
  const max = maxTermDays.value

  if (min != null && max != null && Number(min) === Number(max)) {
    return formatMonthsLabel(min) || 'Не указано'
  }

  if (min != null && max != null) {
    return `от ${formatMonthsLabel(min)} до ${formatMonthsLabel(max)}`
  }

  if (min != null) {
    return `от ${formatMonthsLabel(min)}`
  }

  if (max != null) {
    return `до ${formatMonthsLabel(max)}`
  }

  return 'Не указано'
})

const displayRate = computed(() => {
  return (
    itemModel.value.matched_final_nominal_rate ??
    itemModel.value.matched_rate?.nominal_rate ??
    itemModel.value.nominal_rate ??
    itemModel.value.base_rate?.nominal_rate ??
    null
  )
})

const rateFrom = computed(() => {
  return itemModel.value.min_nominal_rate ?? itemModel.value.rate_from ?? null
})

const rateTo = computed(() => {
  return itemModel.value.max_nominal_rate ?? itemModel.value.rate_to ?? null
})

const nominalRateLabel = computed(() => {
  if (displayRate.value != null) {
    return `${formatPercentValue(displayRate.value)} годовых`
  }

  if (rateFrom.value != null && rateTo.value != null) {
    if (Number(rateFrom.value) === Number(rateTo.value)) {
      return `${formatPercentValue(rateFrom.value)} годовых`
    }

    return `от ${formatPercentValue(rateFrom.value)} до ${formatPercentValue(rateTo.value)} годовых`
  }

  if (rateFrom.value != null) {
    return `от ${formatPercentValue(rateFrom.value)} годовых`
  }

  if (rateTo.value != null) {
    return `до ${formatPercentValue(rateTo.value)} годовых`
  }

  return '—'
})

const openMethodsLabel = computed(() => {
  const methods = itemModel.value.open_methods || []
  if (!methods.length) return 'Не указано'
  return methods.map((method) => method.name).filter(Boolean).join(', ')
})

const interestSchemesLabel = computed(() => {
  const schemes = itemModel.value.interest_schemes || []
  if (!schemes.length) return 'Не указано'

  const hasPayout = schemes.some((scheme) => scheme?.capitalization_enabled === false)
  const hasCap = schemes.some((scheme) => scheme?.capitalization_enabled === true)

  if (hasPayout && hasCap) {
    return 'Выплата процентов / капитализация'
  }

  return schemes.map((scheme) => scheme.name).filter(Boolean).join(', ')
})

const calculatorLink = computed(() => `/calculator?variant=${depositId.value}`)

function selectVariant() {
  store.setSelectedVariant(props.item)
}
</script>



<style scoped>
.deposit {
  padding: 24px;
  border-radius: 24px;
  background: linear-gradient(180deg, #ffffff 0%, #fcfeff 100%);
}

.deposit__top {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.deposit__bank {
  color: var(--primary-deep);
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 8px;
}

.deposit h3 {
  margin: 0 0 8px;
  font-size: 24px;
  line-height: 1.2;
}

.deposit__description {
  margin: 0;
  color: var(--text-soft);
  line-height: 1.5;
}

.deposit__features {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 18px;
}

.deposit__feature {
  padding: 8px 12px;
  border-radius: 999px;
  background: #f5fbff;
  border: 1px solid var(--border);
  color: var(--text-soft);
  font-size: 13px;
  font-weight: 600;
}

.deposit__feature.is-active {
  color: #1a6d91;
  background: #eef8fd;
}

.deposit__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.deposit__metric {
  padding: 16px;
  border-radius: 18px;
  background: #fbfeff;
  border: 1px solid #e6f3fa;
}

.deposit__metric span {
  display: block;
  color: var(--text-soft);
  margin-bottom: 6px;
  font-size: 14px;
}

.deposit__metric strong {
  font-size: 16px;
  line-height: 1.4;
}

.deposit__footer {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.deposit__hint {
  color: var(--text-soft);
  font-size: 14px;
}

.deposit__actions {
  display: flex;
  gap: 10px;
}

@media (max-width: 760px) {
  .deposit__top,
  .deposit__footer {
    flex-direction: column;
    align-items: stretch;
  }

  .deposit__grid {
    grid-template-columns: 1fr;
  }
}
</style>