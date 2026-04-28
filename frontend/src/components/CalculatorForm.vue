<template>
  <form class="calculator card" @submit.prevent="submit">
    <h2>Калькулятор вклада</h2>

    <div v-if="variant" class="calculator__selected">
      <div class="calculator__selected-title">Выбран вклад</div>
      <div class="calculator__selected-name">
        {{ bankName }} — {{ variantName }}
      </div>
      <div class="calculator__selected-meta">
        {{ selectedMetaLabel }}
      </div>
    </div>

    <div v-else-if="loading" class="calculator__placeholder">
      Загрузка параметров вклада...
    </div>

    <div v-else class="calculator__placeholder">
      Перейдите в калькулятор из карточки вклада.
    </div>

    <div class="calculator__grid">
      <UiInput
        v-model="form.amount"
        label="Сумма"
        type="number"
      />

      <UiSelect
        v-model="termValue"
        label="Срок вклада"
        :options="termOptions"
      />

      <UiInput
        v-model="form.promo_code"
        label="Промокод"
      />

      <UiSelect
        v-model="form.open_method_code"
        label="Способ открытия"
        :options="openMethodOptions"
      />

      <UiSelect
        v-model="form.interest_scheme_code"
        label="Начисление процентов"
        :options="interestSchemeOptions"
      />
    </div>

    <div class="calculator__checks">
      <UiCheckbox v-model="form.has_subscription" label="Есть подписка" />
      <UiCheckbox v-model="form.is_salary_client" label="Зарплатный клиент" />
      <UiCheckbox v-model="form.is_pension_client" label="Пенсионный клиент" />
      <UiCheckbox v-model="form.has_premium_package" label="Премиум-пакет" />
    </div>

    <button
      class="btn btn-primary"
      type="submit"
      :disabled="!variant || !isReadyToSubmit"
    >
      Рассчитать доходность
    </button>
  </form>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import UiCheckbox from './UiCheckbox.vue'
import UiInput from './UiInput.vue'
import UiSelect from './UiSelect.vue'

