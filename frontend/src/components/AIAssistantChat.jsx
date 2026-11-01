import React, { useMemo, useState } from 'react'

const CONTACTS = [
  { label: 'National Emergency', number: '112', href: 'tel:112' },
  { label: 'Ambulance', number: '108', href: 'tel:108' },
  { label: 'GHMC DRF', number: '040-21111111', href: 'tel:04021111111' },
  { label: 'Police', number: '100', href: 'tel:100' },
]

const COPY = {
  en: {
    welcome: 'I provide grounded flood-safety guidance from this dashboard. I do not replace 112, GHMC, police, ambulance services, or official warnings. If anyone is in immediate danger, call 112 now.',
    emergency: 'If there is immediate danger, call 112 now. For an ambulance call 108; for GHMC Disaster Response Force call 040-21111111. Move away from moving water, avoid driving through water, and follow official responders.',
    trapped: 'If trapped by rising water: move to the highest safe level, take a phone, water, torch and medicines, switch off electricity only if it is safe, and signal your location. Never enter moving water or a flooded underpass. Call 112.',
    route: 'The route shown is a decision-support result from the road graph and available hazard checks. It is not a guarantee that a road is open or flood-free. Follow police and emergency-service instructions, and turn around if conditions differ on the ground.',
    shelter: 'Shelter and hospital records shown here may be unverified for live capacity or structural safety. Call ahead when possible and confirm with local officials before travelling.',
    risk: 'The dashboard currently reports {risk}. Weather: {weather}. These are informational model/feed results, not an official warning. Confirm changing conditions with authorities.',
    floodPresent: '{floodStatus} at your current map location. {hazardDetail} This check only covers known mapped hazards; no result does not guarantee safety.',
    greeting: 'Hello. I can answer questions about your current flood status, weather, routes, shelters, emergency contacts, and basic flood safety.',
    safety: 'Basic flood safety: move to higher ground, never walk or drive through moving water, stay away from drains and manholes, switch off electricity only if safe, and call 112 for immediate danger.',
    definition: 'A flood is water covering land that is normally dry. It can result from heavy rain, overflowing rivers, blocked drains, or urban waterlogging. Avoid entering floodwater because depth and currents can be hidden.',
    location: 'Your dashboard is currently using the selected location at {coordinates}. Location-based answers are limited to the data available for that point.',
    model: 'Predictions are intentionally suppressed when the calibrated gauge-coverage safeguard is not met. The system prefers “unknown” over an invented risk number.',
    fallback: 'I can help with immediate flood safety, routes, shelters, alerts, or emergency contacts. For a life-threatening situation, stop using the app and call 112.',
    sourceDashboard: 'Source: current dashboard data',
    sourceOfficial: 'Source: official emergency contact guidance',
    sourceSafety: 'Source: standard flood-safety protocol',
    sourceLimits: 'Safety limit: not an official alert or guaranteed route',
    status: 'Grounded guidance · No external AI',
    title: 'SafeMap Safety Assistant',
    quick: 'Ask safely',
    quickQuestions: ['I am trapped by water', 'What is my current risk?', 'Can I use this route?', 'Show emergency contacts'],
    placeholder: 'Ask about danger, routes, shelters, or safety…',
    send: 'Send',
    emergencyLabel: 'Emergency contacts',
  },
  te: {
    welcome: 'నేను ఈ డాష్‌బోర్డ్‌లోని ధృవీకరించిన సమాచారంతో వరద భద్రతా సూచనలు ఇస్తాను. నేను 112, GHMC, పోలీస్ లేదా అధికారిక హెచ్చరికలకు ప్రత్యామ్నాయం కాదు. తక్షణ ప్రమాదం ఉంటే 112కు కాల్ చేయండి.',
    emergency: 'తక్షణ ప్రమాదం ఉంటే 112కు కాల్ చేయండి. అంబులెన్స్ కోసం 108, GHMC DRF కోసం 040-21111111కు కాల్ చేయండి. ప్రవహించే నీటికి దూరంగా ఉండండి; అధికారుల సూచనలు పాటించండి.',
    trapped: 'నీరు పెరుగుతూ చిక్కుకుపోతే: ఎత్తైన సురక్షిత ప్రదేశానికి వెళ్లండి, ఫోన్/నీరు/టార్చ్/మందులు తీసుకోండి, సురక్షితంగా ఉంటే విద్యుత్ ఆపండి, మీ స్థానం తెలియజేయండి. వరద నీటిలోకి వెళ్లవద్దు. 112కు కాల్ చేయండి.',
    route: 'చూపిన మార్గం రోడ్ గ్రాఫ్ మరియు అందుబాటులో ఉన్న ప్రమాద తనిఖీల ఆధారిత సూచన మాత్రమే. ఇది రహదారి సురక్షితం లేదా తెరిచి ఉందని హామీ కాదు. స్థానిక అధికారుల సూచనలు పాటించండి.',
    shelter: 'ఆశ్రయాలు మరియు ఆసుపత్రుల సామర్థ్యం లేదా నిర్మాణ భద్రత ప్రత్యక్షంగా ధృవీకరించబడకపోవచ్చు. వీలైతే ముందుగా ఫోన్ చేసి అధికారులతో నిర్ధారించండి.',
    risk: 'డాష్‌బోర్డ్ ప్రస్తుతం {risk} అని చూపుతోంది. వాతావరణం: {weather}. ఇది అధికారిక హెచ్చరిక కాదు; అధికారులతో నిర్ధారించండి.',
    floodPresent: '{floodStatus} మీ ప్రస్తుత మ్యాప్ స్థానంలో ఉంది. {hazardDetail} ఈ తనిఖీ తెలిసిన మ్యాప్ ప్రమాదాలను మాత్రమే చూస్తుంది; సమాచారం లేకపోవడం భద్రతకు హామీ కాదు.',
    greeting: 'నమస్కారం. మీ ప్రస్తుత వరద స్థితి, వాతావరణం, మార్గాలు, ఆశ్రయాలు, అత్యవసర నంబర్లు మరియు ప్రాథమిక భద్రత గురించి నేను చెప్పగలను.',
    safety: 'ప్రాథమిక వరద భద్రత: ఎత్తైన ప్రదేశానికి వెళ్లండి, ప్రవహించే నీటిలో నడవకండి లేదా వాహనం నడపకండి, కాలువలు మరియు మ్యాన్‌హోళ్లకు దూరంగా ఉండండి, సురక్షితంగా ఉంటే విద్యుత్ ఆపండి, తక్షణ ప్రమాదంలో 112కు కాల్ చేయండి.',
    definition: 'వరద అంటే సాధారణంగా పొడిగా ఉండే భూమిపై నీరు చేరడం. భారీ వర్షం, నది పొంగడం, మూసుకుపోయిన కాలువలు లేదా పట్టణ నీటి నిల్వ దీనికి కారణం కావచ్చు. లోతు తెలియకపోవచ్చు కాబట్టి వరద నీటిలోకి వెళ్లవద్దు.',
    location: 'డాష్‌బోర్డ్ ప్రస్తుతం ఎంచుకున్న స్థానం {coordinates}ను ఉపయోగిస్తోంది. స్థాన ఆధారిత సమాధానాలు అందుబాటులో ఉన్న డేటాకు మాత్రమే పరిమితం.',
    model: 'క్యాలిబ్రేటెడ్ గేజ్ పరిధి సరిపోకపోతే అంచనాలు ఉద్దేశపూర్వకంగా నిలిపివేయబడతాయి. ఊహించిన సంఖ్య కంటే “తెలియదు” అనేదే సురక్షితం.',
    fallback: 'తక్షణ వరద భద్రత, మార్గాలు, ఆశ్రయాలు, హెచ్చరికలు లేదా అత్యవసర నంబర్ల గురించి అడగండి. ప్రాణాపాయం ఉంటే 112కు కాల్ చేయండి.',
    sourceDashboard: 'మూలం: ప్రస్తుత డాష్‌బోర్డ్ సమాచారం',
    sourceOfficial: 'మూలం: అధికారిక అత్యవసర సంప్రదింపులు',
    sourceSafety: 'మూలం: వరద భద్రతా విధానం',
    sourceLimits: 'భద్రతా పరిమితి: అధికారిక హెచ్చరిక లేదా హామీ మార్గం కాదు',
    status: 'ధృవీకరించిన సూచనలు · బాహ్య AI లేదు',
    title: 'SafeMap భద్రతా సహాయకుడు',
    quick: 'సురక్షితంగా అడగండి',
    quickQuestions: ['నీటిలో చిక్కుకున్నాను', 'నా ప్రస్తుత ప్రమాదం ఏమిటి?', 'ఈ మార్గాన్ని ఉపయోగించవచ్చా?', 'అత్యవసర నంబర్లు చూపండి'],
    placeholder: 'ప్రమాదం, మార్గం లేదా భద్రత గురించి అడగండి…',
    send: 'పంపు',
    emergencyLabel: 'అత్యవసర సంప్రదింపులు',
  },
  hi: {
    welcome: 'मैं इस डैशबोर्ड के उपलब्ध डेटा से बाढ़-सुरक्षा मार्गदर्शन देता हूं। मैं 112, GHMC, पुलिस या आधिकारिक चेतावनियों का विकल्प नहीं हूं। तत्काल खतरे में अभी 112 पर कॉल करें।',
    emergency: 'तत्काल खतरे में अभी 112 पर कॉल करें। एम्बुलेंस के लिए 108 और GHMC DRF के लिए 040-21111111 पर कॉल करें। बहते पानी से दूर रहें और अधिकारियों के निर्देश मानें।',
    trapped: 'बढ़ते पानी में फंसने पर: ऊंची सुरक्षित जगह जाएं, फोन/पानी/टॉर्च/दवाएं लें, सुरक्षित हो तो बिजली बंद करें और अपना स्थान बताएं। बाढ़ के पानी में न उतरें। 112 पर कॉल करें।',
    route: 'दिखाया गया मार्ग रोड ग्राफ और उपलब्ध खतरा-जांच पर आधारित सलाह है। यह सड़क खुली या बाढ़-मुक्त होने की गारंटी नहीं है। स्थानीय अधिकारियों की बात मानें।',
    shelter: 'आश्रय और अस्पताल की क्षमता या संरचनात्मक सुरक्षा लाइव सत्यापित नहीं हो सकती। संभव हो तो पहले फोन करके अधिकारियों से पुष्टि करें।',
    risk: 'डैशबोर्ड अभी {risk} दिखा रहा है। मौसम: {weather}। यह आधिकारिक चेतावनी नहीं है; अधिकारियों से पुष्टि करें।',
    floodPresent: '{floodStatus} आपके वर्तमान मानचित्र स्थान पर। {hazardDetail} यह जांच केवल ज्ञात मानचित्रित खतरों को देखती है; कोई परिणाम न मिलना सुरक्षा की गारंटी नहीं है।',
    greeting: 'नमस्ते। मैं आपके वर्तमान बाढ़-स्थिति, मौसम, मार्ग, आश्रय, आपातकालीन संपर्क और बाढ़-सुरक्षा के बारे में बता सकता हूं।',
    safety: 'बाढ़ सुरक्षा: ऊंची जगह जाएं, बहते पानी में न चलें या वाहन न चलाएं, नालों और मैनहोल से दूर रहें, सुरक्षित हो तो बिजली बंद करें और तत्काल खतरे में 112 पर कॉल करें।',
    definition: 'बाढ़ वह स्थिति है जब सामान्य रूप से सूखी जमीन पर पानी भर जाता है। भारी बारिश, नदी का उफान, बंद नालियां या जलभराव इसके कारण हो सकते हैं।',
    location: 'डैशबोर्ड अभी चुने गए स्थान {coordinates} का उपयोग कर रहा है। स्थान-आधारित जवाब उपलब्ध डेटा तक सीमित हैं।',
    model: 'कैलिब्रेटेड गेज कवरेज न मिलने पर अनुमान जानबूझकर रोक दिए जाते हैं। गलत संख्या देने से “अज्ञात” बेहतर है।',
    fallback: 'तत्काल बाढ़ सुरक्षा, मार्ग, आश्रय, चेतावनी या आपातकालीन नंबर के बारे में पूछें। जान का खतरा हो तो 112 पर कॉल करें।',
    sourceDashboard: 'स्रोत: वर्तमान डैशबोर्ड डेटा',
    sourceOfficial: 'स्रोत: आधिकारिक आपातकालीन संपर्क',
    sourceSafety: 'स्रोत: बाढ़-सुरक्षा प्रोटोकॉल',
    sourceLimits: 'सुरक्षा सीमा: आधिकारिक चेतावनी या गारंटीकृत मार्ग नहीं',
    status: 'ग्राउंडेड मार्गदर्शन · बाहरी AI नहीं',
    title: 'SafeMap सुरक्षा सहायक',
    quick: 'सुरक्षित सवाल पूछें',
    quickQuestions: ['मैं पानी में फंसा हूं', 'मेरा वर्तमान खतरा क्या है?', 'क्या मैं यह मार्ग उपयोग करूं?', 'आपातकालीन नंबर दिखाएं'],
    placeholder: 'खतरे, मार्ग या सुरक्षा के बारे में पूछें…',
    send: 'भेजें',
    emergencyLabel: 'आपातकालीन संपर्क',
  },
}

