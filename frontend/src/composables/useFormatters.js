export function useFormatters() {
    const currency = (value, code = 'RUB') => {
        if (value === null || value === undefined || value === '') return '—'

        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: code,
            maximumFractionDigits: 2
        }).format(Number(value))
    }

    const percent = (value) => {
        if (value === null || value === undefined || value === '') return '—'
        return `${Number(value).toFixed(2)}%`
    }

    const daysToMonthsLabel = (days) => {
        if (!days) return '—'
        const months = Math.round(Number(days) / 30)
        return `${days} дн. (~${months} мес.)`
    }

    return { currency, percent, daysToMonthsLabel }
}
export function payoutTypeLabel(code) {
    const map = {
    end_of_term: 'В конце срока',
    monthly: 'Ежемесячно',
    quarterly: 'Ежеквартально',
    yearly: 'Ежегодно'
    }
    return map[code] || code
}