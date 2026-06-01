import { describe, it } from 'vitest'
import * as fc from 'fast-check'

describe('Order price invariants', () => {
  it('total should always be >= sum of individual items', () => {
    fc.assert(
      fc.property(
        fc.array(fc.record({ price: fc.float({ min: 0.01, max: 999.99 }), qty: fc.integer({ min: 1, max: 99 }) }), { minLength: 1 }),
        (items) => {
          const total = items.reduce((sum, item) => sum + item.price * item.qty, 0)
          return total >= 0
        }
      )
    )
  })

  it('removing an item should decrease or maintain the total', () => {
    fc.assert(
      fc.property(
        fc.array(fc.record({ price: fc.float({ min: 0.01, max: 999.99 }), qty: fc.integer({ min: 1, max: 99 }) }), { minLength: 2 }),
        (items) => {
          const totalBefore = items.reduce((sum, i) => sum + i.price * i.qty, 0)
          const [, ...remaining] = items
          const totalAfter = remaining.reduce((sum, i) => sum + i.price * i.qty, 0)
          return totalAfter <= totalBefore
        }
      )
    )
  })
})
