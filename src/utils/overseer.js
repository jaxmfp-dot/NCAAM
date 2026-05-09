import { calculateStreak, isCompletedToday, calculateUrgencyScore } from './goals.js'
import { getPersonalRecords, calculateWeeklyVolume } from './fitness.js'

export function buildOverseerContext({ goals, workouts, whoopData, netWorth, subscriptions, orders }) {
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })

  const goalsContext = goals.map(g => {
    const streak = calculateStreak(g.completions)
    return {
      title: g.title,
      category: g.category,
      urgency: calculateUrgencyScore(g),
      completedToday: isCompletedToday(g),
      streak: streak.current,
      dueDate: g.dueDate || 'No deadline',
    }
  })

  const completedToday = goalsContext.filter(g => g.completedToday).length
  const overdueGoals = goals.filter(g => {
    if (!g.dueDate) return false
    return new Date(g.dueDate) < new Date() && !isCompletedToday(g)
  })

  const prs = getPersonalRecords(workouts)
  const weeklyVol = calculateWeeklyVolume(workouts)

  const totalAssets = (netWorth.assets || []).reduce((s, a) => s + (a.value || 0), 0)
  const totalLiabilities = (netWorth.liabilities || []).reduce((s, l) => s + (l.value || 0), 0)
  const netWorthTotal = totalAssets - totalLiabilities

  const monthlyBurn = (subscriptions || []).reduce((s, sub) => {
    if (sub.cycle === 'annual') return s + sub.cost / 12
    if (sub.cycle === 'weekly') return s + sub.cost * 4.33
    return s + (sub.cost || 0)
  }, 0)

  const pendingOrders = (orders || []).filter(o => ['pending', 'in-progress'].includes(o.status))
  const totalRevenuePipeline = pendingOrders.reduce((s, o) => s + (o.revenue || 0), 0)

  return `Today: ${today}

═══ GOALS STATUS ═══
Total goals: ${goals.length} | Completed today: ${completedToday}/${goals.length}
Overdue: ${overdueGoals.map(g => g.title).join(', ') || 'None'}
Top priority goals: ${goalsContext
  .sort((a, b) => b.urgency - a.urgency)
  .slice(0, 5)
  .map(g => `${g.title} (${g.category}, urgency: ${g.urgency.toFixed(1)}, ${g.completedToday ? '✅ done' : '⬜ pending'}, streak: ${g.streak})`)
  .join('\n  ')}

═══ FITNESS ═══
Workouts this week: ${weeklyVol.workoutCount}
Weekly volume: ${weeklyVol.totalVolume.toLocaleString()} lbs
Recent PRs: ${Object.entries(prs).slice(0, 5).map(([ex, pr]) => `${ex}: ${pr.weight}×${pr.reps} (est 1RM: ${pr.estimated1RM.toFixed(0)} lbs)`).join(', ') || 'None recorded'}

═══ WHOOP RECOVERY ═══
Recovery score: ${whoopData?.recovery?.score ?? 'N/A'}%
HRV: ${whoopData?.recovery?.hrv ? `${whoopData.recovery.hrv.toFixed(1)} ms` : 'N/A'}
Resting HR: ${whoopData?.recovery?.restingHR ?? 'N/A'} bpm
Sleep performance: ${whoopData?.sleep?.performancePercent ?? 'N/A'}%
Strain: ${whoopData?.strain?.score?.toFixed(1) ?? 'N/A'}

═══ BUSINESS / ORDERS ═══
Active orders: ${pendingOrders.length}
Revenue pipeline: $${totalRevenuePipeline.toLocaleString()}
Total orders: ${(orders || []).length}
Businesses: ${[...new Set((orders || []).map(o => o.business))].join(', ') || 'None'}

═══ FINANCES ═══
Net worth: $${netWorthTotal.toLocaleString()}
Assets: $${totalAssets.toLocaleString()} | Liabilities: $${totalLiabilities.toLocaleString()}
Monthly subscription burn: $${monthlyBurn.toFixed(2)}/mo`
}

export async function generateDailyBrief(context, apiKey) {
  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-6',
      max_tokens: 1200,
      messages: [{
        role: 'user',
        content: `You are The Overseer — an uncompromising AI accountability agent. You review all personal metrics daily and hold nothing back. You are direct, specific, and relentlessly honest. Here is today's data snapshot:

${context}

Generate a daily brief with EXACTLY this structure (use markdown headers):

## 🏆 WINS
Bullet list of what is going well. Be specific — reference actual numbers and goals.

## ⚠️ SLIPPAGE ALERTS
Bullet list of what is slipping, missed, or declining. Call it out directly. If something is overdue or underperforming, name it. No sugar-coating.

## 🎯 TODAY'S TOP 3 PRIORITIES
Numbered list of the 3 most important things to focus on today, ranked by impact.

## 📊 TRENDS & INSIGHTS
2-3 sentences on patterns you see across the data. Connect the dots.

## 💭 THE WORD
One punchy, direct sentence to carry into the day based on the data above.

Be sharp. Be honest. Be useful.`,
      }],
    }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error?.message || `API error ${response.status}`)
  }

  const data = await response.json()
  return data.content[0].text
}

export function parseMarkdownBrief(text) {
  return text
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li><span class="text-violet-400 font-bold">$1.</span> $2</li>')
    .replace(/(<li>.*<\/li>)/gs, match => `<ul>${match}</ul>`)
    .split('\n')
    .filter(line => line.trim())
    .map(line => {
      if (line.startsWith('<h') || line.startsWith('<ul') || line.startsWith('<li')) return line
      return `<p>${line}</p>`
    })
    .join('\n')
}
