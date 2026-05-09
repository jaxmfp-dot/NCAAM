import { useState, useEffect } from 'react'
import Sidebar from './components/Layout/Sidebar'
import DashboardTab from './components/Dashboard/DashboardTab'
import GoalsTab from './components/Goals/GoalsTab'
import FitnessTab from './components/Fitness/FitnessTab'
import WhoopTab from './components/WHOOP/WhoopTab'
import OverseerTab from './components/Overseer/OverseerTab'
import { useLocalStorage } from './hooks/useLocalStorage'

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [whoopConfig, setWhoopConfig] = useLocalStorage('os_whoop_config', {
    connected: false, accessToken: null, refreshToken: null, expiresAt: null,
    clientId: '', clientSecret: '',
    data: { recovery: null, sleep: null, strain: null },
    lastSync: null,
  })

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    if (code) {
      window.history.replaceState({}, '', window.location.pathname)
      setActiveTab('whoop')
      setWhoopConfig(prev => ({ ...prev, _pendingCode: code }))
    }
  }, [])

  const tabs = {
    dashboard: <DashboardTab />,
    goals:     <GoalsTab />,
    fitness:   <FitnessTab />,
    whoop:     <WhoopTab whoopConfig={whoopConfig} setWhoopConfig={setWhoopConfig} />,
    overseer:  <OverseerTab whoopData={whoopConfig.data} />,
  }

  return (
    <div className="flex h-screen bg-[#070711] text-[#f8fafc] overflow-hidden">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 overflow-y-auto min-w-0">
        {tabs[activeTab]}
      </main>
    </div>
  )
}
