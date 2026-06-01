import { test, expect } from '@playwright/test'

// Regra dos 3 cliques: abrir uma comanda
test('should open an order in 3 clicks or less', async ({ page }) => {
  await page.goto('/')
  // TODO: implement once UI is built
  // Click 1: Navigate to orders
  // Click 2: Select table
  // Click 3: Confirm open order
  await expect(page).toHaveTitle(/ComandaFácil/)
})
