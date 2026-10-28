import test from 'node:test'
import assert from 'node:assert'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test('Frontend Demo Mode Component & Safety Audit', async (t) => {
  const headerContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'Header.jsx'), 'utf8')
  const appContent = fs.readFileSync(path.join(__dirname, 'src', 'App.jsx'), 'utf8')
  const stylesContent = fs.readFileSync(path.join(__dirname, 'src', 'styles.css'), 'utf8')
  const translationsContent = fs.readFileSync(path.join(__dirname, 'src', 'utils', 'translations.js'), 'utf8')

  await t.test('1. Placement and styling of ▶ DEMO MODE button', () => {
    // Button must exist with unique ID
    assert.match(headerContent, /id=["']header-demo-mode-btn["']/, 'Header must have id="header-demo-mode-btn"')
    assert.match(headerContent, /className=\{`header-demo-mode-btn/, 'Header button must use .header-demo-mode-btn class')

    // Must be placed inside control-actions-right before header-sos-emergency-btn
    const rightActionsIndex = headerContent.indexOf('control-actions-right')
    const demoBtnIndex = headerContent.indexOf('header-demo-mode-btn')
    const sosBtnIndex = headerContent.indexOf('header-sos-emergency-btn')

    assert.ok(rightActionsIndex !== -1, 'control-actions-right container must exist')
    assert.ok(demoBtnIndex > rightActionsIndex, 'Demo mode button must be inside control-actions-right')
    assert.ok(demoBtnIndex < sosBtnIndex, 'Demo mode button must be placed BEFORE red SOS emergency button')

    // Label and play icon
    assert.match(headerContent, /▶/, 'Button must include play icon ▶')
    assert.match(headerContent, /DEMO MODE/, 'Button must display DEMO MODE text')

    // CSS Styling
    assert.match(stylesContent, /\.header-demo-mode-btn\s*\{/, 'styles.css must style .header-demo-mode-btn')
    assert.match(stylesContent, /#0284c7/, 'Button must use cyan/blue palette #0284c7')
    assert.match(stylesContent, /#0ea5e9/, 'Button must use cyan/blue palette #0ea5e9')
    assert.match(stylesContent, /\.header-demo-mode-btn\.active\s*\{/, 'Active demo state must have distinct active styling')
  })

  await t.test('2. Mobile responsiveness without overflow', () => {
    assert.match(stylesContent, /@media\s*\(max-width:\s*768px\)/, 'styles.css must have mobile media queries')
    assert.match(stylesContent, /\.header-demo-mode-btn,\s*\.header-sos-emergency-btn/, 'Mobile query must adapt header buttons')
    assert.match(stylesContent, /flex:\s*1 1 (?:auto|0)/, 'Mobile buttons must flex to fit screen width cleanly')
  })

  await t.test('3. Prominent DEMO MODE — SIMULATED EMERGENCY indicator banner', () => {
    assert.match(appContent, /DEMO MODE — SIMULATED EMERGENCY/, 'App.jsx must render DEMO MODE — SIMULATED EMERGENCY banner')
    assert.match(appContent, /id=["']demo-mode-indicator-banner["']/, 'Indicator banner must have descriptive id')
    assert.match(appContent, /role=["']region["']/, 'Banner must have accessible role')
    assert.match(appContent, /SIMULATION ACTIVE/, 'Banner must have high-visibility simulation active badge')
    assert.match(stylesContent, /\.demo-mode-indicator-banner\s*\{/, 'Banner must have dedicated high-contrast styles')
  })

  await t.test('4. Supported Hyderabad emergency scenarios & locations', () => {
    // Must include Musi River Causeway hotspot
    assert.match(appContent, /Musi River Central Causeway Flash Inundation/, 'Must support Musi River Causeway scenario')
    assert.match(appContent, /17\.382/, 'Musi River latitude must be central Hyderabad hotspot')
    assert.match(appContent, /78\.491/, 'Musi River longitude must be central Hyderabad hotspot')

    // Must include Begumpet Drainage corridor
    assert.match(appContent, /Lower Begumpet Storm-Water Canal/, 'Must support Begumpet scenario')
    assert.match(appContent, /17\.442/, 'Begumpet latitude must be valid supported coordinate')
    assert.match(appContent, /78\.475/, 'Begumpet longitude must be valid supported coordinate')
  })

  await t.test('5. Honest evacuation route calculation and no fake routes', () => {
    assert.match(appContent, /request\(['"]\/evacuation-route['"]/, 'Demo mode must exercise real evacuation-route endpoint')
    // Check that App.jsx / RoutesTab honesty is maintained
    const routesTabContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'tabs', 'RoutesTab.jsx'), 'utf8')
    assert.match(routesTabContent, /NO SAFE ROUTE FOUND/, 'NO_SAFE_ROUTE must be displayed honestly')
    assert.match(routesTabContent, /HAZARDS_AVOIDED|HAZARDS AVOIDED/, 'Detours must indicate hazards avoided honestly')
  })

  await t.test('6. Obvious Exit Demo button & state restoration', () => {
    assert.match(appContent, /id=["']exit-demo-mode-btn["']/, 'App.jsx must provide dedicated Exit Demo button')
    assert.match(appContent, /handleExitDemoMode/, 'Must have handleExitDemoMode restoring dashboard state')
    assert.match(appContent, /setPreDemoState\(null\)/, 'Must clean up preDemoState upon exit')
    assert.match(headerContent, /Exit Demo/, 'Header button must support Exit Demo text when active')
  })

  await t.test('7. Real emergency safety protections', () => {
    // Verify handleStartDemoMode does NOT trigger navigator.geolocation
    const startDemoMatch = appContent.match(/handleStartDemoMode\s*=\s*async[\s\S]*?handleExitDemoMode/)
    assert.ok(startDemoMatch, 'handleStartDemoMode function must be found in App.jsx')
    const startDemoBody = startDemoMatch[0]
    
    assert.ok(!startDemoBody.includes('navigator.geolocation'), 'handleStartDemoMode MUST NOT request browser geolocation')
    assert.ok(!startDemoBody.includes('/sos'), 'handleStartDemoMode MUST NOT call /sos endpoint')
    
    // Verify simulated incident is explicitly marked as demo
    assert.match(appContent, /\[DEMO\] Simulated/, 'Simulated incidents must be prefixed with [DEMO]')
    assert.match(appContent, /status:\s*['"]SIMULATED_DEMO['"]/, 'Simulated incident status must be SIMULATED_DEMO')
    assert.match(appContent, /is_demo:\s*true/, 'Simulated incident must have is_demo flag')
  })

  await t.test('8. Multilingual localization integrity', () => {
    assert.match(translationsContent, /demoModeButton:\s*['"]DEMO MODE['"]/, 'en translation must have demoModeButton')
    assert.match(translationsContent, /demoModeButton:\s*['"]డెమో మోడ్['"]/, 'te translation must have demoModeButton')
    assert.match(translationsContent, /demoModeButton:\s*['"]डेमो मोड['"]/, 'hi translation must have demoModeButton')
    assert.match(translationsContent, /exitDemoButton:\s*['"]Exit Demo['"]/, 'en translation must have exitDemoButton')
  })
})
