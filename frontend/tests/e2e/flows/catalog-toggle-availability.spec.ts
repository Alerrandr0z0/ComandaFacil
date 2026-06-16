import { expect, test } from '@playwright/test'

const MANAGER_EMAIL = 'lucas.gerente@barracadosol.com'
const MANAGER_PASSWORD = 'password123'
const TENANT_ID = 1

async function loginAsManager(page: import('@playwright/test').Page) {
  await page.goto('/login')
  await page.fill('#tenantId', String(TENANT_ID))
  await page.fill('#email', MANAGER_EMAIL)
  await page.fill('#password', MANAGER_PASSWORD)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/orders', { timeout: 10000 })
}

test.describe('Catalog - Toggle Availability', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsManager(page)
    await page.goto('/catalog')
    await page.waitForSelector('text=Catálogo de Produtos')
    await page.waitForSelector('button:has-text("Disponível"), button:has-text("Indisponível")', {
      timeout: 10000,
    })
  })

  test('should toggle item from available to unavailable and persist after reload', async ({
    page,
  }) => {
    const availableButton = page.locator('button:has-text("Disponível")').first()
    await expect(availableButton).toBeVisible()

    const card = availableButton.locator('xpath=ancestor::div[contains(@class,"rounded-2xl")]')
    const itemName = (await card.locator('h4').first().textContent()) ?? ''
    expect(itemName.length).toBeGreaterThan(0)

    // Intercept PATCH to confirm it fires and succeeds
    const patchPromise = page.waitForResponse(
      (resp) => resp.url().includes('/v1/menu/items/') && resp.request().method() === 'PATCH',
    )

    // Click to make unavailable
    await availableButton.click()

    const patchResponse = await patchPromise
    expect(patchResponse.status()).toBe(200)

    // Optimistic UI should show "Indisponível"
    await expect(card.locator('button:has-text("Indisponível")')).toBeVisible({ timeout: 5000 })

    // Wait for the refetch to settle (fetchItems(true) fires after PATCH)
    await page.waitForTimeout(1500)

    // Reload page
    await page.reload()
    await page.waitForSelector('button:has-text("Disponível"), button:has-text("Indisponível")', {
      timeout: 10000,
    })

    // Find the same item card after reload
    const sameItem = page.locator('h4', { hasText: itemName }).first()
    await expect(sameItem).toBeVisible({ timeout: 5000 })
    const sameCard = sameItem.locator('xpath=ancestor::div[contains(@class,"rounded-2xl")]')
    const sameButton = sameCard.locator('button').filter({ hasText: /Disponível|Indisponível/ })

    // The button should say "Indisponível" — if this fails, the toggle didn't persist
    await expect(sameButton.first()).toHaveText('Indisponível', { timeout: 5000 })
  })

  test('should toggle item back to available after making unavailable', async ({ page }) => {
    const availableButton = page.locator('button:has-text("Disponível")').first()
    await expect(availableButton).toBeVisible()

    const card = availableButton.locator('xpath=ancestor::div[contains(@class,"rounded-2xl")]')

    // Make unavailable
    await availableButton.click()
    await expect(card.locator('button:has-text("Indisponível")')).toBeVisible({ timeout: 5000 })

    // Make available again
    await card.locator('button:has-text("Indisponível")').click()
    await expect(card.locator('button:has-text("Disponível")')).toBeVisible({ timeout: 5000 })
  })

  test('should revert optimistic update on PATCH failure', async ({ page }) => {
    const availableButton = page.locator('button:has-text("Disponível")').first()
    await expect(availableButton).toBeVisible()

    const card = availableButton.locator('xpath=ancestor::div[contains(@class,"rounded-2xl")]')

    // Handle dialog BEFORE triggering the action
    page.on('dialog', (dialog) => {
      expect(dialog.message()).toContain('Erro ao alterar disponibilidade')
      dialog.accept()
    })

    // Block PATCH requests
    await page.route('**/v1/menu/items/**', (route) => {
      if (route.request().method() === 'PATCH') {
        route.abort('failed')
      } else {
        route.continue()
      }
    })

    // Click to toggle — PATCH fails, alert fires, optimistic update reverts
    await availableButton.click()

    // Should revert to "Disponível"
    await expect(card.locator('button:has-text("Disponível")')).toBeVisible({ timeout: 5000 })
  })
})
