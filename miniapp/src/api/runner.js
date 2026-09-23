import { get, post } from '../utils/request'

export const certification = () => get('/runner/certification')
export const submitCertification = (data) => post('/runner/certification', data)
export const income = () => get('/runner/income')
export const withdrawals = (params) => get('/runner/withdrawals', params)
export const applyWithdrawal = (data) => post('/runner/withdrawals', data)

export default { certification, submitCertification, income, withdrawals, applyWithdrawal }
