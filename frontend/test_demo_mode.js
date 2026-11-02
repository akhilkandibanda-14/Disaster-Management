import test from 'node:test'
import assert from 'node:assert'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test('Frontend Demo Mode Removal & Production Safety Audit', async (t) => {
  const headerContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'Header.jsx'), 'utf8')
  const appContent = fs.readFileSync(path.join(__dirname, 'src', 'App.jsx'), 'utf8')
  const routesTabContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'tabs', 'RoutesTab.jsx'), 'utf8')
  const incidentsContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'tabs', 'IncidentsTab.jsx'), 'utf8')
  const overviewContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'tabs', 'OverviewTab.jsx'), 'utf8')
  const stylesContent = fs.readFileSync(path.join(__dirname, 'src', 'styles.css'), 'utf8')
  const translationsContent = fs.readFileSync(path.join(__dirname, 'src', 'utils', 'translations.js'), 'utf8')

  await t.test('1. Demo Mode button completely removed from Header', () => {
    assert.ok(!headerContent.includes('id="header-demo-mode-btn"'), 'Header must NOT contain #header-demo-mode-btn')
    assert.ok(!headerContent.includes('header-demo-mode-btn'), 'Header must NOT use .header-demo-mode-btn class')
    assert.ok(!headerContent.includes('isDemoMode'), 'Header must NOT declare isDemoMode prop')
    assert.ok(!headerContent.includes('onToggleDemoMode'), 'Header must NOT declare onToggleDemoMode prop')

    // Right actions must only contain the SOS emergency button
    const rightActionsIndex = headerContent.indexOf('control-actions-right')
    const sosBtnIndex = headerContent.indexOf('header-sos-emergency-btn')
    assert.ok(rightActionsIndex !== -1, 'control-actions-right container must exist')
    assert.ok(sosBtnIndex > rightActionsIndex, 'SOS emergency button must remain in control-actions-right')
  })

  await t.test('2. Mobile responsiveness without overflow', () => {
    assert.match(stylesContent, /@media\s*\(max-width:\s*768px\)/, 'styles.css must have mobile media queries')
    assert.match(stylesContent, /\.header-sos-emergency-btn/, 'Mobile query must style header emergency button')
  })

  await t.test('3. Demo Mode banner completely removed from App', () => {
    assert.ok(!appContent.includes('id="demo-mode-indicator-banner"'), 'App must NOT render demo-mode-indicator-banner')
    assert.ok(!appContent.includes('isDemoMode'), 'App must NOT contain isDemoMode state')
    assert.ok(!appContent.includes('handleToggleDemoMode'), 'App must NOT contain handleToggleDemoMode handler')
  })

  await t.test('4. Supported Hyderabad emergency scenarios & locations preserved', () => {
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

  await t.test('6. OverviewTab renders clean live telemetry without demo tags', () => {
    assert.ok(!overviewContent.includes('isDemoMode'), 'OverviewTab must NOT declare isDemoMode prop')
    assert.ok(!overviewContent.includes('[DEMO SIMULATION]'), 'OverviewTab must NOT display [DEMO SIMULATION]')
    assert.ok(!overviewContent.includes('SIMULATED FLOOD [DEMO]'), 'OverviewTab must NOT display SIMULATED FLOOD [DEMO]')
  })

  await t.test('7. Real emergency safety protections', () => {
    assert.ok(!headerContent.includes('navigator.geolocation'), 'Header must not request browser geolocation')
    assert.match(appContent, /navigator\.geolocation/, 'Location access must remain in the explicit location workflow')
  })

  await t.test('8. Multilingual localization integrity', () => {
    assert.match(translationsContent, /appTitle:/, 'en translation must have appTitle')
    assert.match(translationsContent, /citizenTab:/, 'Translations must contain tab labels')
  })
})
