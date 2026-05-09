import { LayoutDashboard, Target, Dumbbell, Activity, Brain, Zap } from 'lucide-react'

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'goals',     label: 'Goals',     icon: Target },
  { id: 'fitness',   label: 'Fitness',   icon: Dumbbell },
  { id: 'whoop',     label: 'WHOOP',     icon: Activity },
  { id: 'overseer',  label: 'Overseer',  icon: Brain },
]

export default function Sidebar({ activeTab, setActiveTab }) {
  return (
    <aside className="w-[72px] flex-shrink-0 flex flex-col items-center py-5 gap-2
                      bg-[#0a0a16] border-r border-[#1e1e3f]">
      <div className="mb-4 flex flex-col items-center gap-1">
        <div className="w-9 h-9 rounded-xl bg-violet-700 flex items-center justify-center glow-purple">
          <Zap size={18} className="text-white" />
        </div>
        <span className="text-[9px] font-bold text-violet-400 tracking-widest uppercase">OS</span>
      </div>

      <nav className="flex flex-col gap-1 flex-1 w-full px-2">
        {NAV.map(({ id, label, icon: Icon }) => {
          const active = activeTab === id
          return (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              title={label}
              className={`
                w-full flex flex-col items-center gap-1 py-2.5 px-1 rounded-xl
                transition-all duration-150 border-0 cursor-pointer text-center
                ${active
                  ? 'bg-violet-900/40 text-violet-300'
                  : 'bg-transparent text-slate-600 hover:text-slate-300 hover:bg-white/5'
                }
              `}
            >
              <Icon size={20} strokeWidth={active ? 2 : 1.5} />
              <span className="text-[9px] font-medium tracking-wide">{label}</span>
            </button>
          )
        })}
      </nav>

      <div className="text-[8px] text-slate-700 font-mono tracking-widest rotate-90 mt-2">
        THE OS
      </div>
    </aside>
  )
}
