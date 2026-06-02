import { expect, test } from '@playwright/test'

// Regra dos 3 cliques: fechar a conta
test('should close the bill in 3 clicks or less', async ({ page }) => {
  await page.goto('/orders')
  // TODO: implement once UI is built
  await expect(page).toHaveTitle(/ComandaFácil/)
})
