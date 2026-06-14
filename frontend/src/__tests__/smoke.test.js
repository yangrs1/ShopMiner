import { describe, it, expect } from 'vitest'

describe('smoke', () => {
  it('vitest runs correctly', () => {
    expect(1 + 1).toBe(2)
  })

  it('can test async code', async () => {
    const result = await Promise.resolve(42)
    expect(result).toBe(42)
  })
})
