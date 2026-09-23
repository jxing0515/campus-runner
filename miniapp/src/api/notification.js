import { get, post } from '../utils/request'

export const notifications = (params) => get('/notifications', params)
export const readOne = (id) => post(`/notifications/${id}/read`)
export const readAll = () => post('/notifications/read-all')

export default { notifications, readOne, readAll }
