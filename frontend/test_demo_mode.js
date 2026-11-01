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
  const routesTabContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'tabs', 'RoutesTab.jsx'), 'utf8')
  const incidentsContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'tabs', 'IncidentsTab.jsx'), 'utf8')
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
    assert.match(headerContent, /Launch simulated Hyderabad flood emergency demonstration/, 'Demo control must explain simulation')
    assert.match(headerContent, /Exit simulated emergency demonstration/, 'Active control must explain restoration')
    assert.match(translationsContent, /demoSimulatedEmergency:/, 'Simulation copy must be localized')
    assert.match(stylesContent, /\.demo-mode-indicator-banner\s*\{/, 'Simulation banner styles must remain available')
  })

  await t.test('4. Supported Hyderabad emergency scenarios & locations', () => {
    assert.match(incidentsContent, /Musi River Causeway/, 'Musi River incident location must be available')
    assert.match(incidentsContent, /17\.3789/, 'Musi River latitude must be preserved')
    assert.match(incidentsContent, /78\.4871/, 'Musi River longitude must be preserved')
    assert.match(incidentsContent, /Begumpet Rasoolpura Canal/, 'Begumpet incident location must be available')
  })

  await t.test('5. Honest evacuation route calculation and no fake routes', () => {
    assert.match(appContent, /useEvacuationRoute/, 'App must use the production route lifecycle')
    assert.match(routesTabContent, /NO SAFE ROUTE FOUND/, 'NO_SAFE_ROUTE must be displayed honestly')
    assert.match(routesTabContent, /not flood-verified/, 'External directions must not imply flood verification')
    assert.match(routesTabContent, /HAZARDS_AVOIDED|HAZARDS AVOIDED/, 'Detours must indicate hazards avoided honestly')
  })

  await t.test('6. Obvious Exit Demo button & state restoration', () => {
    assert.match(headerContent, /isDemoMode = false/, 'Header must accept controlled demo state')
    assert.match(headerContent, /onClick=\{onToggleDemoMode\}/, 'Demo state changes must be delegated to the parent')
    assert.match(headerContent, /t\.exitDemoButton \|\| 'Exit Demo'/, 'Active state must expose an exit label')
    assert.match(translationsContent, /exitDemoButton:/, 'Exit label must be localized')
  })

  await t.test('7. Real emergency safety protections', () => {
    assert.ok(!headerContent.includes('navigator.geolocation'), 'Header demo control must not request browser geolocation')
    assert.ok(!headerContent.includes('/sos'), 'Header demo control must not submit SOS records')
    assert.match(headerContent, /onToggleDemoMode/, 'Demo behavior must be supplied explicitly by the parent')
    assert.match(appContent, /navigator\.geolocation/, 'Location access must remain in the explicit location workflow')
  })

  await t.test('8. Multilingual localization integrity', () => {
    assert.match(translationsContent, /demoModeButton:\s*['"]DEMO MODE['"]/, 'en translation must have demoModeButton')
    assert.match(translationsContent, /demoModeButton:\s*['"]డెమో మోడ్['"]/, 'te translation must have demoModeButton')
    assert.match(translationsContent, /demoModeButton:\s*['"]डेमो मोड['"]/, 'hi translation must have demoModeButton')
    assert.match(translationsContent, /exitDemoButton:\s*['"]Exit Demo['"]/, 'en translation must have exitDemoButton')
  })
})
