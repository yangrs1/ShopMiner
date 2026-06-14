import { describe, it, expect } from 'vitest'
import { fmtMoney } from '../admin/composables/useECharts'

describe('fmtMoney', () => {
  it('formats integer yuan correctly', () => {
    // 10000 分 = 100 元
    expect(fmtMoney(10000)).toBe('¥100.00')
  })

  it('formats zero as ¥0.00', () => {
    expect(fmtMoney(0)).toBe('¥0.00')
  })

  it('handles null as dash', () => {
    expect(fmtMoney(null)).toBe('-')
  })

  it('handles undefined as dash', () => {
    expect(fmtMoney(undefined)).toBe('-')
  })

  it('formats large amounts with locale separators', () => {
    // 10000000 分 = 100000 元
    expect(fmtMoney(10000000)).toBe('¥100,000.00')
  })

  it('formats decimal amounts correctly', () => {
    // 150 分 = 1.50 元
    expect(fmtMoney(150)).toBe('¥1.50')
  })

  it('formats small amounts less than 1 yuan', () => {
    // 99 分 = 0.99 元
    expect(fmtMoney(99)).toBe('¥0.99')
  })

  it('handles negative amounts', () => {
    // -500 分 = -5.00 元
    expect(fmtMoney(-500)).toBe('¥-5.00')
  })

  it('handles NaN as dash', () => {
    expect(fmtMoney(NaN)).toBe('-')
  })

  it('handles non-numeric string as dash', () => {
    expect(fmtMoney('abc')).toBe('-')
  })

  it('formats string number correctly', () => {
    expect(fmtMoney('2000')).toBe('¥20.00')
  })

  it('formats amount with three-digit group separators', () => {
    // 123456 分 = 1234.56 元
    expect(fmtMoney(123456)).toBe('¥1,234.56')
  })
})
