export const ORDER_STATUS = {
  pending_pay: ['待支付', 'info'],
  pending_accept: ['待接单', 'warning'],
  accepted: ['已接单', 'primary'],
  picked: ['已取件', 'primary'],
  delivering: ['配送中', 'primary'],
  pending_confirm: ['待确认', 'warning'],
  completed: ['已完成', 'success'],
  cancelled: ['已取消', 'info'],
  refunded: ['已退款', 'danger'],
  appealing: ['申诉中', 'danger'],
  abnormal: ['异常', 'danger'],
}
export const CERT_STATUS = {
  none: ['未认证', 'info'],
  pending: ['待审核', 'warning'],
  approved: ['已通过', 'success'],
  rejected: ['已驳回', 'danger'],
}
export const CREDIT_LEVEL = {
  excellent: ['优秀', 'success'],
  good: ['良好', 'primary'],
  normal: ['一般', 'info'],
  limited: ['受限', 'danger'],
}
export const WITHDRAW_STATUS = {
  pending: ['待审核', 'warning'],
  approved: ['已通过', 'success'],
  rejected: ['已驳回', 'danger'],
  paid: ['已打款', 'success'],
}
export const REFUND_STATUS = {
  pending: ['待处理', 'warning'],
  refunded: ['已退款', 'success'],
  rejected: ['已驳回', 'danger'],
}
export const FUND_FLOW_TYPE = {
  recharge: '充值',
  pay: '支付',
  payment: '支付',
  refund: '退款',
  settle: '结算',
  settlement: '结算',
  withdraw: '提现',
  freeze: '冻结',
  unfreeze: '解冻',
  arbitrate: '仲裁分配',
}
export const FEE_PART = {
  runner_fee: '跑腿费',
  item_fee: '物品费',
  platform_fee: '平台服务费',
  deposit: '押金',
}
export const APPEAL_WINNER = [
  { value: 'student', label: '学生胜诉（全额退学生）' },
  { value: 'runner', label: '跑腿员胜诉（全额给跑腿员）' },
  { value: 'partial', label: '部分胜诉（按比例分配）' },
]
export const tag = (map, v) => (map[v] && map[v][1]) || 'info'
export const label = (map, v) => {
  const it = map[v]
  return Array.isArray(it) ? it[0] : it || v || '-'
}
export const opt = (map) => Object.entries(map).map(([value, it]) => ({ value, label: Array.isArray(it) ? it[0] : it }))
