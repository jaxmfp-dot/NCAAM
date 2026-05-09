import { useState, useEffect } from 'react'
import { Activity, RefreshCw, Link, Unlink, AlertTriangle, Zap, Moon, Heart, Flame, CheckCircle, Settings } from 'lucide-react'
import { buildAuthURL, exchangeCodeForToken, fetchWhoopData, getRecoveryRecommendation, formatSleepDuration, getRecoveryRingColor } from '../../utils/whoop'

const REDIRECT_URI = window.location.origin

function RecoveryRing({ score }) {
  const radius = 52
  const circumference = 2 * Math.PI * radius
  const pct = (score ?? 0) / 100
  const strokeDashoffset = circumference * (1 - pct)
  const color = getRecoveryRingColor(score)

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="132" height="132" className="-rotate-90">
        <circle cx="66" cy="66" r={radius} fill="none" stroke="#1e1e3f" strokeWidth="10" />
        <circle
          cx="66" cy="66" r={radius} fill="none"
          stroke={color} strokeWidth="10"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease, stroke 0.4s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-bold font-mono" style={{ color }}>{score ?? '—'}</span>
        <span className="text-xs text-slate-500">recovery</span>
      </div>
    </div>
  )
}

function MetricCard({ icon: Icon, label, value, unit, color = 'text-slate-300', subtext }) {
  return (
    <div className="card flex flex-col gap-1">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon size={13} className={color} />
        <span className="text-xs text-slate-600 uppercase tracking-wider font-medium">{label}</span>
      </div>
      <div className={`text-2xl font-bold font-mono ${color}`}>
        {value ?? <span className="text-slate-700">—</span>}
        {value !== null && value !== undefined && <span className="text-sm font-normal text-slate-500 ml-1">{unit}</span>}
      </div>
      {subtext && <div className="text-xs text-slate-600">{subtext}</div>}
    </div>
  )
}

