import React, { useState } from 'react'

const QUICK_QUESTIONS = [
  {
    q: 'Why does Hyderabad show MODEL_UNSUPPORTED?',
    a: 'SafeMap AI enforces a strict 50.0 km model coverage safeguard. The machine learning model is trained on official INDOFLOODS river gauges. The nearest calibrated gauge to Hyderabad is INDOFLOODS-gauge-916 at 71.8 km (River Manjra). To prevent unvalidated extrapolation and data fabrication, automated predictions are intentionally suppressed for Hyderabad.'
  },
  {
    q: 'How is the evacuation route calculated?',
    a: 'Evacuation routes are computed using Dijkstra shortest path over a real OpenStreetMap drive graph for Hyderabad. If primary roads intersect flooded hazard zones, the system recalculates a detour (HAZARDS_AVOIDED). If all access links are submerged, it returns NO_SAFE_ROUTE. Note: water depth and road closures are unmodelled on static graphs.'
  },
  {
    q: 'What should I do if trapped by rising floodwater?',
    a: '1. Never walk or drive through moving water (just 15 cm can sweep you off your feet). 2. Turn off your home electricity mains and gas cylinders. 3. Move to the top floor or terrace with drinking water and a flashlight. 4. Call GHMC DRF at 040-21111111 or National Emergency 112.'
  },
  {
    q: 'Are the shelters and hospital beds verified?',
    a: 'No. SafeMap AI strictly adheres to truth-in-facilities invariants. Shelter locations are imported from open municipal surveys, but live structural safety ratings and bed occupancies remain PUBLIC_UNVERIFIED unless officially confirmed by health authorities.'
  }
]

export default function AIAssistantChat() {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedFaq, setSelectedFaq] = useState(null)
  const [userQuery, setUserQuery] = useState('')
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: 'Hello! I am your SafeMap AI Emergency Decision Assistant. How can I help you navigate flood risks, evacuation routes, or safety protocols today?'
    }
  ])

  const handleSend = (e) => {
    e.preventDefault()
    if (!userQuery.trim()) return

    const query = userQuery.trim()
    const newMessages = [...messages, { sender: 'user', text: query }]
    setUserQuery('')

    // Generate intelligent grounded response
    const lower = query.toLowerCase()
    let reply = 'SafeMap AI is an academic prototype for Hyderabad flood decision support. Please refer to official directives from GHMC and NDMA in live emergencies.'

    if (lower.includes('unsupported') || lower.includes('model') || lower.includes('gauge') || lower.includes('50 km')) {
      reply = 'Automated ML inference requires a calibrated INDOFLOODS river gauge within 50 km. Hyderabad is 71.8 km from the nearest station (gauge-916), so predictions are suppressed to avoid fabricated numbers.'
    } else if (lower.includes('route') || lower.includes('evac') || lower.includes('escape') || lower.includes('car')) {
      reply = 'Evacuation routes are computed on the OpenStreetMap road graph. If a road is flooded, a detour is calculated. Remember: unmonitored roads are not guaranteed flood-free!'
    } else if (lower.includes('sos') || lower.includes('help') || lower.includes('call') || lower.includes('number')) {
      reply = 'Emergency Hotlines: Dial 112 for All-in-One Emergency, 040-21111111 for GHMC Disaster Response Force (DRF), 108 for Ambulance, and 100 for Police.'
    } else if (lower.includes('shelter') || lower.includes('hospital') || lower.includes('bed')) {
      reply = 'Facility locations are from municipal directories. Operational status and capacities are PUBLIC_UNVERIFIED. Always call ahead if possible.'
    }

    setMessages([...newMessages, { sender: 'bot', text: reply }])
  }

  return (
    <>
      {/* Floating Action Button */}
      <button 
        type="button" 
        className="ai-chat-floating-btn" 
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Open AI Safety Assistant"
      >
        <span className="ai-btn-avatar" aria-hidden="true">🤖</span>
        <span className="ai-btn-text">AI Safety Assistant</span>
      </button>

      {/* Chat Drawer / Modal */}
      {isOpen && (
        <div className="ai-chat-window" role="dialog" aria-labelledby="ai-chat-title">
          <div className="ai-chat-header">
            <div className="ai-header-info">
              <span className="ai-header-avatar">🤖</span>
              <div>
                <strong id="ai-chat-title">SafeMap AI Assistant</strong>
                <span className="ai-header-status">Online · Decision Guidance</span>
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

          <div className="ai-chat-body">
            <div className="ai-messages-list">
              {messages.map((m, idx) => (
                <div key={idx} className={`ai-message-bubble ${m.sender}`}>
                  {m.text}
                </div>
              ))}
            </div>

            {/* Quick Suggested Questions */}
            <div className="ai-faq-section">
              <span className="faq-title">Frequently Asked Questions</span>
              <div className="faq-chips-wrap">
                {QUICK_QUESTIONS.map((faq, i) => (
                  <button 
                    key={i} 
                    type="button" 
                    className="faq-chip-btn"
                    onClick={() => {
                      setMessages(prev => [
                        ...prev, 
                        { sender: 'user', text: faq.q },
                        { sender: 'bot', text: faq.a }
                      ])
                    }}
                  >
                    {faq.q}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <form className="ai-chat-footer" onSubmit={handleSend}>
            <input 
              type="text" 
              placeholder="Ask about flood risks, routes, or contacts..." 
              value={userQuery}
              onChange={(e) => setUserQuery(e.target.value)}
              aria-label="Chat query"
            />
            <button type="submit" className="ai-send-btn" disabled={!userQuery.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
    </>
  )
}
