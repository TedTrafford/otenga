import React from 'react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'

export default function Layout({ children, topBarProps = {} }) {
  return (
    <div className="flex h-screen bg-space-mesh overflow-hidden">
      {/* Ambient background orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="orb orb-cyan w-96 h-96 top-0 right-0 opacity-40" />
        <div className="orb orb-violet w-80 h-80 bottom-20 left-20 opacity-30" />
        <div className="orb orb-mint w-64 h-64 top-1/2 right-1/3 opacity-20" />
      </div>

      <Sidebar />

      <div className="flex flex-col flex-1 min-w-0 relative z-10">
        <TopBar {...topBarProps} />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
