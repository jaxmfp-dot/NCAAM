export function todayStr() {
  return new Date().toISOString().split('T')[0]
}

export function isCompletedToday(goal) {
  return (goal.completions || []).includes(todayStr())
}

export function calculateUrgencyScore(goal) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  let score = goal.baseUrgency || 5

  const categoryMultiplier = { business: 1.3, health: 1.15, personal: 1.0 }
  score *= categoryMultiplier[goal.category] || 1.0

  if (goal.dueDate) {
    const due = new Date(goal.dueDate)
    due.setHours(0, 0, 0, 0)
    const daysUntilDue = Math.round((due - today) / 86400000)

    if (daysUntilDue < 0) score += Math.min(12, Math.abs(daysUntilDue) * 1.5)
    else if (daysUntilDue === 0) score += 8
    else if (daysUntilDue <= 2) score += 6
    else if (daysUntilDue <= 7) score += 3
    else if (daysUntilDue <= 14) score += 1
  }

  if (isCompletedToday(goal)) score *= 0.1

  return Math.round(Math.min(25, score) * 10) / 10
}

export function getUrgencyLevel(score) {
  if (score >= 15) return 'critical'
  if (score >= 10) return 'high'
  if (score >= 5)  return 'medium'
  return 'low'
}

export function getUrgencyColor(score) {
  if (score >= 15) return 'text-red-400'
  if (score >= 10) return 'text-orange-400'
  if (score >= 5)  return 'text-amber-400'
  return 'text-slate-500'
}

export function calculateStreak(completions) {
  if (!completions || completions.length === 0) return { current: 0, best: 0 }

  const sorted = [...new Set(completions)].sort((a, b) => b.localeCompare(a))

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  const todayS = today.toISOString().split('T')[0]
  const yesterdayS = yesterday.toISOString().split('T')[0]

  let currentStreak = 0
  let startFrom = sorted[0] === todayS || sorted[0] === yesterdayS ? sorted[0] : null

  if (startFrom) {
    let checkDate = new Date(startFrom)
    checkDate.setHours(0, 0, 0, 0)

    for (const comp of sorted) {
      const checkStr = checkDate.toISOString().split('T')[0]
      if (comp === checkStr) {
        currentStreak++
        checkDate.setDate(checkDate.getDate() - 1)
      } else {
        break
      }
    }
  }

  let bestStreak = 0
  let runningStreak = 1
  for (let i = 1; i < sorted.length; i++) {
    const prev = new Date(sorted[i - 1])
    const curr = new Date(sorted[i])
    const diff = Math.round((prev - curr) / 86400000)
    if (diff === 1) {
      runningStreak++
      bestStreak = Math.max(bestStreak, runningStreak)
    } else {
      runningStreak = 1
    }
  }
  bestStreak = Math.max(bestStreak, currentStreak, sorted.length > 0 ? 1 : 0)

  return { current: currentStreak, best: bestStreak }
}

export function sortGoalsByUrgency(goals) {
  return [...goals].sort((a, b) => calculateUrgencyScore(b) - calculateUrgencyScore(a))
}

export function generateGoalId() {
  return `goal_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
}
