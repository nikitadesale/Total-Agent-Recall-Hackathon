import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import './App.css'

const API = 'http://localhost:8000'

const PRIORITY_COLOR = { high: '#ef4444', medium: '#f59e0b', low: '#10b981' }

const QUICK_PROMPTS = [
  "Should I order DoorDash tonight?",
  "Is now a good time to book an Uber?",
  "What subscriptions am I wasting money on?",
  "How's my health budget looking today?",
  "Am I on track with my goals this week?",
  "Should I go to the gym today?",
]

// ── Markdown renderer ─────────────────────────────────────────────────────────
function renderMarkdown(text) {
  const lines = text.split('\n')
  const elements = []
  let listItems = []

  const flushList = () => {
    if (listItems.length) {
      elements.push(<ul key={`ul-${elements.length}`}>{listItems}</ul>)
      listItems = []
    }
  }

  lines.forEach((line, i) => {
    const trimmed = line.trim()
    if (!trimmed) { flushList(); elements.push(<br key={i} />); return }

    // Bullet line
    if (/^[-•*]\s/.test(trimmed)) {
      const content = trimmed.replace(/^[-•*]\s/, '')
      listItems.push(<li key={i}>{inlineMd(content)}</li>)
      return
    }

    flushList()

    // Heading-like bold line (entire line is bold)
    if (/^\*\*[^*]+\*\*:?$/.test(trimmed)) {
      const content = trimmed.replace(/^\*\*/, '').replace(/\*\*:?$/, '')
      elements.push(<p key={i} className="md-heading">{content}</p>)
      return
    }

    elements.push(<p key={i}>{inlineMd(trimmed)}</p>)
  })

  flushList()
  return elements
}

function inlineMd(text) {
  // **bold**
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((part, i) =>
    /^\*\*[^*]+\*\*$/.test(part)
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : part
  )
}

// ── Text-to-Speech ────────────────────────────────────────────────────────────
function speak(text) {
  window.speechSynthesis.cancel()
  const clean = text.replace(/\*\*/g, '').replace(/\n/g, ' ')
  const utt = new SpeechSynthesisUtterance(clean)
  utt.rate  = 0.95
  utt.pitch = 1.0
  // prefer a natural-sounding voice
  const voices = window.speechSynthesis.getVoices()
  const preferred = voices.find(v => /samantha|karen|moira|daniel|google/i.test(v.name))
  if (preferred) utt.voice = preferred
  window.speechSynthesis.speak(utt)
}

function stopSpeaking() { window.speechSynthesis.cancel() }

// ── Logo ──────────────────────────────────────────────────────────────────────
function Logo() {
  return (
    <div className="logo">
      <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
        <rect width="36" height="36" rx="10" fill="#0f172a" stroke="#1e3a5f" strokeWidth="1.5"/>
        <path d="M18 9C12.477 9 8 13 8 18C8 23 12.477 27 18 27C23.523 27 28 23 28 18C28 13 23.523 9 18 9Z"
          fill="none" stroke="#38bdf8" strokeWidth="1.4" strokeLinecap="round"/>
        <ellipse cx="18" cy="18" rx="4" ry="4" fill="#38bdf8" opacity="0.9"/>
        <ellipse cx="18" cy="18" rx="1.8" ry="1.8" fill="#0f172a"/>
        <path d="M8 18 C11 14, 25 14, 28 18" stroke="#38bdf8" strokeWidth="1" opacity="0.4" strokeLinecap="round"/>
        <path d="M8 18 C11 22, 25 22, 28 18" stroke="#38bdf8" strokeWidth="1" opacity="0.4" strokeLinecap="round"/>
      </svg>
      <div>
        <span className="logo-title">Sentinel Twin</span>
        <span className="logo-sub">Privacy-First Digital Twin</span>
      </div>
    </div>
  )
}

