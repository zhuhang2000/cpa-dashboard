import { store } from './store'

export function currency() {
  return store.status?.currency_symbol || '$'
}

function fixed(value, min, max) {
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: min,
    maximumFractionDigits: max,
  })
}

// Balances and costs: 2 decimals normally, up to 4 for sub-unit amounts.
export function money(value, { sign = false } = {}) {
  const v = Number(value) || 0
  const abs = Math.abs(v)
  const digits = abs !== 0 && abs < 1 ? 4 : 2
  const prefix = v < 0 ? '-' : sign && v > 0 ? '+' : ''
  return `${prefix}${currency()}${fixed(abs, 2, digits)}`
}

// Per-1M-token prices: trim trailing zeros, keep up to 4 decimals.
export function price(value) {
  if (value === null || value === undefined) return '—'
  return `${currency()}${fixed(value, 0, 4)}`
}

export function num(value) {
  return (Number(value) || 0).toLocaleString('zh-CN')
}

export function tokens(value) {
  const v = Number(value) || 0
  if (v < 1000) return String(v)
  if (v < 1e6) return `${(v / 1e3).toFixed(v < 1e4 ? 2 : 1)}K`
  if (v < 1e9) return `${(v / 1e6).toFixed(2)}M`
  return `${(v / 1e9).toFixed(2)}B`
}

const pad = (n) => String(n).padStart(2, '0')

export function dateTime(ms, { seconds = false } = {}) {
  if (!ms) return '—'
  const d = new Date(ms)
  const base = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  return seconds ? `${base}:${pad(d.getSeconds())}` : base
}

export function date(ms) {
  if (!ms) return '—'
  const d = new Date(ms)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function relative(ms) {
  if (!ms) return '从未'
  const diff = Date.now() - ms
  if (diff < 60e3) return '刚刚'
  if (diff < 3600e3) return `${Math.floor(diff / 60e3)} 分钟前`
  if (diff < 86400e3) return `${Math.floor(diff / 3600e3)} 小时前`
  if (diff < 30 * 86400e3) return `${Math.floor(diff / 86400e3)} 天前`
  return date(ms)
}

export function duration(ms) {
  if (ms === null || ms === undefined) return '—'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(ms < 10000 ? 2 : 1)}s`
}

// yyyy-mm-dd (local) <-> epoch ms at local midnight
export function toInputDate(ms) {
  const d = new Date(ms)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function fromInputDate(value, endOfDay = false) {
  if (!value) return null
  const [y, m, d] = value.split('-').map(Number)
  const dt = new Date(y, m - 1, d)
  if (endOfDay) dt.setDate(dt.getDate() + 1)
  return dt.getTime()
}

export const TX_TYPES = {
  redeem: { label: '兑换码充值', tone: 'success' },
  online: { label: '在线充值', tone: 'success' },
  admin: { label: '管理员调整', tone: 'info' },
  bonus: { label: '赠送', tone: 'accent' },
}

export const KEY_STATES = {
  active: { label: '正常', tone: 'success' },
  disabled: { label: '已禁用', tone: '' },
  expired: { label: '已过期', tone: 'warning' },
  exhausted: { label: '额度用尽', tone: 'warning' },
  suspended: { label: '余额不足', tone: 'danger' },
}

export const PAY_CHANNELS = {
  alipay: '支付宝',
  wxpay: '微信支付',
  qqpay: 'QQ 钱包',
}
