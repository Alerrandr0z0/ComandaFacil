import { expect, test } from '@playwright/test'

test('should toggle catalog item availability', async ({ page }) => {
  // Navigate to login
  await page.goto('/login')

  // Log in
  await page.fill('#tenantId', '1')
  await page.fill('#email', 'lucas.gerente@barracadosol.com')
  await page.fill('#password', 'password123')
  await page.click('button[type="submit"]')

  // Wait for redirect to /orders
  await expect(page).toHaveURL(/.*\/orders/)

  // Navigate to catalog
  await page.goto('/catalog')

  // Wait for loading to disappear
  await expect(page.getByText('Carregando catálogo...')).not.toBeVisible()

  // Find a specific product card to ensure stability
  const itemCard = page.locator('div.grid > div').filter({ hasText: 'Moqueca de Camarão' }).first()
  await expect(itemCard).toBeVisible({ timeout: 10000 })

  // Find the toggle button inside the item (Disponível / Indisponível)
  const toggleBtn = itemCard.locator('button').filter({ hasText: /Disponível|Indisponível/ }).first()
  const initialText = (await toggleBtn.textContent())?.trim()
  const expectedTextAfterToggle = initialText === 'Disponível' ? 'Indisponível' : 'Disponível'

  // Click to toggle and wait for the response
  const patchPromise = page.waitForResponse(resp => 
    resp.url().includes(`/v1/menu/items/`) && resp.request().method() === 'PATCH'
  )
  await toggleBtn.click()
  const response = await patchPromise
  console.log(`PATCH Response Status: ${response.status()}`)

  // Verify it changed on-screen
  await expect(toggleBtn).toHaveText(expectedTextAfterToggle)

  // Reload page and verify it persisted
  await page.reload()
  await expect(page.getByText('Carregando catálogo...')).not.toBeVisible()
  
  const sameItemAfterReload = page.locator('div.grid > div').filter({ hasText: 'Moqueca de Camarão' }).first()
  const toggleBtnAfterReload = sameItemAfterReload.locator('button').filter({ hasText: /Disponível|Indisponível/ }).first()
  await expect(toggleBtnAfterReload).toHaveText(expectedTextAfterToggle, { timeout: 10000 })

  // Toggle back to clean up state
  await toggleBtnAfterReload.click()
  await page.waitForResponse(resp => 
    resp.url().includes(`/v1/menu/items/`) && resp.request().method() === 'PATCH'
  )
  await expect(toggleBtnAfterReload).toHaveText(initialText || '', { timeout: 10000 })
})
