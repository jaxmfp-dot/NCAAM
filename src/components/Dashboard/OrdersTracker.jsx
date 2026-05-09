import { useState } from 'react'
import { useLocalStorage } from '../../hooks/useLocalStorage'
import { Plus, X, Package, CheckCircle, Clock, Truck, XCircle, Building2 } from 'lucide-react'

const STATUSES = ['pending', 'in-progress', 'shipped', 'delivered', 'cancelled']

const STATUS_CONFIG = {
  'pending':    { color: 'text-amber-400',  bg: 'bg-amber-900/30',  border: 'border-amber-800/40',  icon: Clock,        label: 'Pending' },
  'in-progress':{ color: 'text-blue-400',   bg: 'bg-blue-900/30',   border: 'border-blue-800/40',   icon: Package,      label: 'In Progress' },
  'shipped':    { color: 'text-violet-400', bg: 'bg-violet-900/30', border: 'border-violet-800/40', icon: Truck,        label: 'Shipped' },
  'delivered':  { color: 'text-emerald-400',bg: 'bg-emerald-900/30',border: 'border-emerald-800/40',icon: CheckCircle,  label: 'Delivered' },
  'cancelled':  { color: 'text-slate-500',  bg: 'bg-slate-900/30',  border: 'border-slate-800/40',  icon: XCircle,      label: 'Cancelled' },
}