const format = (text, context) => text
  .replace('{risk}', context.riskLabel)
  .replace('{weather}', context.weatherLabel)
  .replace('{floodStatus}', context.floodStatus)
  .replace('{hazardDetail}', context.hazardDetail)
  .replace('{coordinates}', context.coordinates)

export default function AIAssistantChat({ language = 'en', riskData, weather, alerts = [], route, shelters = [], hazardWarning, location }) {
  const copy = COPY[language] || COPY.en
  const [isOpen, setIsOpen] = useState(false)
  const [userQuery, setUserQuery] = useState('')
  const [messages, setMessages] = useState([{ sender: 'bot', text: copy.welcome, source: copy.sourceLimits }])

  const context = useMemo(() => ({
    riskLabel: riskData?.risk_level || riskData?.risk_label || 'unknown / not confirmed',
    weatherLabel: weather?.description || weather?.condition || 'not available',
    alertCount: alerts.length,
    routeStatus: route?.status || 'not calculated',
    shelterCount: shelters.length,
    floodStatus: hazardWarning
      ? (hazardWarning.is_in_hazard_zone ? `A known flood hazard is present` : 'No known mapped flood hazard is reported')
      : 'Flood-location check is not available',
    hazardDetail: hazardWarning?.highest_severity && hazardWarning.highest_severity !== 'NONE'
      ? `Highest mapped severity: ${hazardWarning.highest_severity}.`
      : 'No mapped hazard severity is currently available.',
    coordinates: location ? `${Number(location.latitude).toFixed(4)}, ${Number(location.longitude).toFixed(4)}` : 'the default Hyderabad location',
  }), [riskData, weather, alerts.length, route, shelters.length, hazardWarning, location])

  const answer = (query) => {
    const lower = query.toLowerCase()
    if (/(^|\s)(hi|hello|hey|namaste|ನಮಸ್ಕಾರ)(\s|!|$)/i.test(lower)) return { text: copy.greeting, source: copy.sourceSafety }
    if (/(is there|any|present|current|near me|at my|my location|location).*(flood|waterlog|inundat|hazard)|(flood|waterlog|inundat|hazard).*(present|current|near me|my location)/i.test(lower)) {
      return { text: format(copy.floodPresent, context), source: copy.sourceDashboard }
    }
    if (/(what is|meaning of|define).*(flood|disaster|waterlog)/i.test(lower)) return { text: copy.definition, source: copy.sourceSafety }
    if (/(how to stay safe|stay safe|safety tips|what should i do|basic safety)/i.test(lower)) return { text: copy.safety, source: copy.sourceSafety }
    if (/(where am i|my coordinates|current location|which location)/i.test(lower)) return { text: format(copy.location, context), source: copy.sourceDashboard }
    if (/(die|dying|trapped|stuck|help me|emergency|sos|danger|rescue|save)/i.test(lower)) {
      return { text: copy.trapped, source: copy.sourceOfficial, emergency: true }
    }
    if (/(call|number|ambulance|police|112|108|ghmc)/i.test(lower)) {
      return { text: copy.emergency, source: copy.sourceOfficial, emergency: true }
    }
    if (/(route|evac|road|drive|car|travel)/i.test(lower)) return { text: copy.route, source: copy.sourceLimits }
    if (/(shelter|hospital|bed|safe place)/i.test(lower)) return { text: copy.shelter, source: copy.sourceDashboard }
    if (/(risk|weather|rain|alert|status|temperature|forecast)/i.test(lower)) return { text: format(copy.risk, context), source: `${copy.sourceDashboard} · ${context.alertCount} alert(s)` }
    if (/(model|prediction|gauge|unsupported)/i.test(lower)) return { text: copy.model, source: copy.sourceLimits }
    return { text: copy.fallback, source: copy.sourceSafety }
  }

  const sendMessage = (query) => {
    const cleanQuery = query.trim()
    if (!cleanQuery) return
    const reply = answer(cleanQuery)
    setMessages((previous) => [...previous, { sender: 'user', text: cleanQuery }, { sender: 'bot', ...reply }])
    setUserQuery('')
  }

  return (
    <>
      <button type="button" className="ai-chat-floating-btn" onClick={() => setIsOpen(!isOpen)} aria-label="Open AI Safety Assistant">
        <span className="ai-btn-avatar" aria-hidden="true">🛟</span>
        <span className="ai-btn-text">AI Safety Assistant</span>
      </button>

      {isOpen && (
        <div className="ai-chat-window" role="dialog" aria-modal="true" aria-labelledby="ai-chat-title">
          <div className="ai-chat-header">
            <div className="ai-header-info">
              <span className="ai-header-avatar" aria-hidden="true">🛟</span>
              <div><strong id="ai-chat-title">{copy.title}</strong><span className="ai-header-status">{copy.status}</span></div>
            </div>
            <button type="button" className="ai-chat-close" onClick={() => setIsOpen(false)} aria-label="Close assistant">✕</button>
          </div>

          <div className="ai-context-strip">
            <span>Dashboard: <strong>{context.riskLabel}</strong></span>
            <span>{context.alertCount} alert(s) · {context.shelterCount} facilities</span>
          </div>

          <div className="ai-chat-body">
            <div className="ai-messages-list">
              {messages.map((message, index) => (
                <div key={`${message.sender}-${index}`} className={`ai-message-wrap ${message.sender}`}>
                  <div className={`ai-message-bubble ${message.sender}`}>{message.text}</div>
                  {message.source && <small className="ai-message-source">{message.source}</small>}
                  {message.emergency && <div className="ai-inline-contacts">{CONTACTS.map((contact) => <a key={contact.number} href={contact.href}>{contact.label} <strong>{contact.number}</strong></a>)}</div>}
                </div>
              ))}
            </div>
            <div className="ai-quick-faq-section">
              <span className="faq-section-title">{copy.quick}</span>
              <div className="faq-chips-list">
                {copy.quickQuestions.map((question) => (
                  <button key={question} type="button" className="ai-faq-chip" onClick={() => sendMessage(question)}>{question}</button>
                ))}
              </div>
            </div>
          </div>

          <form className="ai-chat-input-form" onSubmit={(event) => { event.preventDefault(); sendMessage(userQuery) }}>
            <input className="ai-chat-input" type="text" placeholder={copy.placeholder} value={userQuery} onChange={(event) => setUserQuery(event.target.value)} aria-label="Safety assistant question" />
            <button type="submit" className="ai-chat-send-btn" disabled={!userQuery.trim()}>{copy.send}</button>
          </form>
        </div>
      )}
    </>
  )
}
