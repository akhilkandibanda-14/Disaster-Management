import test from 'node:test'
import assert from 'node:assert'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test('Safety Fix 11: Audit Fixes Regression Tests', async (t) => {
  const translationsPath = path.join(__dirname, 'src', 'utils', 'translations.js')
  const overviewTabPath = path.join(__dirname, 'src', 'components', 'tabs', 'OverviewTab.jsx')
  const appPath = path.join(__dirname, 'src', 'App.jsx')
  const assistantPath = path.join(__dirname, 'src', 'components', 'AIAssistantChat.jsx')

  const translationsContent = fs.readFileSync(translationsPath, 'utf8')
  const overviewContent = fs.readFileSync(overviewTabPath, 'utf8')
  const appContent = fs.readFileSync(appPath, 'utf8')
  const assistantContent = fs.readFileSync(assistantPath, 'utf8')

  await t.test('1. Terminology: "Shelter Candidates" replaces misleading "Safe Shelters"', () => {
    // English translation
    assert.match(translationsContent, /layerShelters:\s*['"]Shelter Candidates['"]/, 'English translation must use "Shelter Candidates"')
    // Telugu translation
    assert.match(translationsContent, /layerShelters:\s*['"]ఆశ్రయ అభ్యర్థులు['"]/, 'Telugu translation must use "ఆశ్రయ అభ్యర్థులు"')
    // Hindi translation
    assert.match(translationsContent, /layerShelters:\s*['"]आश्रय उम्मीदवार['"]/, 'Hindi translation must use "आश्रय उम्मीदवार"')
    // OverviewTab fallback
    assert.match(overviewContent, /t\.layerShelters\s*\|\|\s*['"]Shelter Candidates['"]/, 'OverviewTab must use "Shelter Candidates" fallback')
    // Ensure no misleading "Safe Shelters" layer naming remains in translations or overview
    assert.doesNotMatch(translationsContent, /layerShelters:\s*['"]Safe Shelters['"]/, 'translations.js must not contain "Safe Shelters"')
    assert.doesNotMatch(overviewContent, /['"]Safe Shelters['"]/, 'OverviewTab.jsx must not contain "Safe Shelters"')
  })

  await t.test('2. Road conditions resilience in App.jsx', () => {
    // Check that App.jsx unpacks roadPayload defensively whether array or object
    assert.match(appContent, /resources\.roads\?\.status === 'available'/, 'Must check roads status safely')
    assert.match(appContent, /data_status === 'UNAVAILABLE'/, 'Must inspect data_status for UNAVAILABLE')
    assert.match(appContent, /nextStatus\.roads = 'unavailable'/, 'Must set dashboardStatus.roads to unavailable when degraded')
    assert.match(appContent, /Array\.isArray\(roadPayload\)\s*\?\s*roadPayload\s*:\s*\(roadPayload\?\.roads\s*\|\|\s*\[\]\)/, 'Must unpack roads array for state')
  })

  await t.test('3. AI assistant coverage explanation for MODEL_UNSUPPORTED', () => {
    // English model copy (handles escaped apostrophe model\'s)
    assert.match(assistantContent, /outside the model(?:'|\\')s supported gauge coverage/, 'English must explain outside gauge coverage')
    assert.match(assistantContent, /does not mean the location is flood-free or low risk/, 'English must state not flood-free or low risk')
    // Telugu model copy
    assert.match(assistantContent, /గేజ్ పరిధికి వెలుపల/, 'Telugu must explain outside gauge coverage')
    assert.match(assistantContent, /వరద-రహితం లేదా తక్కువ ప్రమాదం అని కాదు/, 'Telugu must state not flood-free or low risk')
    // Hindi model copy
    assert.match(assistantContent, /समर्थित कवरेज से बाहर/, 'Hindi must explain outside gauge coverage')
    assert.match(assistantContent, /बाढ़-मुक्त या कम जोखिम वाला है/, 'Hindi must state not flood-free or low risk')
    // Context riskLabel mapping
    assert.match(assistantContent, /riskData\?\.coverage_status === 'MODEL_UNSUPPORTED'/, 'Must check for MODEL_UNSUPPORTED in context')
    assert.match(assistantContent, /outside model coverage/, 'riskLabel must explain outside model coverage')
    assert.match(assistantContent, /not verified flood-free or low risk/, 'riskLabel must explicitly warn not verified flood-free')
    // Keyword pattern matches coverage queries
    assert.match(assistantContent, /\(model\|prediction\|gauge\|coverage\|unsupported\)/, 'Query regex must match coverage')
  })
})
