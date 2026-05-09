import { useState } from 'react'
import { useLocalStorage } from '../../hooks/useLocalStorage'
import { Plus, X, CreditCard, AlertCircle } from 'lucide-react'

const CYCLES = ['monthly', 'annual', 'weekly']
const CATEGORIES = ['Software', 'Media', 'Health', 'Finance', 'Business', 'Utilities', 'Other']

function toMonthly(cost, cycle) {
  if (cycle === 'annual') return cost / 12
  if (cycle === 'weekly') return cost * 4.33
  return cost
}

const CYCLE_COLORS = {
  monthly: 'text-blue-400',
  annual:  'text-violet-400',
  weekly:  'text-amber-400',
}

export default function SubscriptionManager() {
  const [subs, setSubs] = useLocalStorage('os_subscriptions', [])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', cost: '', cycle: 'monthly', category: 'Software', nextBilling: '', notes: '' })
  const [filter, setFilter] = useState('All')

  const totalBurn = subs.reduce((s, sub) => s + toMonthly(sub.cost, sub.cycle), 0)

  const addSub = () => {
    if (!form.name.trim() || !form.cost) return
    setSubs(prev => [...prev, { ...form, id: `sub_${Date.now()}`, cost: parseFloat(form.cost) }])
    setForm({ name: '', cost: '', cycle: 'monthly', category: 'Software', nextBilling: '', notes: '' })
    setShowForm(false)
  }

  const deleteSub = (id) => setSubs(prev => prev.filter(s => s.id !== id))

  const allCategories = ['All', ...new Set(subs.map(s => s.category))]
  const filtered = filter === 'All' ? subs : subs.filter(s => s.category === filter)

  const annualCost = totalBurn * 12

  return (
    <div className="card space-y-4 h-fit">
      <div className="flex items-center justify-between">
        <h2 className="section-title">Subscriptions</h2>
        <button onClick={() => setShowForm(s => !s)} className="btn-icon">
          <Plus size={16} />
        </button>
      </div>

      <div className="flex items-center justify-between p-3 bg-amber-900/20 rounded-lg border border-amber-900/30">
        <div>
          <div className="text-xs text-amber-500 uppercase tracking-wider font-medium">Monthly Burn</div>
          <div className="text-xl font-bold font-mono text-amber-400">${totalBurn.toFixed(2)}</div>
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-600">Annual</div>
          <div className="text-sm font-mono text-slate-400">${annualCost.toFixed(0)}</div>
        </div>
      </div>

      {showForm && (
        <div className="p-3 bg-[#070711] rounded-lg border border-[#1e1e3f] space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="label">Service Name</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="Netflix" className="input text-sm" />
            </div>
            <div>
              <label className="label">Category</label>
              <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} className="select text-sm">
                {CATEGORIES.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="label">Cost ($)</label>
              <input type="number" value={form.cost} onChange={e => setForm(f => ({ ...f, cost: e.target.value }))}
                placeholder="0.00" className="input text-sm" />
            </div>
            <div>
              <label className="label">Billing Cycle</label>
              <select value={form.cycle} onChange={e => setForm(f => ({ ...f, cycle: e.target.value }))} className="select text-sm">
                {CYCLES.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="label">Next Billing (optional)</label>
            <input type="date" value={form.nextBilling} onChange={e => setForm(f => ({ ...f, nextBilling: e.target.value }))} className="input text-sm" />
          </div>
          <div className="flex gap-2">
            <button onClick={addSub} className="btn-primary text-xs py-1.5">Add</button>
            <button onClick={() => setShowForm(false)} className="btn-secondary text-xs py-1.5">Cancel</button>
          </div>
        </div>
      )}

      {allCategories.length > 2 && (
        <div className="flex gap-1 flex-wrap">
          {allCategories.map(c => (
            <button key={c} onClick={() => setFilter(c)}
              className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${filter === c ? 'bg-violet-900/50 border-violet-700 text-violet-300' : 'border-[#1e1e3f] text-slate-600 hover:text-slate-400'}`}>
              {c}
            </button>
          ))}
        </div>
      )}

      <div className="space-y-1.5">
        {filtered.length === 0 && (
          <p className="text-xs text-slate-600 py-2">No subscriptions yet. Add one above.</p>
        )}
        {filtered.map(sub => {
          const monthly = toMonthly(sub.cost, sub.cycle)
          const pct = totalBurn > 0 ? (monthly / totalBurn) * 100 : 0
          const isOverdue = sub.nextBilling && new Date(sub.nextBilling) < new Date()
          return (
            <div key={sub.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-[#0a0a16] hover:bg-[#111125] transition-colors group">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm text-slate-200 truncate">{sub.name}</span>
                  {isOverdue && <AlertCircle size={12} className="text-amber-400 flex-shrink-0" />}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-slate-600">{sub.category}</span>
                  <span className={`text-xs ${CYCLE_COLORS[sub.cycle] || 'text-slate-500'}`}>{sub.cycle}</span>
                  {sub.nextBilling && (
                    <span className="text-xs text-slate-700">renews {new Date(sub.nextBilling).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                  )}
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-sm font-mono text-slate-200">${monthly.toFixed(2)}<span className="text-slate-600">/mo</span></div>
                {sub.cycle !== 'monthly' && (
                  <div className="text-xs text-slate-600">${sub.cost}/{sub.cycle === 'annual' ? 'yr' : 'wk'}</div>
                )}
              </div>
              <button onClick={() => deleteSub(sub.id)} className="btn-icon opacity-0 group-hover:opacity-100 text-red-500 flex-shrink-0">
                <X size={14} />
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
