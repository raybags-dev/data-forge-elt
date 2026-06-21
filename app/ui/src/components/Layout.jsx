import React from 'react'
import { NavLink, Outlet } from 'react-router-dom'

const NAV_ITEMS = [
  { label: 'Dashboard', to: '/' },
  { label: 'Pipeline', to: '/pipeline' },
  { label: 'Crawlers', to: '/crawlers' },
  { label: 'Datasets', to: '/datasets' },
  { label: 'Logs', to: '/logs' },
]

/**
 * Main application layout: sidebar navigation + main content outlet.
 */
export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-56 flex-shrink-0 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="px-4 py-5 border-b border-slate-700">
          <h1 className="text-lg font-bold text-sky-400">DataForge ELT</h1>
          <p className="text-xs text-slate-400 mt-1">Production Dashboard</p>
        </div>
        <nav className="flex-1 px-2 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-sky-600 text-white'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-slate-700">
          <p className="text-xs text-slate-500">v1.0.0</p>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-slate-900 p-6">
        <Outlet />
      </main>
    </div>
  )
}