export default function WhoopTab({ whoopConfig, setWhoopConfig }) {
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [showSetup, setShowSetup] = useState(false)
  const [credentials, setCredentials] = useState({
    clientId:     whoopConfig.clientId || '',
    clientSecret: whoopConfig.clientSecret || '',
  })

  const { connected, data, lastSync } = whoopConfig
  const rec   = data?.recovery
  const sleep = data?.sleep
  const strain = data?.strain

  const recommendation = getRecoveryRecommendation(rec?.score)

  useEffect(() => {
    if (whoopConfig._pendingCode && whoopConfig.clientId && whoopConfig.clientSecret) {
      handleCodeExchange(whoopConfig._pendingCode)
    }
  }, [whoopConfig._pendingCode])

  const handleCodeExchange = async (code) => {
    setLoading(true)
    setError('')
    try {
      const tokens = await exchangeCodeForToken(code, whoopConfig.clientId, whoopConfig.clientSecret, REDIRECT_URI)
      const newConfig = {
        ...whoopConfig,
        connected: true,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        expiresAt: Date.now() + tokens.expires_in * 1000,
        _pendingCode: null,
      }
      setWhoopConfig(newConfig)
      await syncData(newConfig)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const syncData = async (config = whoopConfig) => {
    if (!config.accessToken) return
    setLoading(true)
    setError('')
    try {
      const newData = await fetchWhoopData(config.accessToken)
      setWhoopConfig(prev => ({ ...prev, data: newData, lastSync: new Date().toISOString() }))
    } catch (e) {
      setError(e.message || 'Sync failed. Token may be expired.')
    } finally {
      setLoading(false)
    }
  }

  const startOAuth = () => {
    if (!credentials.clientId) { setError('Client ID is required'); return }
    setWhoopConfig(prev => ({ ...prev, clientId: credentials.clientId, clientSecret: credentials.clientSecret }))
    const url = buildAuthURL(credentials.clientId, REDIRECT_URI)
    window.open(url, '_blank', 'width=600,height=700')
  }

  const disconnect = () => {
    setWhoopConfig(prev => ({
      ...prev,
      connected: false, accessToken: null, refreshToken: null,
      data: { recovery: null, sleep: null, strain: null }, lastSync: null,
    }))
  }

  const saveManualToken = () => {
    setWhoopConfig(prev => ({
      ...prev,
      clientId: credentials.clientId,
      clientSecret: credentials.clientSecret,
    }))
    setShowSetup(false)
  }

  return (
    <div className="tab-content space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">WHOOP</h1>
          <p className="text-sm text-slate-500 mt-0.5">Recovery, sleep & strain</p>
        </div>
        <div className="flex items-center gap-2">
          {connected && (
            <button onClick={() => syncData()} disabled={loading} className="btn-secondary text-sm">
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Sync
            </button>
          )}
          <button onClick={() => setShowSetup(s => !s)} className="btn-ghost">
            <Settings size={16} />
          </button>
          {connected && (
            <button onClick={disconnect} className="btn-danger text-sm">
              <Unlink size={14} /> Disconnect
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-900/20 border border-red-900/40 rounded-lg text-sm text-red-400">
          <AlertTriangle size={14} />
          {error}
        </div>
      )}

      {showSetup && (
        <div className="card border-violet-900/40 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-200">WHOOP API Setup</h3>
            <a href="https://developer.whoop.com" target="_blank" rel="noopener" className="text-xs text-violet-400 hover:text-violet-300">
              Get credentials →
            </a>
          </div>
          <p className="text-xs text-slate-500">
            Register at developer.whoop.com and create an app with redirect URI: <code className="bg-[#1e1e3f] px-1 rounded text-slate-300">{REDIRECT_URI}</code>
          </p>
          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className="label">Client ID</label>
              <input value={credentials.clientId} onChange={e => setCredentials(c => ({ ...c, clientId: e.target.value }))}
                placeholder="your-client-id" className="input font-mono text-sm" />
            </div>
            <div>
              <label className="label">Client Secret</label>
              <input type="password" value={credentials.clientSecret} onChange={e => setCredentials(c => ({ ...c, clientSecret: e.target.value }))}
                placeholder="your-client-secret" className="input font-mono text-sm" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={startOAuth} className="btn-primary">
              <Link size={14} /> Connect WHOOP
            </button>
            <button onClick={saveManualToken} className="btn-secondary">Save Credentials</button>
          </div>
          <p className="text-xs text-slate-600">
            After clicking Connect WHOOP, authorize in the popup window. The app will detect the callback automatically.
          </p>
        </div>
      )}

      {!connected ? (
        <div className="card text-center py-16">
          <div className="w-16 h-16 rounded-full bg-[#1e1e3f] flex items-center justify-center mx-auto mb-4">
            <Activity size={28} className="text-slate-600" />
          </div>
          <h3 className="text-lg font-semibold text-slate-300 mb-2">Connect WHOOP</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto mb-6">
            Link your WHOOP account to see recovery scores, HRV, sleep performance, and get daily training recommendations.
          </p>
          <button onClick={() => setShowSetup(true)} className="btn-primary">
            <Link size={16} /> Set Up WHOOP Integration
          </button>
        </div>
      ) : (
        <>
          {lastSync && (
            <div className="flex items-center gap-1.5 text-xs text-slate-600">
              <CheckCircle size={11} className="text-emerald-600" />
              Last synced {new Date(lastSync).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </div>
          )}

          {/* Daily Recommendation */}
          <div className={`card border-2 ${
            recommendation.label === 'Train Hard' ? 'border-emerald-800/60 bg-emerald-900/10' :
            recommendation.label === 'Maintain'   ? 'border-amber-800/60 bg-amber-900/10' :
            recommendation.label === 'Recover'    ? 'border-red-800/60 bg-red-900/10' :
            'border-[#1e1e3f]'
          }`}>
            <div className="flex items-center gap-3">
              <span className="text-3xl">{recommendation.icon}</span>
              <div>
                <div className={`text-lg font-bold ${recommendation.color}`}>
                  {recommendation.label}
                </div>
                <p className="text-sm text-slate-400 mt-0.5">{recommendation.desc}</p>
              </div>
            </div>
          </div>

          {/* Recovery ring + metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="card flex flex-col items-center gap-4">
              <RecoveryRing score={rec?.score} />
              <div className="grid grid-cols-2 gap-3 w-full">
                <div className="text-center">
                  <div className="text-xs text-slate-600 mb-0.5">HRV</div>
                  <div className="text-lg font-bold font-mono text-blue-400">
                    {rec?.hrv ? rec.hrv.toFixed(1) : '—'}<span className="text-xs text-slate-500"> ms</span>
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-slate-600 mb-0.5">Resting HR</div>
                  <div className="text-lg font-bold font-mono text-red-400">
                    {rec?.restingHR ?? '—'}<span className="text-xs text-slate-500"> bpm</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3">
              <MetricCard
                icon={Moon} label="Sleep Performance"
                value={sleep?.performancePercent ? `${sleep.performancePercent.toFixed(0)}%` : null}
                color={sleep?.performancePercent >= 70 ? 'text-blue-400' : 'text-amber-400'}
                subtext={sleep?.totalSleepMs ? `${formatSleepDuration(sleep.totalSleepMs)} sleep` : null}
              />
              <MetricCard
                icon={Flame} label="Strain"
                value={strain?.score ? strain.score.toFixed(1) : null}
                color={strain?.score >= 15 ? 'text-red-400' : strain?.score >= 10 ? 'text-amber-400' : 'text-emerald-400'}
                subtext={strain?.kilojoule ? `${(strain.kilojoule / 4.184).toFixed(0)} kcal` : null}
              />
              {rec?.bloodOxygen && (
                <MetricCard
                  icon={Heart} label="SpO₂"
                  value={`${rec.bloodOxygen.toFixed(1)}%`}
                  color={rec.bloodOxygen >= 95 ? 'text-emerald-400' : 'text-amber-400'}
                />
              )}
            </div>
          </div>

          {/* Peak energy / deep work flag */}
          {rec?.score >= 80 && (
            <div className="card border-violet-800/40 bg-violet-900/10 flex items-center gap-3">
              <Zap size={20} className="text-violet-400 flex-shrink-0" />
              <div>
                <div className="text-sm font-semibold text-violet-300">⚡ Peak Energy Window</div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Recovery {rec.score}% — your body is primed. Schedule your most demanding creative or cognitive work now.
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
