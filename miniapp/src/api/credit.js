import { get } from '../utils/request'

export const myCredit = () => get('/credit/me')
export const creditLogs = (params) => get('/credit/logs', params)

export default { myCredit, creditLogs }