// ── Message bubble ────────────────────────────────────────────────────────────
function Message({ msg, isLast }) {
  const [speaking, setSpeaking] = useState(false)

  const toggleAudio = useCallback(() => {
    if (speaking) { stopSpeaking(); setSpeaking(false) }
    else { speak(msg.content); setSpeaking(true) }
  }, [speaking, msg.content])

  useEffect(() => {
    const interval = setInterval(() => {
      if (!window.speechSynthesis.speaking) setSpeaking(false)
    }, 500)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className={`msg ${msg.role}`}>
      {msg.role === 'assistant' && (
        <div className="avatar">
          <svg width="18" height="18" viewBox="0 0 36 36" fill="none">
            <path d="M18 6C10.8 6 5 11.4 5 18s5.8 12 13 12 13-5.4 13-12S25.2 6 18 6z" fill="none" stroke="#38bdf8" strokeWidth="2"/>
            <ellipse cx="18" cy="18" rx="4.5" ry="4.5" fill="#38bdf8"/>
            <ellipse cx="18" cy="18" rx="2" ry="2" fill="#0f172a"/>
          </svg>
        </div>
      )}
      <div className="bubble">
        <div className="bubble-text">
          {msg.role === 'assistant' ? renderMarkdown(msg.content) : msg.content}
        </div>
        {msg.role === 'assistant' && (
          <div className="bubble-footer">
            {msg.meta?.memory_hit && <span className="badge memory">🧠 memory</span>}
            <button className={`tts-btn ${speaking ? 'speaking' : ''}`} onClick={toggleAudio} title={speaking ? 'Stop' : 'Listen'}>
              {speaking
                ? <><span className="tts-bar"/><span className="tts-bar"/><span className="tts-bar"/></>
                : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
              }
            </button>
          </div>
        )}
      </div>
      {msg.role === 'user' && <div className="avatar user-avatar">You</div>}
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [messages, setMessages]   = useState([
    { role: 'assistant', content: "Hey — I'm your Sentinel Twin. I have a live view of your finances, health, transport, habits, and calendar.\n\nWhat decision can I help you with today?" }
  ])
  const [input, setInput]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [vault, setVault]         = useState(null)
  const [insights, setInsights]   = useState([])
  const [activeTab, setActiveTab] = useState('insights')
  const bottomRef = useRef(null)

  useEffect(() => { loadVault(); loadInsights() }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  async function loadVault() {
    try { const { data } = await axios.get(`${API}/vault/status`); setVault(data) }
    catch {}
  }
  async function loadInsights() {
    try { const { data } = await axios.get(`${API}/insights`); setInsights(data.insights || []) }
    catch {}
  }

  async function sendMessage(text) {
    if (!text.trim() || loading) return
    const userMsg = { role: 'user', content: text }
    const history = [...messages, userMsg]
    setMessages(history)
    setInput('')
    setLoading(true)
    try {
      const { data } = await axios.post(`${API}/chat`, {
        messages: history.filter(m => m.role !== 'system'),
        include_vault: true,
      })
      const reply = { role: 'assistant', content: data.reply, meta: data }
      setMessages(prev => [...prev, reply])
      loadVault(); loadInsights()
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Could not reach Sentinel Twin API. Is the server running on port 8000?' }])
    } finally { setLoading(false) }
  }

  const vaultDomains = vault ? [
    { icon: '💰', label: 'Finance',       entries: [['Remaining today', `$${vault.finance?.remaining_budget}`], ['Spent today', `$${vault.finance?.spent_today}`], ['Status', vault.finance?.liquidity_status]] },
    { icon: '🥗', label: 'Health',        entries: [['Kcal remaining', vault.health?.remaining_calories], ['Allergens', vault.health?.known_allergens?.join(', ') || 'none'], ['Diet', vault.health?.dietary_profile]] },
    { icon: '🚗', label: 'Transport',     entries: [['Surge now', `${vault.transport?.current_surge}x`], ['Drop in', `${vault.transport?.surge_drop_in_mins} min`], ['Ride budget left', `$${vault.transport?.remaining_ride_budget}`]] },
    { icon: '📱', label: 'Subscriptions', entries: [['Monthly waste', `$${vault.subscriptions?.monthly_waste}`], ['Score', vault.subscriptions?.waste_score], ['Unused', vault.subscriptions?.unused_apps?.join(', ') || 'none']] },
    { icon: '🏃', label: 'Habits',        entries: [['Steps today', `${vault.habits?.steps_today} / ${vault.habits?.steps_goal}`], ['Sleep debt', `${vault.habits?.sleep_debt_hours}h`], ['DoorDash/wk', vault.habits?.doordash_this_week]] },
    { icon: '📅', label: 'Calendar',      entries: [['Today', vault.calendar?.today], ['Mtgs tomorrow', vault.calendar?.work_meetings_tomorrow], ['Social/wk', vault.calendar?.social_events_this_week]] },
  ] : []

  return (
    <div className="app">
      <header className="header">
        <Logo />
        <div className="header-stats">
          {vault && <>
            <Stat val={`$${vault.finance?.remaining_budget}`} label="budget left" />
            <div className="stat-div"/>
            <Stat val={vault.health?.remaining_calories} label="kcal left" />
            <div className="stat-div"/>
            <Stat val={`${vault.transport?.current_surge}x`} label="uber surge"
              color={vault.transport?.current_surge > 1.4 ? '#ef4444' : '#10b981'} />
            <div className="stat-div"/>
            <Stat val={insights.filter(i => i.priority === 'high').length} label="alerts"
              color={insights.filter(i => i.priority === 'high').length > 0 ? '#f59e0b' : '#10b981'} />
          </>}
        </div>
        <div className="header-badge">LIVE</div>
      </header>

      <div className="main">
        {/* Chat */}
        <div className="chat-panel">
          <div className="messages">
            {messages.map((m, i) => <Message key={i} msg={m} isLast={i === messages.length - 1} />)}
            {loading && (
              <div className="msg assistant">
                <div className="avatar">
                  <svg width="18" height="18" viewBox="0 0 36 36" fill="none">
                    <path d="M18 6C10.8 6 5 11.4 5 18s5.8 12 13 12 13-5.4 13-12S25.2 6 18 6z" fill="none" stroke="#38bdf8" strokeWidth="2"/>
                    <ellipse cx="18" cy="18" rx="4.5" ry="4.5" fill="#38bdf8"/>
                    <ellipse cx="18" cy="18" rx="2" ry="2" fill="#0f172a"/>
                  </svg>
                </div>
                <div className="bubble"><div className="typing"><span/><span/><span/></div></div>
              </div>
            )}
            <div ref={bottomRef}/>
          </div>

          <div className="quick-prompts">
            {QUICK_PROMPTS.map((p, i) => (
              <button key={i} className="quick-btn" onClick={() => sendMessage(p)}>{p}</button>
            ))}
          </div>

          <div className="input-row">
            <input className="chat-input" value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage(input)}
              placeholder="Ask your twin anything..."
              disabled={loading}
            />
            <button className="send-btn" onClick={() => sendMessage(input)} disabled={loading || !input.trim()}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>

        {/* Dashboard */}
        <div className="right-panel">
          <div className="tabs">
            {[
              { id: 'insights', label: `Alerts`, count: insights.length },
              { id: 'vault',    label: 'Vault' },
              { id: 'memory',   label: 'Memory' },
            ].map(t => (
              <button key={t.id} className={`tab ${activeTab === t.id ? 'active' : ''}`} onClick={() => setActiveTab(t.id)}>
                {t.label}{t.count != null && <span className="tab-count">{t.count}</span>}
              </button>
            ))}
          </div>

          {activeTab === 'insights' && (
            <div className="tab-content">
              {insights.length === 0
                ? <div className="empty">All clear — you're on track ✓</div>
                : insights.map((ins, i) => (
                  <div key={i} className="insight-card" style={{borderLeftColor: PRIORITY_COLOR[ins.priority]}}>
                    <div className="ins-header">
                      <span className="ins-icon">{ins.icon}</span>
                      <div className="ins-meta">
                        <div className="ins-title">{ins.title}</div>
                        <div className="ins-domain">{ins.domain}</div>
                      </div>
                      <span className="ins-pill" style={{background: PRIORITY_COLOR[ins.priority]+'18', color: PRIORITY_COLOR[ins.priority]}}>{ins.priority}</span>
                    </div>
                    <div className="ins-body">{ins.body}</div>
                    <button className="ins-ask" onClick={() => sendMessage(ins.title)}>Ask twin →</button>
                  </div>
                ))
              }
            </div>
          )}

          {activeTab === 'vault' && (
            <div className="tab-content">
              {vaultDomains.map((d, i) => (
                <div key={i} className="vault-card">
                  <div className="vault-header">{d.icon} <span>{d.label}</span></div>
                  {d.entries.map(([k, v], j) => (
                    <div key={j} className="vault-row">
                      <span className="vk">{k}</span>
                      <span className="vv">{v ?? '—'}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'memory' && <MemoryPanel />}
        </div>
      </div>
    </div>
  )
}

function Stat({ val, label, color }) {
  return (
    <div className="stat">
      <span className="stat-val" style={color ? {color} : {}}>{val}</span>
      <span className="stat-label">{label}</span>
    </div>
  )
}

function MemoryPanel() {
  const [query, setQuery]     = useState('')
  const [result, setResult]   = useState(null)
  const [loading, setLoading] = useState(false)

  async function recall() {
    setLoading(true)
    try {
      const { data } = await axios.get(`${API}/memory/recall`, { params: { query: query || 'recent decisions' } })
      setResult(data)
    } catch {}
    finally { setLoading(false) }
  }

  return (
    <div className="tab-content">
      <p className="mem-note">Every chat and decision is stored in HydraDB. Your twin learns your patterns over time.</p>
      <div className="memory-search">
        <input className="mem-input" value={query} onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && recall()}
          placeholder="Search memories... e.g. 'food orders'"/>
        <button className="mem-btn" onClick={recall} disabled={loading}>{loading ? '…' : 'Recall'}</button>
      </div>
      {result && (
        <div className="memory-result">
          <div className="mem-label">Recalled from HydraDB</div>
          <pre className="mem-text">{result.context || 'No memories yet — start chatting!'}</pre>
        </div>
      )}
    </div>
  )
}
