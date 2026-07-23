import { expect, test } from '@playwright/test'

const sampleContract = '押金为两个月租金，房东可随时没收且概不退还。违约金按全部租金计算，租金可由房东单方调整。'

test.describe('rental tenant workspace', () => {
  test('loads database listings, uses page navigation, and exposes RAG evidence', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByRole('heading', { name: '在真实房源中，快速确定下一处住处' })).toBeVisible()
    const propertyCards = page.locator('.property-card')
    await expect(propertyCards.first()).toBeVisible()
    await expect(propertyCards).toHaveCount(24)
    await expect(propertyCards.first().locator('img')).toBeVisible()
    await expect(propertyCards.first().locator('img')).toHaveAttribute('src', /images\.unsplash\.com|^https?:\/\//)
    await expect.poll(() => propertyCards.first().locator('img').evaluate((image) => image.complete && image.naturalWidth > 0)).toBeTruthy()

    await page.getByRole('button', { name: '我的预约' }).click()
    await expect(page.getByRole('heading', { name: '我的预约' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '在真实房源中，快速确定下一处住处' })).toHaveCount(0)

    await page.getByRole('button', { name: '合同审查' }).click()
    await expect(page.getByRole('heading', { name: '合同风险分析' })).toBeVisible()
    await page.getByPlaceholder('粘贴租房合同条款，例如押金、租金、违约责任、维修和房东入户约定').fill(sampleContract)
    await page.getByRole('button', { name: '开始分析' }).click()
    await expect(page.getByRole('heading', { name: '与当前条款相关的审查知识' })).toBeVisible()
    await expect(page.locator('.knowledge-panel article')).toHaveCount(3)
    await expect.poll(async () => page.locator('.risk-card').count()).toBeGreaterThanOrEqual(3)
    await expect(page.locator('.risk-card.high').first()).toBeVisible()
  })

  test('keeps the navigation and primary content readable on a mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')

    await expect(page.getByRole('button', { name: '找房工作台' })).toBeVisible()
    await expect(page.getByRole('button', { name: '我的预约' })).toBeVisible()
    await expect(page.locator('.property-card').first()).toBeVisible()
    await expect(page.locator('.property-card').first().locator('img')).toBeVisible()
  })
})