const props = defineProps({
  variant: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['submit'])

const form = reactive({
  amount: '',
  term_days: '',
  open_method_code: '',
  interest_scheme_code: '',
  has_subscription: false,
  is_salary_client: false,
  is_pension_client: false,
  has_premium_package: false,
  promo_code: ''
})

const variantName = computed(() => props.variant?.name || 'Вклад')

const bankName = computed(() => {
  return (
    props.variant?.bank?.name ||
    props.variant?.product?.bank?.name ||
    props.variant?.product?.bank_name ||
    'Банк'
  )
})

const currencyCode = computed(() => props.variant?.product?.currency || 'RUB')
const minAmount = computed(() => props.variant?.min_amount ?? null)
const maxAmount = computed(() => props.variant?.max_amount ?? null)
const minTermDays = computed(() => Number(props.variant?.min_term_days || 0))
const maxTermDays = computed(() => Number(props.variant?.max_term_days || 0))

const amountLabel = computed(() => {
  if (minAmount.value == null) return '—'
  return formatMoneyWithCurrency(minAmount.value, currencyCode.value)
})

const maxAmountLabel = computed(() => {
  if (maxAmount.value == null) return ''
  return formatMoneyWithCurrency(maxAmount.value, currencyCode.value)
})

const minTermLabel = computed(() => {
  return minTermDays.value ? `${minTermDays.value} дн.` : '—'
})

const maxTermLabel = computed(() => {
  return maxTermDays.value ? `${maxTermDays.value} дн.` : '—'
})

const selectedMetaLabel = computed(() => {
  const amountText = maxAmount.value != null
    ? `Сумма от ${amountLabel.value} до ${maxAmountLabel.value}`
    : `Сумма от ${amountLabel.value}`

  const termText = maxTermDays.value
    ? `срок от ${minTermLabel.value} до ${maxTermLabel.value}`
    : `срок от ${minTermLabel.value}`

  return `${amountText} · ${termText}`
})

function formatMoneyWithCurrency(value, currencyCode) {
  const amount = Number(value)

  if (Number.isNaN(amount)) {
    return `0 ${currencyCode}`
  }

  return `${new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 2,
    minimumFractionDigits: amount % 1 === 0 ? 0 : 2
  }).format(amount)} ${currencyCode}`
}

function monthsLabel(months) {
  if (months === 1) return '1 месяц'
  if (months >= 2 && months <= 4) return `${months} месяца`
  return `${months} месяцев`
}

function payoutShortLabel(code) {
  const map = {
    end_of_term: 'В конце срока',
    end: 'В конце срока',
    monthly: 'Ежемесячно',
    quarterly: 'Ежеквартально',
    yearly: 'Ежегодно',
    daily: 'Ежедневно'
  }
  return map[code] || code || 'Не указано'
}

function schemeLabel(scheme) {
  if (!scheme) return 'Не указано'

  if (scheme.name) {
    return scheme.name
  }

  const payout = payoutShortLabel(scheme.payout_type)
  return scheme.capitalization_enabled ? `${payout} с капитализацией` : payout
}

function openMethodLabel(method) {
  if (!method) return 'Не указано'
  if (method.name) return method.name

  const map = {
    online: 'Онлайн',
    office: 'В отделении банка',
    branch: 'В отделении банка',
    mobile_app: 'В мобильном приложении',
    internet_bank: 'В интернет-банке',
    gosuslugi: 'Через Госуслуги'
  }

  return map[method.code] || method.code || 'Не указано'
}

function dedupeByValue(items) {
  const map = new Map()

  items.forEach((item) => {
    if (!item?.value) return
    if (!map.has(item.value)) {
      map.set(item.value, item)
    }
  })

  return [...map.values()]
}

function representativeDaysForMonths(months, minDays, maxDays) {
  const special = {
    4: 120,
    5: 150,
    6: 181,
    7: 212,
    8: 243,
    9: 273,
    10: 304,
    11: 334,
    12: 367,
    18: 548,
    24: 730,
    36: 1095
  }

  let value = special[months] || Math.round(months * 30.4)

  if (value < minDays) value = minDays
  if (maxDays && value > maxDays) value = maxDays

  return value
}

function buildMonthCandidates(minDays, maxDays) {
  const candidates = []
  const minMonths = Math.max(1, Math.ceil(minDays / 30))
  const maxMonths = Math.max(minMonths, Math.floor(maxDays / 30))

  for (let month = minMonths; month <= Math.min(maxMonths, 12); month += 1) {
    candidates.push(month)
  }

  if (maxMonths >= 18) candidates.push(18)
  if (maxMonths >= 24) candidates.push(24)
  if (maxMonths >= 36) candidates.push(36)

  return [...new Set(candidates)].sort((a, b) => a - b)
}

function buildTermOptions(baseRates, variant) {
  if (!variant) return []

  const minDays = Number(variant.min_term_days || 0)
  const maxDays = Number(variant.max_term_days || minDays || 0)

  const usableRates = (baseRates || []).length
    ? baseRates
    : [{ term_from_days: minDays, term_to_days: maxDays }]

  const monthCandidates = buildMonthCandidates(minDays, maxDays)

  const options = monthCandidates
    .map((months) => {
      const dayValue = representativeDaysForMonths(months, minDays, maxDays)

      const allowed = usableRates.some((rate) => {
        const from = Number(rate.term_from_days || 0)
        const to = Number(rate.term_to_days || 0)
        return dayValue >= from && dayValue <= to
      })

      if (!allowed) return null

      let label

      if (months === 12) {
        label = '1 год'
      } else if (months === 18) {
        label = '1,5 года'
      } else if (months === 24) {
        label = '2 года'
      } else if (months === 36) {
        label = '3 года'
      } else {
        label = monthsLabel(months)
      }

      return {
        value: String(dayValue),
        label
      }
    })
    .filter(Boolean)

  const fallbackMin = {
    value: String(minDays),
    label: `${minDays} дн.`
  }

  return dedupeByValue(options.length ? options : [fallbackMin])
}

const filteredRatesByMethodAndScheme = computed(() => {
  const rates = props.variant?.base_rates || []

  return rates.filter((rate) => {
    const methodCode = rate.open_method?.code || ''
    const schemeCode = rate.interest_scheme?.code || ''

    const methodOk = !form.open_method_code || methodCode === form.open_method_code
    const schemeOk = !form.interest_scheme_code || schemeCode === form.interest_scheme_code

    return methodOk && schemeOk
  })
})

const openMethodOptions = computed(() => {
  const methodsFromRates = (props.variant?.base_rates || [])
    .map((rate) => rate.open_method)
    .filter(Boolean)
    .map((method) => ({
      value: method.code,
      label: openMethodLabel(method)
    }))

  const methodsFromVariant = (props.variant?.open_methods || [])
    .filter(Boolean)
    .map((method) => ({
      value: method.code,
      label: openMethodLabel(method)
    }))

  const options = dedupeByValue([...methodsFromVariant, ...methodsFromRates])

  return options.length ? options : [{ value: '', label: 'Не указано' }]
})

const interestSchemeOptions = computed(() => {
  const schemesFromRates = (props.variant?.base_rates || [])
    .map((rate) => rate.interest_scheme)
    .filter(Boolean)
    .map((scheme) => ({
      value: scheme.code,
      label: schemeLabel(scheme)
    }))

  const schemesFromVariant = (props.variant?.interest_schemes || [])
    .filter(Boolean)
    .map((scheme) => ({
      value: scheme.code,
      label: schemeLabel(scheme)
    }))

  const options = dedupeByValue([...schemesFromVariant, ...schemesFromRates])

  return options.length ? options : [{ value: '', label: 'Не указано' }]
})
computed(() => {
  const schemes = props.variant?.interest_schemes || []
  return schemes.find((scheme) => scheme.code === form.interest_scheme_code) || null
});
const termOptions = computed(() => {
  return buildTermOptions(filteredRatesByMethodAndScheme.value, props.variant)
})

const termValue = computed({
  get: () => String(form.term_days || ''),
  set: (value) => {
    form.term_days = value ? Number(value) : ''
  }
})

watch(
  () => props.variant,
  (variant) => {
    if (!variant) return

    form.amount = Number(variant.min_amount || 0)
    form.open_method_code = openMethodOptions.value[0]?.value || ''

    const preferredScheme = (variant.interest_schemes || []).find(
      (scheme) => scheme?.capitalization_enabled === true
    )

    form.interest_scheme_code = preferredScheme?.code || interestSchemeOptions.value[0]?.value || ''
    form.term_days = termOptions.value[0]?.value
      ? Number(termOptions.value[0].value)
      : Number(variant.min_term_days || 0)
  },
  { immediate: true }
)

watch(
  () => [form.open_method_code, form.interest_scheme_code],
  () => {
    const availableTerms = termOptions.value
    if (!availableTerms.length) return

    const current = String(form.term_days || '')
    const exists = availableTerms.some((item) => item.value === current)

    if (!exists) {
      form.term_days = Number(availableTerms[0].value)
    }
  }
)

const isReadyToSubmit = computed(() => {
  return Boolean(
    props.variant &&
    form.amount &&
    form.term_days
  )
})

function submit() {
  if (!props.variant) return

  emit('submit', {
    variant_id: Number(props.variant.id),
    amount: Number(form.amount),
    term_days: Number(form.term_days),
    open_method_code: form.open_method_code || null,
    interest_scheme_code: form.interest_scheme_code || null,
    has_subscription: form.has_subscription,
    is_salary_client: form.is_salary_client,
    is_pension_client: form.is_pension_client,
    monthly_spend: null,
    savings_balance: null,
    has_premium_package: form.has_premium_package,
    promo_code: form.promo_code || null,
    extra_context: {}
  })
}
</script>

<style scoped>
.calculator {
  padding: 28px;
}

.calculator h2 {
  margin: 0 0 18px;
}

.calculator__selected {
  margin-bottom: 18px;
  padding: 18px 20px;
  border-radius: 20px;
  background: #f5fbff;
  border: 1px solid var(--border);
}

.calculator__selected-title {
  color: var(--text-soft);
  font-size: 13px;
  margin-bottom: 6px;
}

.calculator__selected-name {
  font-weight: 800;
  font-size: 18px;
  margin-bottom: 6px;
}

.calculator__placeholder {
  margin-bottom: 18px;
  padding: 16px 18px;
  border-radius: 18px;
  background: #fbfeff;
  border: 1px solid var(--border);
  color: var(--text-soft);
}

.calculator__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.calculator__checks {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

@media (max-width: 900px) {
  .calculator__grid,
  .calculator__checks {
    grid-template-columns: 1fr;
  }
}
</style>
