// 前端数据脱敏工具

/** 手机号脱敏: 138****5678 */
export function maskPhone(phone: string): string {
  if (!phone || phone.length < 7) return phone
  return phone.slice(0, 3) + '****' + phone.slice(-4)
}

/** 邮箱脱敏: t***@example.com */
export function maskEmail(email: string): string {
  if (!email || !email.includes('@')) return email
  const parts = email.split('@')
  const name = parts[0] || ''
  const domain = parts[1] || ''
  return name[0] + '***' + '@' + domain
}

/** 设备编号脱敏: INV**** */
export function maskDeviceId(id: string): string {
  if (!id || id.length < 4) return id
  return id.slice(0, 3) + '*'.repeat(Math.min(id.length - 3, 4))
}

/** 通用脱敏: 对字符串中段替换 */
export function maskString(value: string, showStart = 3, showEnd = 3): string {
  if (!value || value.length <= showStart + showEnd) return value
  return value.slice(0, showStart) + '*'.repeat(value.length - showStart - showEnd) + value.slice(-showEnd)
}

/** 自动检测并脱敏响应数据中的敏感字段 */
export function autoMask(obj: any, depth = 0): any {
  if (depth > 3 || obj === null || obj === undefined) return obj
  if (typeof obj === 'string') return obj
  if (Array.isArray(obj)) return obj.map(item => autoMask(item, depth + 1))
  if (typeof obj !== 'object') return obj

  const sensitiveKeys = ['phone', 'mobile', 'email', 'password', 'secret', 'token', 'api_key', 'operator']
  const result: Record<string, any> = {}

  for (const [key, value] of Object.entries(obj)) {
    if (sensitiveKeys.some(k => key.toLowerCase().includes(k))) {
      if (typeof value === 'string' && value.length > 0) {
        result[key] = value.length > 10 ? value.slice(0, 2) + '****' + value.slice(-2) : '***'
      } else {
        result[key] = '***'
      }
    } else {
      result[key] = autoMask(value, depth + 1)
    }
  }
  return result
}
