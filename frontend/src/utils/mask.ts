/** 自动检测并脱敏响应数据中的敏感字段 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function autoMask(obj: any, depth = 0): any {
  if (depth > 3 || obj === null || obj === undefined) return obj
  if (typeof obj === 'string') return obj
  if (Array.isArray(obj)) return obj.map(item => autoMask(item, depth + 1))
  if (typeof obj !== 'object') return obj

  const sensitiveKeys = ['phone', 'mobile', 'email', 'password', 'secret', 'token', 'api_key', 'operator']
  const result: Record<string, unknown> = {}

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
