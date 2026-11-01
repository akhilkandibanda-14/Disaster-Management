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
    assert.match(appContent, /shelters=\{shelters\}/, 'Must pass shelter records')
    assert.match(appContent, /riskData=\{riskData\}/, 'Must pass risk data')
    assert.match(appContent, /weather=\{weather\}/, 'Must pass weather data')
    assert.match(appContent, /language=\{language\}/, 'Must pass language prop')
  })

  await t.test('2. Guidance is local and does not send dashboard data to an AI endpoint', () => {
    assert.match(assistantContent, /const answer = \(query\)/, 'Assistant must use the local grounded answer function')
    assert.doesNotMatch(assistantContent, /fetch\(/, 'Assistant must not send data to an external AI endpoint')
    assert.match(assistantContent, /No external AI/, 'UI must disclose that no external AI is used')
  })

  await t.test('3. Emergency guidance keeps official contact links visible', () => {
    assert.match(assistantContent, /href=\{contact\.href\}/, 'Emergency contacts must be rendered as links')
    assert.match(assistantContent, /href: ['"]tel:112['"]/, 'Must provide direct 112 dialing')
    assert.match(assistantContent, /href: ['"]tel:108['"]/, 'Must provide ambulance dialing')
    assert.match(assistantContent, /href: ['"]tel:04021111111['"]/, 'Must provide GHMC DRF dialing')
    assert.match(assistantContent, /call 112/i, 'Emergency copy must direct users to 112')
  })

  await t.test('4. Guidance includes route and shelter safety limitations', () => {
    assert.match(assistantContent, /not a guarantee that a road is open or flood-free/i)
    assert.match(assistantContent, /may be unverified for live capacity or structural safety/i)
    assert.match(stylesContent, /\.ai-message-source\s*\{/, 'Source and limitation labels must be styled')
  })

  await t.test('5. Multilingual suggested flood questions (en, te, hi)', () => {
    for (const language of ['en', 'te', 'hi']) {
      assert.match(assistantContent, new RegExp(`${language}:\\s*\\{`), `${language} copy must exist`)
    }
    assert.match(assistantContent, /quickQuestions:/, 'Each language must provide safe quick questions')
    assert.match(assistantContent, /emergency|safety/i, 'Quick guidance must include emergency or safety wording')
  })

  await t.test('6. Input validation and character count constraints', () => {
    assert.match(assistantContent, /if \(!cleanQuery\) return/, 'Blank questions must be ignored')
    assert.match(assistantContent, /disabled=\{!userQuery\.trim\(\)\}/, 'Send button must be disabled for empty input')
  })

  await t.test('7. Real emergency safety protections (no accidental SOS or geolocation prompt)', () => {
    assert.ok(!assistantContent.includes('navigator.geolocation'), 'Chat assistant MUST NOT invoke browser geolocation prompts')
    assert.ok(!assistantContent.includes('/sos'), 'Chat assistant MUST NOT submit automated SOS records')
    assert.ok(!assistantContent.includes('/incidents'), 'Chat assistant MUST NOT post public incidents without explicit user form')
  })
})
