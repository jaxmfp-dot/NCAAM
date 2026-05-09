import { useState } from 'react'
import { useLocalStorage } from '../../hooks/useLocalStorage'
import {
  Plus, X, Check, Flame, Target, ChevronDown, ChevronUp,
  Calendar, RotateCcw, Trophy, Filter, Zap
} from 'lucide-react'
import {
  calculateUrgencyScore, getUrgencyLevel, getUrgencyColor,
  calculateStreak, isCompletedToday, sortGoalsByUrgency,
  generateGoalId, todayStr
} from '../../utils/goals'

const CATEGORIES = ['business', 'health', 'personal']
const CAT_BADGE = { business: 'badge-business', health: 'badge-health', personal: 'badge-personal' }
const CAT_ICONS = { business: '💼', health: '💪', personal: '⭐' }

const URGENCY_BORDER = {
  low:      'urgency-low',
  medium:   'urgency-medium',
  high:     'urgency-high',
  critical: 'urgency-critical',
}

function GoalCard({ goal, onComplete, onDelete, onSkip }) {
  const [expanded, setExpanded] = useState(false)
  const score    = calculateUrgencyScore(goal)
  const level    = getUrgencyLevel(score)
  const streak   = calculateStreak(goal.completions)
  const done     = isCompletedToday(goal)

  const completionsThisWeek = (goal.completions || []).filter(d => {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - 7)
    return new Date(d) >= cutoff
  }).length

  return (
    <div className={`card ${URGENCY_BORDER[level]} transition-all group ${done ? 'opacity-60' : ''}`}>
      <div className="flex items-start gap-3">
        <button
          onClick={() => !done && onComplete(goal.id)}
          className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all
            ${done ? 'bg-emerald-600 border-emerald-600' : 'border-slate-600 hover:border-emerald-500'}`}
        >
          {done && <Check size={11} strokeWidth={3} className="text-white" />}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-medium ${done ? 'line-through text-slate-500' : 'text-slate-100'}`}>
              {goal.title}
            </span>
            <span className={CAT_BADGE[goal.category]}>
              {CAT_ICONS[goal.category]} {goal.category}
            </span>
            {goal.isRecurring && (
              <span className="badge bg-slate-800 text-slate-500 border border-slate-700">
                <RotateCcw size={9} /> recurring
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <span className={`text-xs font-medium ${getUrgencyColor(score)}`}>
              <Zap size={10} className="inline" /> {score.toFixed(1)} urgency
            </span>
            {streak.current > 0 && (
              <span className="text-xs text-orange-400 font-medium">
                <Flame size={11} className="inline" /> {streak.current} day streak
              </span>
            )}
            {streak.best > 1 && (
              <span className="text-xs text-slate-600">best: {streak.best}</span>
            )}
            {goal.dueDate && (
              <span className="text-xs text-slate-600">
                <Calendar size={10} className="inline" /> {new Date(goal.dueDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </span>
            )}
            <span className="text-xs text-slate-700">{completionsThisWeek}× this week</span>
          </div>

          {goal.notes && expanded && (
            <p className="text-xs text-slate-500 mt-2 italic">{goal.notes}</p>
          )}
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {goal.notes && (
            <button onClick={() => setExpanded(e => !e)} className="btn-icon text-slate-600">
              {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}
          <button onClick={() => onDelete(goal.id)} className="btn-icon opacity-0 group-hover:opacity-100 text-red-500">
            <X size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

function AddGoalForm({ onAdd, onClose }) {
  const [form, setForm] = useState({
    title: '', category: 'business', baseUrgency: 5,
    dueDate: '', notes: '', isRecurring: false,
  })

  const submit = () => {
    if (!form.title.trim()) return
    onAdd({
      ...form,
      id: generateGoalId(),
      baseUrgency: parseInt(form.baseUrgency),
      completions: [],
      createdAt: new Date().toISOString(),
    })
    onClose()
  }

  return (
    <div className="card border-violet-900/50 space-y-3">
      <h3 className="text-sm font-semibold text-slate-200">Add Goal</h3>
      <div>
        <label className="label">Goal</label>
        <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
          onKeyDown={e => e.key === 'Enter' && submit()}
          placeholder="What do you want to accomplish?" className="input" autoFocus />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Category</label>
          <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} className="select">
            {CATEGORIES.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Base Urgency (1–10)</label>
          <input type="range" min={1} max={10} value={form.baseUrgency}
            onChange={e => setForm(f => ({ ...f, baseUrgency: e.target.value }))}
            className="w-full mt-1 accent-violet-600" />
          <div className="text-xs text-slate-500 text-center">{form.baseUrgency}</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Due Date (optional)</label>
          <input type="date" value={form.dueDate} onChange={e => setForm(f => ({ ...f, dueDate: e.target.value }))} className="input" />
        </div>
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.isRecurring}
              onChange={e => setForm(f => ({ ...f, isRecurring: e.target.checked }))}
              className="accent-violet-600 w-4 h-4" />
            <span className="text-sm text-slate-400">Recurring daily</span>
          </label>
        </div>
      </div>
      <div>
        <label className="label">Notes (optional)</label>
        <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
          placeholder="Additional context..." className="input resize-none" rows={2} />
      </div>
      <div className="flex gap-2">
        <button onClick={submit} className="btn-primary">Add Goal</button>
        <button onClick={onClose} className="btn-secondary">Cancel</button>
      </div>
    </div>
  )
}

export default function GoalsTab() {
  const [goals, setGoals] = useLocalStorage('os_goals', [])
  const [showForm, setShowForm] = useState(false)
  const [filterCat, setFilterCat] = useState('all')
  const [showCompleted, setShowCompleted] = useState(false)

  const addGoal = (goal) => setGoals(prev => [...prev, goal])

  const completeGoal = (id) => {
    const today = todayStr()
    setGoals(prev => prev.map(g => {
      if (g.id !== id) return g
      const completions = g.completions || []
      if (completions.includes(today)) return g
      return { ...g, completions: [...completions, today] }
    }))
  }

  const deleteGoal = (id) => setGoals(prev => prev.filter(g => g.id !== id))

  const filteredGoals = goals.filter(g => filterCat === 'all' || g.category === filterCat)
  const sorted = sortGoalsByUrgency(filteredGoals)
  const pending   = sorted.filter(g => !isCompletedToday(g))
  const completed = sorted.filter(g => isCompletedToday(g))

  const totalDone   = goals.filter(g => isCompletedToday(g)).length
  const topStreaks  = [...goals].sort((a, b) => calculateStreak(b.completions).current - calculateStreak(a.completions).current).slice(0, 3)
  const criticalCount = goals.filter(g => getUrgencyLevel(calculateUrgencyScore(g)) === 'critical').length

  return (
    <div className="tab-content space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Goals</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <button onClick={() => setShowForm(s => !s)} className="btn-primary">
          <Plus size={16} /> Add Goal
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="stat-card">
          <div className="stat-label">Completed Today</div>
          <div className="stat-value text-emerald-400">{totalDone}/{goals.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Critical</div>
          <div className={`stat-value ${criticalCount > 0 ? 'text-red-400' : 'text-slate-500'}`}>{criticalCount}</div>
        </div>
        <div className="stat-card col-span-2">
          <div className="stat-label">Top Streaks</div>
          <div className="flex gap-3 mt-1">
            {topStreaks.map(g => {
              const s = calculateStreak(g.completions)
              return s.current > 0 ? (
                <div key={g.id} className="text-xs">
                  <span className="text-orange-400 font-bold"><Flame size={10} className="inline" /> {s.current}</span>
                  <span className="text-slate-600 ml-1 truncate">{g.title.split(' ').slice(0, 2).join(' ')}</span>
                </div>
              ) : null
            })}
            {topStreaks.every(g => calculateStreak(g.completions).current === 0) && (
              <span className="text-xs text-slate-600">Complete goals to build streaks</span>
            )}
          </div>
        </div>
      </div>

      {showForm && <AddGoalForm onAdd={addGoal} onClose={() => setShowForm(false)} />}

      {/* Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={13} className="text-slate-600" />
        {['all', ...CATEGORIES].map(c => (
          <button key={c} onClick={() => setFilterCat(c)}
            className={`text-xs px-3 py-1 rounded-full border transition-colors capitalize ${filterCat === c ? 'bg-violet-900/50 border-violet-700 text-violet-300' : 'border-[#1e1e3f] text-slate-600 hover:text-slate-400'}`}>
            {CAT_ICONS[c] || ''} {c}
          </button>
        ))}
      </div>

      {/* Pending goals */}
      {pending.length === 0 && completed.length === 0 && (
        <div className="card text-center py-12">
          <Target size={32} className="mx-auto text-slate-700 mb-3" />
          <p className="text-slate-500 text-sm">No goals yet. Add your first goal above.</p>
        </div>
      )}

      {pending.length === 0 && completed.length > 0 && (
        <div className="card text-center py-8 border-emerald-900/40">
          <Trophy size={28} className="mx-auto text-emerald-500 mb-2" />
          <p className="text-emerald-400 font-semibold">All goals complete for today! 🔥</p>
        </div>
      )}

      <div className="space-y-3">
        {pending.map(goal => (
          <GoalCard key={goal.id} goal={goal} onComplete={completeGoal} onDelete={deleteGoal} />
        ))}
      </div>

      {/* Completed today */}
      {completed.length > 0 && (
        <div>
          <button
            onClick={() => setShowCompleted(s => !s)}
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors mb-3"
          >
            {showCompleted ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            Completed today ({completed.length})
          </button>
          {showCompleted && (
            <div className="space-y-3">
              {completed.map(goal => (
                <GoalCard key={goal.id} goal={goal} onComplete={completeGoal} onDelete={deleteGoal} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
