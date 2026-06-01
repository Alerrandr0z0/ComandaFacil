import { test, expect } from '@playwright/test'

// Regra dos 3 cliques: adicionar item a uma comanda
test('should add an item to order in 3 clicks or less', async ({ page }) => {
  await page.goto('/orders')
  // TODO: implement once UI is built
  await expect(page).toHaveTitle(/ComandaFácil/)
})
