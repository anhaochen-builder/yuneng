/** 风险等级英文 → 中文 */
export function riskLabel(level: string): string {
  const map: Record<string, string> = {
    CRITICAL: '危急',
    HIGH: '高',
    MEDIUM: '中',
    LOW: '低',
    critical: '危急',
    high: '高',
    medium: '中',
    low: '低',
    EMERGENCY: '紧急',
    emergency: '紧急',
  }
  return map[level] || level
}