export default function OrdersTracker() {
  const [orders, setOrders] = useLocalStorage('os_orders', [])
  const [showForm, setShowForm] = useState(false)
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterBusiness, setFilterBusiness] = useState('all')
  const [form, setForm] = useState({ business: '', customer: '', description: '', status: 'pending', revenue: '', dueDate: '' })

  const businesses = ['all', ...new Set(orders.map(o => o.business).filter(Boolean))]

  const addOrder = () => {
    if (!form.business.trim()) return
    setOrders(prev => [...prev, {
      ...form,
      id: `order_${Date.now()}`,
      revenue: parseFloat(form.revenue) || 0,
      createdAt: new Date().toISOString(),
    }])
    setForm({ business: '', customer: '', description: '', status: 'pending', revenue: '', dueDate: '' })
    setShowForm(false)
  }

  const deleteOrder = (id) => setOrders(prev => prev.filter(o => o.id !== id))
  const updateStatus = (id, status) => setOrders(prev => prev.map(o => o.id === id ? { ...o, status } : o))

  const filtered = orders.filter(o => {
    const matchStatus   = filterStatus === 'all' || o.status === filterStatus
    const matchBusiness = filterBusiness === 'all' || o.business === filterBusiness
    return matchStatus && matchBusiness
  })

  const groupedByBusiness = filtered.reduce((acc, o) => {
    const key = o.business || 'Unnamed'
    if (!acc[key]) acc[key] = []
    acc[key].push(o)
    return acc
  }, {})

  const pipeline = orders
    .filter(o => ['pending', 'in-progress', 'shipped'].includes(o.status))
    .reduce((s, o) => s + (o.revenue || 0), 0)

  return (
    <div className="card space-y-4 h-fit">
      <div className="flex items-center justify-between">
        <h2 className="section-title">Orders</h2>
        <button onClick={() => setShowForm(s => !s)} className="btn-icon"><Plus size={16} /></button>
      </div>

      <div className="flex items-center justify-between p-3 bg-blue-900/20 rounded-lg border border-blue-900/30">
        <div>
          <div className="text-xs text-blue-500 uppercase tracking-wider font-medium">Pipeline</div>
          <div className="text-xl font-bold font-mono text-blue-400">${pipeline.toLocaleString()}</div>
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-600">Total orders</div>
          <div className="text-sm font-mono text-slate-400">{orders.length}</div>
        </div>
      </div>

      {showForm && (
        <div className="p-3 bg-[#070711] rounded-lg border border-[#1e1e3f] space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="label">Business</label>
              <input value={form.business} onChange={e => setForm(f => ({ ...f, business: e.target.value }))}
                placeholder="Acme Corp" className="input text-sm" list="business-list" />
              <datalist id="business-list">
                {[...new Set(orders.map(o => o.business))].filter(Boolean).map(b => <option key={b} value={b} />)}
              </datalist>
            </div>
            <div>
              <label className="label">Customer</label>
              <input value={form.customer} onChange={e => setForm(f => ({ ...f, customer: e.target.value }))}
                placeholder="Customer name" className="input text-sm" />
            </div>
          </div>
          <div>
            <label className="label">Description</label>
            <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Order details" className="input text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="label">Revenue ($)</label>
              <input type="number" value={form.revenue} onChange={e => setForm(f => ({ ...f, revenue: e.target.value }))}
                placeholder="0.00" className="input text-sm" />
            </div>
            <div>
              <label className="label">Status</label>
              <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))} className="select text-sm">
                {STATUSES.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="label">Due Date (optional)</label>
            <input type="date" value={form.dueDate} onChange={e => setForm(f => ({ ...f, dueDate: e.target.value }))} className="input text-sm" />
          </div>
          <div className="flex gap-2">
            <button onClick={addOrder} className="btn-primary text-xs py-1.5">Add Order</button>
            <button onClick={() => setShowForm(false)} className="btn-secondary text-xs py-1.5">Cancel</button>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-1 flex-wrap">
        {['all', ...STATUSES].map(s => (
          <button key={s} onClick={() => setFilterStatus(s)}
            className={`text-xs px-2 py-0.5 rounded-full border transition-colors capitalize ${filterStatus === s ? 'bg-blue-900/50 border-blue-700 text-blue-300' : 'border-[#1e1e3f] text-slate-600 hover:text-slate-400'}`}>
            {s === 'all' ? 'All' : s}
          </button>
        ))}
      </div>

      {businesses.length > 2 && (
        <div className="flex gap-1 flex-wrap">
          {businesses.map(b => (
            <button key={b} onClick={() => setFilterBusiness(b)}
              className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${filterBusiness === b ? 'bg-violet-900/50 border-violet-700 text-violet-300' : 'border-[#1e1e3f] text-slate-600 hover:text-slate-400'}`}>
              {b === 'all' ? 'All Businesses' : b}
            </button>
          ))}
        </div>
      )}

      <div className="space-y-3">
        {Object.keys(groupedByBusiness).length === 0 && (
          <p className="text-xs text-slate-600 py-2">No orders yet. Add one above.</p>
        )}
        {Object.entries(groupedByBusiness).map(([business, bizOrders]) => (
          <div key={business}>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Building2 size={12} className="text-slate-600" />
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{business}</span>
            </div>
            <div className="space-y-1.5">
              {bizOrders.map(order => {
                const cfg = STATUS_CONFIG[order.status] || STATUS_CONFIG.pending
                const Icon = cfg.icon
                const isOverdue = order.dueDate && new Date(order.dueDate) < new Date() && order.status !== 'delivered'
                return (
                  <div key={order.id} className={`p-2.5 rounded-lg ${cfg.bg} border ${cfg.border} group`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <Icon size={12} className={cfg.color} />
                          <span className="text-sm text-slate-200 truncate">{order.customer || 'Unknown Customer'}</span>
                          {isOverdue && <span className="text-xs text-red-400">overdue</span>}
                        </div>
                        {order.description && (
                          <div className="text-xs text-slate-600 mt-0.5 truncate">{order.description}</div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {order.revenue > 0 && (
                          <span className="text-sm font-mono text-emerald-400">${order.revenue.toLocaleString()}</span>
                        )}
                        <select
                          value={order.status}
                          onChange={e => updateStatus(order.id, e.target.value)}
                          className="text-xs bg-transparent border-0 outline-none cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={e => e.stopPropagation()}
                        >
                          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                        <button onClick={() => deleteOrder(order.id)} className="btn-icon opacity-0 group-hover:opacity-100 text-red-500">
                          <X size={12} />
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className={`badge ${cfg.bg} ${cfg.color} border ${cfg.border}`}>{cfg.label}</span>
                      {order.dueDate && (
                        <span className="text-xs text-slate-600">
                          due {new Date(order.dueDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                      )}
                      <span className="text-xs text-slate-700 ml-auto">
                        {new Date(order.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
