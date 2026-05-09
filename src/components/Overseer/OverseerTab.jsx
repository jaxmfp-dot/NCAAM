import { useState, useEffect } from 'react'
import { Brain, RefreshCw, Key, ChevronDown, ChevronUp, AlertTriangle, Zap, Clock, Trash2 } from 'lucide-react'
import { useLocalStorage } from '../../hooks/useLocalStorage'
import { buildOverseerContext, generateDailyBrief } from '../../utils/overseer'

function BriefDisplay({ content }) {
  const sections = content.split(/(?=^## )/m).filter(Boolean)

  const getSectionStyle = (heading) => {
    if (heading.includes('WINS'))       return { border: 'border-emerald-800/40', bg: 'bg-emerald-900/10', icon: '🏆' }
    if (heading.includes('SLIPPAGE'))   return { border: 'border-red-800/40',     bg: 'bg-red-900/10',     icon: '⚠️' }
    if (heading.includes('PRIORITIES')) return { border: 'border-blue-800/40',    bg: 'bg-blue-900/10',    icon: '🎯' }
    if (heading.includes('TRENDS'))     return { border: 'border-amber-800/40',   bg: 'bg-amber-900/10',   icon: '📊' }
    if (heading.includes('WORD'))       return { border: 'border-violet-800/40',  bg: 'bg-violet-900/10',  icon: '💭' }
    return { border: 'border-[#1e1e3f]', bg: '', icon: '' }
  }

  if (sections.length <= 1) {
    return (
      <div className="prose-dark whitespace-pre-wrap text-slate-300 text-sm leading-relaxed">
        {content}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {sections.map((section, i) => {
        const lines    = section.split('\n')
        const heading  = lines[0].replace(/^##\s*/, '').trim()
        const bodyLines = lines.slice(1).filter(l => l.trim())
        const style    = getSectionStyle(heading)

        return (
          <div key={i} className={`p-4 rounded-xl border ${style.border} ${style.bg}`}>
            <h3 className="text-sm font-semibold text-slate-200 mb-2">{heading}</h3>
            <div className="space-y-1.5">
              {bodyLines.map((line, j) => {
                const isBullet = line.trim().startsWith('-') || line.trim().startsWith('•')
                const isNumbered = /^\d+\./.test(line.trim())
                const text = line.trim().replace(/^[-•]\s*/, '').replace(/^\d+\.\s*/, '')

                if (isBullet) return (
                  <div key={j} className="flex gap-2 text-sm text-slate-300">
                    <span className="text-slate-600 flex-shrink-0 mt-0.5">•</span>
                    <span dangerouslySetInnerHTML={{
                      __html: text.replace(/\*\*(.+?)\*\*/g, '<strong class="text-slate-100">$1</strong>')
                    }} />
                  </div>
                )

                if (isNumbered) {
                  const num = line.trim().match(/^(\d+)\./)?.[1]
                  return (
                    <div key={j} className="flex gap-2 text-sm text-slate-300">
                      <span className="text-violet-400 font-bold flex-shrink-0 w-5">{num}.</span>
                      <span dangerouslySetInnerHTML={{
                        __html: text.replace(/\*\*(.+?)\*\*/g, '<strong class="text-slate-100">$1</strong>')
                      }} />
                    </div>
                  )
                }

                if (!text) return null
                return (
                  <p key={j} className="text-sm text-slate-300 leading-relaxed"
                    dangerouslySetInnerHTML={{
                      __html: text.replace(/\*\*(.+?)\*\*/g, '<strong class="text-slate-100">$1</strong>')
                    }} />
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function HistoryItem({ brief, onDelete }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="card">
      <div className="flex items-center justify-between gap-3">
        <button onClick={() => setOpen(o => !o)} className="flex-1 flex items-center gap-3 text-left">
          <Clock size={14} className="text-slate-600 flex-shrink-0" />
          <div>
            <div className="text-sm text-slate-300">
              {new Date(brief.date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
            </div>
            <div className="text-xs text-slate-600 mt-0.5 truncate max-w-md">
              {brief.content.slice(0, 120)}...
            </div>
          </div>
          {open ? <ChevronUp size={14} className="text-slate-600 flex-shrink-0" /> : <ChevronDown size={14} className="text-slate-600 flex-shrink-0" />}
        </button>
        <button onClick={() => onDelete(brief.id)} className="btn-icon text-red-500 flex-shrink-0">
          <Trash2 size={14} />
        </button>
      </div>
      {open && (
        <div className="mt-4 pt-4 border-t border-[#1e1e3f]">
          <BriefDisplay content={brief.content} />
        </div>
      )}
    </div>
  )
}

export default function OverseerTab({ whoopData }) {
  const [goals]         = useLocalStorage('os_goals', [])
  const [workouts]      = useLocalStorage('os_workouts', [])
  const [netWorth]      = useLocalStorage('os_networth', { assets: [], liabilities: [] })
  const [subscriptions] = useLocalStorage('os_subscriptions', [])
  const [orders]        = useLocalStorage('os_orders', [])
  const [settings, setSettings] = useLocalStorage('os_overseer_settings', { apiKey: '', briefs: [] })

  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [showKey, setShowKey]   = useState(false)
  const [apiKey, setApiKey]     = useState(settings.apiKey || '')
  const [currentBrief, setCurrentBrief] = useState(null)

  const todayBrief = settings.briefs?.find(b => b.date.startsWith(new Date().toISOString().split('T')[0]))

  useEffect(() => {
    if (todayBrief) setCurrentBrief(todayBrief)
  }, [])

  const saveKey = () => {
    setSettings(prev => ({ ...prev, apiKey }))
    setShowKey(false)
  }

  const generateBrief = async () => {
    const key = settings.apiKey || apiKey
    if (!key) { setError('Please enter your Anthropic API key first.'); return }

    setLoading(true)
    setError('')

    try {
      const context = buildOverseerContext({ goals, workouts, whoopData, netWorth, subscriptions, orders })
      const brief   = await generateDailyBrief(context, key)

      const briefRecord = {
        id:      `brief_${Date.now()}`,
        date:    new Date().toISOString(),
        content: brief,
      }

      setCurrentBrief(briefRecord)
      setSettings(prev => ({
        ...prev,
        apiKey: key,
        briefs: [briefRecord, ...(prev.briefs || []).filter(b => !b.date.startsWith(new Date().toISOString().split('T')[0]))].slice(0, 30),
      }))
    } catch (e) {
      setError(e.message || 'Failed to generate brief. Check your API key.')
    } finally {
      setLoading(false)
    }
  }

  const deleteBrief = (id) => {
    setSettings(prev => ({ ...prev, briefs: (prev.briefs || []).filter(b => b.id !== id) }))
    if (currentBrief?.id === id) setCurrentBrief(null)
  }

  const hasData = goals.length > 0 || workouts.length > 0 || orders.length > 0

  return (
    <div className="tab-content space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">The Overseer</h1>
          <p className="text-sm text-slate-500 mt-0.5">AI accountability — powered by Claude</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowKey(s => !s)} className="btn-ghost text-sm">
            <Key size={14} /> {settings.apiKey ? 'Update Key' : 'Set API Key'}
          </button>
          <button
            onClick={generateBrief}
            disabled={loading}
            className="btn-primary"
          >
            {loading
              ? <><RefreshCw size={15} className="animate-spin" /> Analyzing...</>
              : <><Brain size={15} /> Generate Brief</>
            }
          </button>
        </div>
      </div>

      {showKey && (
        <div className="card border-violet-900/40 space-y-3">
          <div className="flex items-center gap-2">
            <Key size={14} className="text-violet-400" />
            <h3 className="text-sm font-semibold text-slate-200">Anthropic API Key</h3>
          </div>
          <p className="text-xs text-slate-500">
            Get your key at <span className="text-violet-400">console.anthropic.com</span>. Stored only in your browser's localStorage.
          </p>
          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && saveKey()}
            placeholder="sk-ant-..."
            className="input font-mono text-sm"
          />
          <div className="flex gap-2">
            <button onClick={saveKey} className="btn-primary text-sm">Save Key</button>
            <button onClick={() => setShowKey(false)} className="btn-secondary text-sm">Cancel</button>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-900/20 border border-red-900/40 rounded-lg text-sm text-red-400">
          <AlertTriangle size={14} className="flex-shrink-0" />
          {error}
        </div>
      )}

      {!hasData && !currentBrief && (
        <div className="card text-center py-16">
          <Brain size={36} className="mx-auto text-slate-700 mb-4" />
          <h3 className="text-base font-semibold text-slate-400 mb-2">No data to analyze yet</h3>
          <p className="text-sm text-slate-600 max-w-sm mx-auto">
            Add goals, log workouts, track orders, and connect WHOOP — then The Overseer will have something to work with.
          </p>
        </div>
      )}

      {!settings.apiKey && !showKey && (
        <div className="card border-amber-900/40 bg-amber-900/10 flex items-center gap-3">
          <Zap size={18} className="text-amber-400 flex-shrink-0" />
          <div>
            <div className="text-sm font-semibold text-amber-300">API Key Required</div>
            <p className="text-xs text-slate-400 mt-0.5">
              Click "Set API Key" above and enter your Anthropic API key to enable The Overseer.
            </p>
          </div>
        </div>
      )}

      {/* Current brief */}
      {currentBrief && (
        <div className="card border-violet-900/40">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-violet-500 animate-pulse" />
              <span className="text-sm font-semibold text-slate-200">
                {new Date(currentBrief.date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-600">
                {new Date(currentBrief.date).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
              </span>
              <button onClick={generateBrief} disabled={loading} className="btn-ghost text-xs py-1">
                <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Refresh
              </button>
            </div>
          </div>
          <BriefDisplay content={currentBrief.content} />
        </div>
      )}

      {/* History */}
      {(settings.briefs || []).length > 1 && (
        <div>
          <h2 className="section-title mb-3">Brief History</h2>
          <div className="space-y-2">
            {(settings.briefs || [])
              .filter(b => b.id !== currentBrief?.id)
              .slice(0, 10)
              .map(brief => (
                <HistoryItem key={brief.id} brief={brief} onDelete={deleteBrief} />
              ))}
          </div>
        </div>
      )}
    </div>
  )
}
