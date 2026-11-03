// Role, status and ledger type values the API returns, and how the UI labels them.
// The value objects mirror the backend's constants.py: when a value is added there, add it
// here as well, together with its entry in the matching label map below.

// A MANAGER only sees and credits the regular users that share its tag.
export const Role = { USER: 'user', ADMIN: 'admin', MANAGER: 'manager' }

export const UserStatus = { ACTIVE: 'active', BANNED: 'banned' }

// Deleted keys are never listed, so KeyStatus.DELETED is left out.
export const KeyStatus = { ACTIVE: 'active', DISABLED: 'disabled' }

// Extra values the API reports in a key's `state` when an active key cannot serve requests.
export const KeyState = { EXPIRED: 'expired', EXHAUSTED: 'exhausted', SUSPENDED: 'suspended' }

export const RedeemStatus = { UNUSED: 'unused', USED: 'used', DISABLED: 'disabled' }

export const RedeemType = { RECHARGE: 'recharge', GIFT: 'gift' }

// Not stored: the UI shows an unused code past its expiry date as expired.
export const RedeemState = { EXPIRED: 'expired' }

export const OrderStatus = { PENDING: 'pending', PAID: 'paid' }

export const TxType = { REDEEM: 'redeem', REDEEM_GIFT: 'redeem_gift', ONLINE: 'online', ADMIN: 'admin', BONUS: 'bonus' }

// Label and badge tone (badge-<tone>, '' for neutral) of each value, shown by <StatusBadge>.
export const ROLES = {
  [Role.USER]: { label: '普通用户', tone: '' },
  [Role.MANAGER]: { label: '管理员', tone: 'info' },
  [Role.ADMIN]: { label: '超级管理员', tone: 'accent' },
}

export const USER_STATUSES = {
  [UserStatus.ACTIVE]: { label: '正常', tone: 'success' },
  [UserStatus.BANNED]: { label: '已禁用', tone: 'danger' },
}

export const KEY_STATES = {
  [KeyStatus.ACTIVE]: { label: '正常', tone: 'success' },
  [KeyStatus.DISABLED]: { label: '已禁用', tone: '' },
  [KeyState.EXPIRED]: { label: '已过期', tone: 'warning' },
  [KeyState.EXHAUSTED]: { label: '额度用尽', tone: 'warning' },
  [KeyState.SUSPENDED]: { label: '余额不足', tone: 'danger' },
}

export const REDEEM_STATES = {
  [RedeemStatus.UNUSED]: { label: '未使用', tone: 'success' },
  [RedeemStatus.USED]: { label: '已使用', tone: 'info' },
  [RedeemStatus.DISABLED]: { label: '已停用', tone: '' },
  [RedeemState.EXPIRED]: { label: '已过期', tone: 'warning' },
}

export const REDEEM_TYPES = {
  [RedeemType.RECHARGE]: { label: '充值', tone: 'success' },
  [RedeemType.GIFT]: { label: '赠送', tone: 'accent' },
}

export const ORDER_STATUSES = {
  [OrderStatus.PENDING]: { label: '待支付', tone: 'warning' },
  [OrderStatus.PAID]: { label: '已到账', tone: 'success' },
}

export const TX_TYPES = {
  [TxType.REDEEM]: { label: '兑换码充值', tone: 'success' },
  [TxType.REDEEM_GIFT]: { label: '兑换码赠送', tone: 'accent' },
  [TxType.ONLINE]: { label: '在线充值', tone: 'success' },
  [TxType.ADMIN]: { label: '管理员调整', tone: 'info' },
  [TxType.BONUS]: { label: '管理员赠送', tone: 'accent' },
}

// Where a model's selling price comes from (PriceBook.resolve in the backend).
export const PRICE_SOURCES = {
  override: { label: '自定义', tone: 'accent' },
  cpamp: { label: '官方价', tone: 'info' },
  default: { label: '默认价格', tone: 'warning' },
  none: { label: '未定价', tone: 'danger' },
}

export const PAY_CHANNELS = {
  alipay: '支付宝',
  wxpay: '微信支付',
  qqpay: 'QQ 钱包',
}
