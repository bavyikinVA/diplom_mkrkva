import { defineStore } from 'pinia'
import {
    fetchDeposits,
    calculateDeposit,
    fetchDepositsStats,
    fetchDepositVariantById
} from '../api/deposits'

export const useDepositsStore = defineStore('deposits', {
    state: () => ({
        items: [],
        total: 0,
        page: 1,
        pageSize: 12,
        loading: false,
        error: '',

        calculatorLoading: false,
        calculatorError: '',
        calculationResult: null,

        selectedVariant: null,
        selectedVariantLoading: false,
        selectedVariantError: '',

        statsLoading: false,
        statsError: '',
        stats: {
            totalOffers: 0,
            totalBanks: 0,
            topupOffers: 0,
            capitalizationOffers: 0
        },

        filters: {
            amount: 50000,
            term_days: 367,
            currency: 'RUB',
            capitalization_enabled: null,
            allow_topup: null,
            allow_partial_withdraw: null,
            auto_prolongation: null,
            page: 1,
            page_size: 12
        }
    }),

    actions: {
        cleanParams(params) {
            const result = { ...params }

            Object.keys(result).forEach((key) => {
                if (result[key] === null || result[key] === '' || result[key] === undefined) {
                    delete result[key]
                }
            })

            return result
        },

        async loadDeposits(override = {}) {
            this.loading = true
            this.error = ''

            try {
                const params = this.cleanParams({
                    ...this.filters,
                    ...override
                })

                const data = await fetchDeposits(params)

                this.items = data.items || []
                this.total = data.total || 0
                this.page = data.page || 1
                this.pageSize = data.page_size || 12

                this.filters = {
                    ...this.filters,
                    ...override,
                    page: this.page,
                    page_size: this.pageSize
                }
            } catch (error) {
                this.error = error?.response?.data?.detail || 'Не удалось загрузить предложения'
            } finally {
                this.loading = false
            }
        },

        async loadStats() {
            this.statsLoading = true
            this.statsError = ''

            try {
                const data = await fetchDepositsStats()

                this.stats = {
                    totalOffers: Number(data.total_offers || 0),
                    totalBanks: Number(data.total_banks || 0),
                    topupOffers: Number(data.topup_offers || 0),
                    capitalizationOffers: Number(data.capitalization_offers || 0)
                }
            } catch (error) {
                this.statsError = error?.response?.data?.detail || 'Не удалось загрузить статистику'
            } finally {
                this.statsLoading = false
            }
        },

        setSelectedVariant(variant) {
            this.selectedVariant = variant
        },

        async loadVariantById(variantId) {
            if (!variantId) return

            if (this.selectedVariant && Number(this.selectedVariant.id) === Number(variantId)) {
                return
            }

            this.selectedVariantLoading = true
            this.selectedVariantError = ''

            try {
                const data = await fetchDepositVariantById(variantId)
                this.selectedVariant = data
            } catch (error) {
                this.selectedVariantError = error?.response?.data?.detail || 'Не удалось загрузить вклад'
            } finally {
                this.selectedVariantLoading = false
            }
        },

        async goToPage(page) {
            await this.loadDeposits({ page })
        },

        async runCalculation(payload) {
            this.calculatorLoading = true
            this.calculatorError = ''
            this.calculationResult = null

            try {
                this.calculationResult = await calculateDeposit(payload)
            } catch (error) {
                this.calculatorError = error?.response?.data?.detail || 'Не удалось выполнить расчёт'
            } finally {
                this.calculatorLoading = false
            }
        }
    }
})