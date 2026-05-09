import { useState } from 'react'
import { useLocalStorage } from '../../hooks/useLocalStorage'
import { Plus, X, TrendingUp, TrendingDown, ChevronDown, ChevronUp, Edit2, Check } from 'lucide-react'

const ASSET_CATEGORIES = ['Cash', 'Investments', 'Real Estate', 'Crypto', 'Business Equity', 'Vehicle', 'Other']
const LIABILITY_CATEGORIES = ['Mortgage', 'Auto Loan', 'Student Loan', 'Credit Card', 'Personal Loan', 'Other']

function EntryRow({ item, onDelete, onEdit }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(item.value)

  const save = () => {
    onEdit(item.id, parseFloat(value) || 0)
    setEditing(false)
  }

  return (
    <div className="flex items-center justify-between py-2 border-b border-[#1e1e3f]/50 last:border-0 group">
      <div>
        <div className="text-sm text-slate-300">{item.name}</div>
        <div className="text-xs text-slate-600">{item.category}</div>
      </div>
      <div className="flex items-center gap-2">
        {editing ? (
          <>
            <span className="text-slate-500 text-sm">$</span>
            <input
              type="number"
              value={value}
              onChange={e => setValue(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && save()}
              className="input w-28 text-right text-sm py-1"
              autoFocus
            />
            <button onClick={save} className="btn-icon text-emerald-400"><Check size={14} /></button>
          </>
        ) : (
          <>
            <span className="text-sm font-mono text-slate-200">${(item.value || 0).toLocaleString()}</span>
            <button onClick={() => setEditing(true)} className="btn-icon opacity-0 group-hover:opacity-100"><Edit2 size={12} /></button>
            <button onClick={() => onDelete(item.id)} className="btn-icon opacity-0 group-hover:opacity-100 text-red-500"><X size={14} /></button>
          </>
        )}
      </div>
    </div>
  )
}

function AddForm({ categories, type, onAdd, onClose }) {
  const [name, setName] = useState('')
  const [category, setCategory] = useState(categories[0])
  const [value, setValue] = useState('')

  const submit = () => {
    if (!name.trim() || !value) return
    onAdd({ id: `${type}_${Date.now()}`, name: name.trim(), category, value: parseFloat(value) || 0 })
    onClose()
  }

  return (
    <div className="mt-3 p-3 bg-[#070711] rounded-lg border border-[#1e1e3f] space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="label">Name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Fidelity Brokerage" className="input text-sm" />
        </div>
        <div>
          <label className="label">Category</label>
          <select value={category} onChange={e => setCategory(e.target.value)} className="select text-sm">
            {categories.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>
      </div>
      <div>
        <label className="label">Value ($)</label>
        <input type="number" value={value} onChange={e => setValue(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          placeholder="0" className="input text-sm" />
      </div>
      <div className="flex gap-2">
        <button onClick={submit} className="btn-primary text-xs py-1.5">Add</button>
        <button onClick={onClose} className="btn-secondary text-xs py-1.5">Cancel</button>
      </div>
    </div>
  )
}

export default function NetWorthTracker() {
  const [data, setData] = useLocalStorage('os_networth', { assets: [], liabilities: [] })
  const [showAddAsset, setShowAddAsset] = useState(false)
  const [showAddLiab, setShowAddLiab] = useState(false)
  const [assetsOpen, setAssetsOpen] = useState(true)
  const [liabsOpen, setLiabsOpen]   = useState(true)

  const totalAssets = (data.assets || []).reduce((s, a) => s + (a.value || 0), 0)
  const totalLiabs  = (data.liabilities || []).reduce((s, l) => s + (l.value || 0), 0)
  const netWorth    = totalAssets - totalLiabs

  const addAsset = (item) => setData(d => ({ ...d, assets: [...(d.assets || []), item] }))
  const addLiab  = (item) => setData(d => ({ ...d, liabilities: [...(d.liabilities || []), item] }))

  const deleteAsset = (id) => setData(d => ({ ...d, assets: (d.assets || []).filter(a => a.id !== id) }))
  const deleteLiab  = (id) => setData(d => ({ ...d, liabilities: (d.liabilities || []).filter(l => l.id !== id) }))

  const editAsset = (id, value) => setData(d => ({ ...d, assets: (d.assets || []).map(a => a.id === id ? { ...a, value } : a) }))
  const editLiab  = (id, value) => setData(d => ({ ...d, liabilities: (d.liabilities || []).map(l => l.id === id ? { ...l, value } : l) }))

  return (
    <div className="card space-y-4 h-fit">
      <div className="flex items-center justify-between">
        <h2 className="section-title">Net Worth</h2>
        <div className={`text-lg font-bold font-mono ${netWorth >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {netWorth < 0 ? '-' : ''}${Math.abs(netWorth).toLocaleString()}
        </div>
      </div>

      {/* Assets */}
      <div>
        <button
          onClick={() => setAssetsOpen(o => !o)}
          className="w-full flex items-center justify-between text-sm font-medium text-emerald-400 hover:text-emerald-300 transition-colors mb-2"
        >
          <span className="flex items-center gap-1.5">
            <TrendingUp size={14} /> Assets · ${totalAssets.toLocaleString()}
          </span>
          {assetsOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        {assetsOpen && (
          <>
            {(data.assets || []).length === 0 && (
              <p className="text-xs text-slate-600 py-2">No assets yet.</p>
            )}
            {(data.assets || []).map(a => (
              <EntryRow key={a.id} item={a} onDelete={deleteAsset} onEdit={editAsset} />
            ))}
            {showAddAsset
              ? <AddForm categories={ASSET_CATEGORIES} type="asset" onAdd={addAsset} onClose={() => setShowAddAsset(false)} />
              : <button onClick={() => setShowAddAsset(true)} className="btn-ghost text-xs mt-2 px-0"><Plus size={12} /> Add asset</button>
            }
          </>
        )}
      </div>

      <div className="border-t border-[#1e1e3f]" />

      {/* Liabilities */}
      <div>
        <button
          onClick={() => setLiabsOpen(o => !o)}
          className="w-full flex items-center justify-between text-sm font-medium text-red-400 hover:text-red-300 transition-colors mb-2"
        >
          <span className="flex items-center gap-1.5">
            <TrendingDown size={14} /> Liabilities · ${totalLiabs.toLocaleString()}
          </span>
          {liabsOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        {liabsOpen && (
          <>
            {(data.liabilities || []).length === 0 && (
              <p className="text-xs text-slate-600 py-2">No liabilities yet.</p>
            )}
            {(data.liabilities || []).map(l => (
              <EntryRow key={l.id} item={l} onDelete={deleteLiab} onEdit={editLiab} />
            ))}
            {showAddLiab
              ? <AddForm categories={LIABILITY_CATEGORIES} type="liab" onAdd={addLiab} onClose={() => setShowAddLiab(false)} />
              : <button onClick={() => setShowAddLiab(true)} className="btn-ghost text-xs mt-2 px-0"><Plus size={12} /> Add liability</button>
            }
          </>
        )}
      </div>
    </div>
  )
}
