import test from 'node:test'
import assert from 'node:assert'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test('Frontend AI Safety Assistant Audit', async (t) => {
  const assistantContent = fs.readFileSync(path.join(__dirname, 'src', 'components', 'AIAssistantChat.jsx'), 'utf8')
  const appContent = fs.readFileSync(path.join(__dirname, 'src', 'App.jsx'), 'utf8')
  const stylesContent = fs.readFileSync(path.join(__dirname, 'src', 'styles.css'), 'utf8')

  await t.test('1. AIAssistantChat receives rich dashboard context props from App.jsx', () => {
    assert.match(appContent, /<AIAssistantChat/, 'AIAssistantChat must be mounted in App.jsx')
    assert.match(appContent, /location=\{location\}/, 'Must pass location prop')
    assert.match(appContent, /hazardWarning=\{hazardWarning\}/, 'Must pass hazardWarning prop')
    assert.match(appContent, /route=\{route\}/, 'Must pass route prop')
    assert.match(appContent, /isSevereWeather=\{isSevereWeather\}/, 'Must pass isSevereWeather prop')
    assert.match(appContent, /isDemoMode=\{isDemoMode\}/, 'Must pass isDemoMode prop')
    assert.match(appContent, /selectedFacility=\{selectedFacility\}/, 'Must pass selectedFacility prop')
    assert.match(appContent, /language=\{language\}/, 'Must pass language prop')
    assert.match(appContent, /apiBaseUrl=\{apiBaseUrl\}/, 'Must pass apiBaseUrl prop')
    assert.match(appContent, /onNavigateToTab=\{setActiveTab\}/, 'Must pass onNavigateToTab prop')
  })

  await t.test('2. Real HTTP communication with backend /assistant/query', () => {
    assert.match(assistantContent, /\$\{apiBaseUrl\}\/assistant\/query/, 'Must POST to ${apiBaseUrl}/assistant/query')
    assert.match(assistantContent, /method:\s*['"]POST['"]/, 'Must use POST method')
    assert.match(assistantContent, /AbortController/, 'Must enforce AbortController request timeout')
    assert.match(assistantContent, /setTimeout\(\(\)\s*=>\s*controller\.abort\(\),\s*8000\)/, 'Timeout must be 8 seconds')
  })

  await t.test('3. Immediate danger alert banner and emergency phone dials', () => {
    assert.match(assistantContent, /ai-danger-alert-box/, 'Must render ai-danger-alert-box on emergency')
    assert.match(assistantContent, /CRITICAL SAFETY ALERT/, 'Must flag critical safety alert')
    assert.match(assistantContent, /window\.open\(['"]tel:112['"]/, 'Must support direct 112 dialing')
    assert.match(assistantContent, /window\.open\(['"]tel:04021111111['"]/, 'Must support direct GHMC DRF dialing')
    assert.match(stylesContent, /\.ai-danger-alert-box\s*\{/, 'styles.css must style ai-danger-alert-box')
  })

  await t.test('4. Loading indicators, error messages, and retry behavior', () => {
    assert.match(assistantContent, /ai-loading-dots/, 'Must have animated loading dots')
    assert.match(assistantContent, /ai-chat-error-bar/, 'Must have error notification bar')
    assert.match(assistantContent, /retry-btn/, 'Must have retry button')
    assert.match(assistantContent, /sendQuery\(lastQuery\)/, 'Retry button must re-trigger lastQuery')
    assert.match(stylesContent, /\.ai-loading-dots\s*\{/, 'styles.css must style ai-loading-dots')
  })

  await t.test('5. Multilingual suggested flood questions (en, te, hi)', () => {
    assert.match(assistantContent, /I am near the Musi River and water is rising/, 'English Musi River question must exist')
    assert.match(assistantContent, /మూసీ నది వద్ద నీరు పెరుగుతుంది/, 'Telugu Musi River question must exist')
    assert.match(assistantContent, /मूसी नदी के पास जलस्तर बढ़ रहा है/, 'Hindi Musi River question must exist')
    assert.match(assistantContent, /NO_SAFE_ROUTE/, 'NO_SAFE_ROUTE question must exist in suggestions')
  })

  await t.test('6. Input validation and character count constraints', () => {
    assert.match(assistantContent, /disabled=\{!userQuery\.trim\(\)\s*\|\|\s*isLoading\}/, 'Send button must be disabled for empty or in-flight query')
    assert.match(assistantContent, /maxLength=\{1200\}/, 'Input must constrain max length to prevent huge payloads')
  })

  await t.test('7. Real emergency safety protections (no accidental SOS or geolocation prompt)', () => {
    assert.ok(!assistantContent.includes('navigator.geolocation'), 'Chat assistant MUST NOT invoke browser geolocation prompts')
    assert.ok(!assistantContent.includes('/sos'), 'Chat assistant MUST NOT submit automated SOS records')
    assert.ok(!assistantContent.includes('/incidents'), 'Chat assistant MUST NOT post public incidents without explicit user form')
  })
})
