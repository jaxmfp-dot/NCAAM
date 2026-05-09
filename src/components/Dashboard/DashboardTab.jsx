import { useLocalStorage } from '../../hooks/useLocalStorage'
import NetWorthTracker from './NetWorthTracker'
import SubscriptionManager from './SubscriptionManager'
import OrdersTracker from './OrdersTracker'
import { DollarSign, CreditCard, Package, TrendingUp, TrendingDown } from 'lucide-react'

export default function DashboardTab() {
  const [netWorth]      = useLocalStorage('os_networth', { assets: [], liabilities: [] })
  const [subscriptions] = useLocalStorage('os_subscriptions', [])
  const [orders]        = useLocalStorage('os_orders', [])

  const totalAssets      = (netWorth.assets || []).reduce((s, a) => s + (a.value || 0), 0)
  const totalLiabilities = (netWorth.liabilities || []).reduce((s, l) => s + (l.value || 0), 0)
  const nw               = totalAssets - totalLiabilities

  const monthlyBurn = subscriptions.reduce((s, sub) => {
    if (sub.cycle === 'annual') return s + sub.cost / 12
    if (sub.cycle === 'weekly') return s + sub.cost * 4.33
    return s + (sub.cost || 0)
  }, 0)

  const activeOrders  = orders.filter(o => ['pending', 'in-progress'].includes(o.status))
  const revenuePipeline = activeOrders.reduce((s, o) => s + (o.revenue || 0), 0)
  const businesses    = [...new Set(orders.map(o => o.business))].filter(Boolean)

  return (
    <div className="tab-content space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
        </p>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Net Worth</span>
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${nw >= 0 ? 'bg-emerald-900/40' : 'bg-red-900/40'}`}>
              {nw >= 0 ? <TrendingUp size={16} className="text-emerald-400" /> : <TrendingDown size={16} className="text-red-400" />}
            </div>
          </div>
          <div className={`stat-value ${nw >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {nw < 0 ? '-' : ''}${Math.abs(nw).toLocaleString()}
          </div>
          <div className="text-xs text-slate-600">
            Assets ${totalAssets.toLocaleString()} · Liab ${totalLiabilities.toLocaleString()}
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Monthly Burn</span>
            <div className="w-8 h-8 rounded-lg bg-amber-900/40 flex items-center justify-center">
              <CreditCard size={16} className="text-amber-400" />
            </div>
          </div>
          <div className="stat-value text-amber-400">${monthlyBurn.toFixed(0)}/mo</div>
          <div className="text-xs text-slate-600">{subscriptions.length} subscriptions</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Revenue Pipeline</span>
            <div className="w-8 h-8 rounded-lg bg-blue-900/40 flex items-center justify-center">
              <Package size={16} className="text-blue-400" />
            </div>
          </div>
          <div className="stat-value text-blue-400">${revenuePipeline.toLocaleString()}</div>
          <div className="text-xs text-slate-600">
            {activeOrders.length} active orders · {businesses.length} {businesses.length === 1 ? 'business' : 'businesses'}
          </div>
        </div>
      </div>

      {/* Main panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <NetWorthTracker />
        <SubscriptionManager />
        <OrdersTracker />
      </div>
    </div>
  )
}
