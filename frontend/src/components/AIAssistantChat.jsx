import React, { useState, useEffect, useRef } from 'react'

const SUGGESTED_QUESTIONS = {
  en: [
    'I am near the Musi River and water is rising. What should I do?',
    'Is this location in a mapped flood-prone zone?',
    'Find an available evacuation route.',
    'Where is the nearest listed shelter?',
    'The route says NO_SAFE_ROUTE. What should I do?',
    'What does MODEL_UNSUPPORTED mean?',
    'How do I report a blocked road?',
    'What should I do if floodwater enters my house?'
  ],
  te: [
    'మూసీ నది వద్ద నీరు పెరుగుతుంది, ఏమి చేయాలి?',
    'మా ప్రాంతం వరద ప్రమాద జోన్‌లో ఉందా?',
    'సురక్షితమైన తరలింపు మార్గం చూపించు',
    'NO_SAFE_ROUTE అంటే ఏమి చేయాలి?',
    'సమీపంలోని సురక్షిత ఆశ్రయం ఎక్కడ ఉంది?',
    'ఇంట్లోకి వరద నీరు చేరితే ఏమి చేయాలి?'
  ],
  hi: [
    'मूसी नदी के पास जलस्तर बढ़ रहा है, क्या करूँ?',
    'क्या यह स्थान बाढ़-प्रवण क्षेत्र में है?',
    'सुरक्षित निकासी मार्ग खोजें',
    'NO_SAFE_ROUTE दिखने पर क्या करें?',
    'निकटतम राहत आश्रय कहाँ है?',
    'घर में पानी घुसने पर क्या करना चाहिए?'
  ]
}

