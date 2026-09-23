import { get, post } from '../utils/request'

/** 发单 */
export const createOrder = (data) => post('/orders', data)
/** 我的订单：role = student | runner */
export const myOrders = (params) => get('/orders', params)
/** 详情：状态日志、凭证、评价、资金流水 */
export const orderDetail = (orderNo) => get(`/orders/${orderNo}`)
/** 模拟支付（Idempotency-Key 生效） */
export const payOrder = (orderNo, idempotencyKey) =>
  post(`/orders/${orderNo}/pay`, {}, { header: { 'Idempotency-Key': idempotencyKey } })
export const cancelOrder = (orderNo, reason) => post(`/orders/${orderNo}/cancel`, { reason })
export const confirmOrder = (orderNo) => post(`/orders/${orderNo}/confirm`)
/** 双向评价：{score:1-5, content} */
export const reviewOrder = (orderNo, data) => post(`/orders/${orderNo}/review`, data)
/** 申诉：{appeal_type, description, card_file_ids} */
export const appealOrder = (orderNo, data) => post(`/orders/${orderNo}/appeal`, data)

/** 跑腿员待接单大厅：sort = time | fee */
export const availableOrders = (params) => get('/orders/available', params)
export const acceptOrder = (orderNo) => post(`/orders/${orderNo}/accept`)
export const pickupOrder = (orderNo, fileIds) => post(`/orders/${orderNo}/pickup`, { file_ids: fileIds })
export const deliverOrder = (orderNo, data) => post(`/orders/${orderNo}/deliver`, data)

export default {
  createOrder,
  myOrders,
  orderDetail,
  payOrder,
  cancelOrder,
  confirmOrder,
  reviewOrder,
  appealOrder,
  availableOrders,
  acceptOrder,
  pickupOrder,
  deliverOrder,
}
