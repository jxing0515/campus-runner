export const fmtDate = (v) => (v ? String(v).replace('T', ' ').slice(0, 19) : '-')
export const fmtMoney = (v) => (v === null || v === undefined || v === '' ? '-' : `¥${v}`)
