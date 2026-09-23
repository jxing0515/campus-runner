// 统一配置：真机/小程序调试时改成局域网地址，如 http://192.168.1.10:8000/api/v1
const H5_BASE = 'http://127.0.0.1:8000/api/v1'
const APP_BASE = 'http://127.0.0.1:8000/api/v1'

// #ifdef H5
export const BASE_URL = H5_BASE
// #endif
// #ifndef H5
export const BASE_URL = APP_BASE
// #endif

export const ORDER_STATUS = {
  pending_pay: '待支付',
  pending_accept: '待接单',
  accepted: '已接单',
  picked: '已取件',
  delivering: '配送中',
  pending_confirm: '待确认',
  completed: '已完成',
  cancelled: '已取消',
  refunded: '已退款',
  appealing: '申诉中',
  abnormal: '异常',
}

export const CREDIT_LEVEL = {
  excellent: '优秀',
  good: '良好',
  normal: '一般',
  limited: '受限',
}

export const CERT_STATUS = {
  none: '未认证',
  pending: '审核中',
  approved: '已认证',
  rejected: '已驳回',
}

export const APPEAL_TYPES = [
  { value: 'item_damaged', label: '物品损坏' },
  { value: 'item_lost', label: '物品丢失' },
  { value: 'not_delivered', label: '未送达' },
  { value: 'fee_dispute', label: '费用争议' },
  { value: 'other', label: '其他' },
]

export const WITHDRAW_METHODS = ['支付宝', '微信', '银行卡']
