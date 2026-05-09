const WHOOP_AUTH_URL  = 'https://api.prod.whoop.com/oauth/oauth2/auth'
const WHOOP_TOKEN_URL = 'https://api.prod.whoop.com/oauth/oauth2/token'
const WHOOP_API_BASE  = 'https://api.prod.whoop.com/developer/v1'
const WHOOP_SCOPE = 'read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement'

export function buildAuthURL(clientId, redirectUri) {
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: 'code',
    scope: WHOOP_SCOPE,
  })
  return `${WHOOP_AUTH_URL}?${params.toString()}`
}

export async function exchangeCodeForToken(code, clientId, clientSecret, redirectUri) {
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    client_id: clientId,
    client_secret: clientSecret,
    redirect_uri: redirectUri,
  })

  const res = await fetch(WHOOP_TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  })

  if (!res.ok) throw new Error(`Token exchange failed: ${res.status}`)
  return res.json()
}

export async function refreshToken(refreshTok, clientId, clientSecret) {
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: refreshTok,
    client_id: clientId,
    client_secret: clientSecret,
    scope: WHOOP_SCOPE,
  })

  const res = await fetch(WHOOP_TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  })

  if (!res.ok) throw new Error(`Token refresh failed: ${res.status}`)
  return res.json()
}

async function whoopFetch(path, accessToken) {
  const res = await fetch(`${WHOOP_API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) throw new Error(`WHOOP API error: ${res.status} ${path}`)
  return res.json()
}

export async function fetchWhoopData(accessToken) {
  const [cycleRes, recoveryRes, sleepRes] = await Promise.allSettled([
    whoopFetch('/cycle?limit=1', accessToken),
    whoopFetch('/recovery?limit=1', accessToken),
    whoopFetch('/sleep?limit=1', accessToken),
  ])

  const recovery = recoveryRes.status === 'fulfilled'
    ? recoveryRes.value?.records?.[0] : null
  const sleep = sleepRes.status === 'fulfilled'
    ? sleepRes.value?.records?.[0] : null
  const cycle = cycleRes.status === 'fulfilled'
    ? cycleRes.value?.records?.[0] : null

  return {
    recovery: recovery ? {
      score:      recovery.score?.recovery_score ?? null,
      hrv:        recovery.score?.hrv_rmssd_milli ?? null,
      restingHR:  recovery.score?.resting_heart_rate ?? null,
      bloodOxygen: recovery.score?.spo2_percentage ?? null,
    } : null,
    sleep: sleep ? {
      performancePercent: sleep.score?.sleep_performance_percentage ?? null,
      totalSleepMs:       sleep.score?.stage_summary?.total_light_sleep_time_milli +
                          sleep.score?.stage_summary?.total_slow_wave_sleep_time_milli +
                          sleep.score?.stage_summary?.total_rem_sleep_time_milli ?? null,
      remMs:              sleep.score?.stage_summary?.total_rem_sleep_time_milli ?? null,
      disturbances:       sleep.score?.disturbances ?? null,
    } : null,
    strain: cycle ? {
      score:      cycle.score?.strain ?? null,
      kilojoule:  cycle.score?.kilojoule ?? null,
    } : null,
  }
}

export function getRecoveryRecommendation(score) {
  if (score === null || score === undefined) return { label: 'No Data', color: 'text-slate-500', icon: '—', desc: 'Sync WHOOP to get your recommendation.' }
  if (score >= 67) return {
    label: 'Train Hard',
    color: 'text-emerald-400',
    icon: '🟢',
    desc: score >= 84
      ? 'Peak performance window. Push intensity and tackle deep work.'
      : 'Green zone. High-intensity training and focused work sessions recommended.',
  }
  if (score >= 34) return {
    label: 'Maintain',
    color: 'text-amber-400',
    icon: '🟡',
    desc: 'Yellow zone. Moderate activity. Listen to your body.',
  }
  return {
    label: 'Recover',
    color: 'text-red-400',
    icon: '🔴',
    desc: 'Red zone. Prioritize sleep, nutrition, and light movement only.',
  }
}

export function formatSleepDuration(ms) {
  if (!ms) return 'N/A'
  const hours = Math.floor(ms / 3600000)
  const mins  = Math.floor((ms % 3600000) / 60000)
  return `${hours}h ${mins}m`
}

export function getRecoveryRingColor(score) {
  if (score === null || score === undefined) return '#475569'
  if (score >= 67) return '#10b981'
  if (score >= 34) return '#f59e0b'
  return '#ef4444'
}