export default function AIAssistantChat({
  location,
  locationStatus,
  hazardWarning,
  route,
  isSevereWeather = false,
  isDemoMode = false,
  selectedFacility,
  facilities = [],
  alerts = [],
  language = 'en',
  apiBaseUrl = 'http://127.0.0.1:8000',
  onNavigateToTab
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [userQuery, setUserQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastQuery, setLastQuery] = useState('')
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: language === 'te' 
        ? 'నమస్కారం! నేను మీ సేఫ్‌మ్యాప్ AI వరద భద్రతా సహాయకుడిని. వరద ప్రమాదాలు, మార్గాలు లేదా అత్యవసర రక్షణపై మీకు ఎలా సహాయపడగలను?'
        : language === 'hi'
          ? 'नमस्ते! मैं आपका सेफमैप एआई बाढ़ सुरक्षा सहायक हूँ। बाढ़ जोखिम, निकासी मार्ग या सुरक्षा नियमों के संबंध में मैं आपकी क्या सहायता कर सकता हूँ?'
          : 'Hello! I am your SafeMap AI Flood Safety Assistant. How can I help you navigate Hyderabad flood risks, evacuation routes, or emergency protocols today?',
      provider: 'SAFETY_DECISION_ENGINE_FALLBACK',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ])

  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isLoading, isOpen])

  const sendQuery = async (queryText) => {
    const text = (queryText || userQuery).trim()
    if (!text || isLoading) return

    setError('')
    setLastQuery(text)
    setUserQuery('')

    const userMsg = {
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)

    const payload = {
      message: text,
      language: language || 'en',
      context: {
        location: location ? { latitude: location.latitude, longitude: location.longitude } : null,
        location_status: locationStatus || null,
        is_in_hazard_zone: hazardWarning?.is_in_hazard_zone || false,
        hazard_names: hazardWarning?.intersected_hazards?.map((h) => h.title) || [],
        highest_severity: hazardWarning?.highest_severity || 'NONE',
        route_status: route?.route_status || null,
        route_distance_km: route?.route_distance_km || null,
        is_severe_weather: isSevereWeather,
        is_demo_mode: isDemoMode,
        nearest_shelter_name: selectedFacility?.name || facilities[0]?.name || null,
        nearest_shelter_distance_km: selectedFacility?.distance_km || null,
        active_alerts_count: alerts.length || 0
      }
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 8000)

    try {
      const response = await fetch(`${apiBaseUrl}/assistant/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      })
      clearTimeout(timeoutId)

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}))
        throw new Error(errJson.detail || `Server returned ${response.status}`)
      }

      const data = await response.json()
      setMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: data.reply,
          is_emergency: data.is_emergency,
          provider: data.provider,
          suggested_actions: data.suggested_actions || [],
          follow_up_question: data.follow_up_question || null,
          data_disclaimer: data.data_disclaimer || null,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ])
    } catch (err) {
      clearTimeout(timeoutId)
      const isTimeout = err.name === 'AbortError'
      const errMsg = isTimeout
        ? 'Request timed out after 8s. Checking local safety fallback...'
        : (err.message || 'Network connection failed')
      setError(errMsg)

      // Reliable offline fallback response to safeguard user
      setMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: '⚠️ Network connection to the server was delayed. In an immediate life-safety emergency, never wait for an app response: Immediately dial National Emergency 112 or GHMC DRF 040-21111111. Move to high ground and avoid all flooded roadways.',
          is_emergency: true,
          provider: 'SAFETY_DECISION_ENGINE_FALLBACK',
          suggested_actions: ['Call 112 Emergency', 'Call GHMC DRF (040-21111111)'],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleActionClick = (action) => {
    if (action.includes('112')) {
      window.open('tel:112', '_self')
    } else if (action.includes('040-21111111') || action.includes('GHMC')) {
      window.open('tel:04021111111', '_self')
    } else if (action.includes('Route') || action.includes('Detour')) {
      onNavigateToTab?.('routes')
    } else if (action.includes('Map') || action.includes('Polygon') || action.includes('Location')) {
      onNavigateToTab?.('map')
    } else if (action.includes('Shelter') || action.includes('Directory')) {
      onNavigateToTab?.('directory')
    } else if (action.includes('Report') || action.includes('Incident')) {
      onNavigateToTab?.('incidents')
    } else {
      sendQuery(action)
    }
  }

  const activeQuestions = SUGGESTED_QUESTIONS[language] || SUGGESTED_QUESTIONS.en

  return (
    <>
      {/* Floating Action Button */}
      <button
        type="button"
        id="ai-assistant-floating-btn"
        className="ai-chat-floating-btn"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? 'Close AI Safety Assistant' : 'Open AI Safety Assistant'}
        aria-expanded={isOpen}
      >
        <span className="ai-btn-avatar" aria-hidden="true">🤖</span>
        <span className="ai-btn-text">
          {language === 'te' ? 'AI భద్రతా సహాయకుడు' : language === 'hi' ? 'AI सुरक्षा सहायक' : 'AI Safety Assistant'}
        </span>
      </button>

      {/* Chat Drawer / Window */}
      {isOpen && (
        <div 
          className="ai-chat-window" 
          role="dialog" 
          aria-labelledby="ai-chat-title"
          aria-modal="false"
        >
          <div className="ai-chat-header">
            <div className="ai-header-info">
              <span className="ai-header-avatar" aria-hidden="true">🤖</span>
              <div>
                <strong id="ai-chat-title">
                  {language === 'te' ? 'సేఫ్‌మ్యాప్ AI సహాయకుడు' : language === 'hi' ? 'सेफमैप एआई सहायक' : 'SafeMap AI Assistant'}
                </strong>
                <span className="ai-header-status">
                  <span className="status-online-dot" />
                  {isDemoMode ? 'Online · Demo Simulation' : 'Online · Decision Support'}
                </span>
              </div>
            </div>
            <button
              type="button"
              className="ai-chat-close"
              onClick={() => setIsOpen(false)}
              aria-label="Close assistant"
            >
              ✕
            </button>
          </div>

          <div className="ai-chat-body" tabIndex={0} aria-label="Conversation history">
            <div className="ai-messages-list">
              {messages.map((m, idx) => (
                <div key={idx} className={`ai-message-bubble ${m.sender} ${m.is_emergency ? 'emergency' : ''}`}>
                  {m.is_emergency && (
                    <div className="ai-danger-alert-box">
                      <span className="alert-flare" aria-hidden="true">🚨</span>
                      <strong>CRITICAL SAFETY ALERT</strong>
                    </div>
                  )}

                  <div className="ai-message-text" style={{ whiteSpace: 'pre-line' }}>
                    {m.text}
                  </div>

                  {m.follow_up_question && (
                    <div className="ai-follow-up-box">
                      <span className="follow-up-icon" aria-hidden="true">💡</span>
                      <em>{m.follow_up_question}</em>
                    </div>
                  )}

                  {m.suggested_actions && m.suggested_actions.length > 0 && (
                    <div className="ai-actions-wrap">
                      {m.suggested_actions.map((act, i) => (
                        <button
                          key={i}
                          type="button"
                          className={`ai-action-btn ${act.includes('112') || act.includes('GHMC') ? 'emergency' : ''}`}
                          onClick={() => handleActionClick(act)}
                        >
                          {act.includes('112') ? '📞 ' : act.includes('Route') ? '🚗 ' : act.includes('Map') ? '🗺️ ' : '👉 '}
                          {act}
                        </button>
                      ))}
                    </div>
                  )}

                  {m.provider && (
                    <div className="ai-provider-meta">
                      <span className="provider-badge">
                        {m.provider === 'SAFETY_DECISION_ENGINE_FALLBACK'
                          ? '⚡ Safety Decision Engine (Offline Safe)'
                          : `✨ Model: ${m.provider}`}
                      </span>
                      <span className="message-time">{m.timestamp}</span>
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="ai-message-bubble bot loading">
                  <div className="ai-loading-dots">
                    <span className="dot" />
                    <span className="dot" />
                    <span className="dot" />
                  </div>
                  <span className="loading-caption">Evaluating Hyderabad flood telemetry...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {error && (
              <div className="ai-chat-error-bar" role="alert">
                <span>⚠️ {error}</span>
                {lastQuery && (
                  <button type="button" className="retry-btn" onClick={() => sendQuery(lastQuery)}>
                    Retry
                  </button>
                )}
              </div>
            )}

            {/* Quick Suggested Questions */}
            <div className="ai-quick-faq-section">
              <span className="faq-section-title">
                {language === 'te' ? 'తరచుగా అడిగే ప్రశ్నలు (FAQ)' : language === 'hi' ? 'अक्सर पूछे जाने वाले प्रश्न' : 'Suggested Flood Questions'}
              </span>
              <div className="faq-chips-list">
                {activeQuestions.map((q, i) => (
                  <button
                    key={i}
                    type="button"
                    className="ai-faq-chip"
                    onClick={() => sendQuery(q)}
                    disabled={isLoading}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <form
            className="ai-chat-input-form"
            onSubmit={(e) => {
              e.preventDefault()
              sendQuery()
            }}
          >
            <input
              type="text"
              className="ai-chat-input"
              placeholder={
                language === 'te'
                  ? 'వరదలు, మార్గాలు లేదా ఆశ్రయాల గురించి అడగండి...'
                  : language === 'hi'
                    ? 'बाढ़, मार्गों या आश्रयों के बारे में पूछें...'
                    : 'Ask about flood zones, routes, or safety...'
              }
              value={userQuery}
              onChange={(e) => setUserQuery(e.target.value)}
              disabled={isLoading}
              maxLength={1200}
              aria-label="Ask flood safety assistant"
            />
            <button
              type="submit"
              className="ai-chat-send-btn"
              disabled={!userQuery.trim() || isLoading}
              aria-label="Send message"
            >
              {isLoading ? '...' : 'Send'}
            </button>
          </form>
        </div>
      )}
    </>
  )
}
