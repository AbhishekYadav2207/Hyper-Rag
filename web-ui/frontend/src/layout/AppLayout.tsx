import React, { useState, useEffect, useRef } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { observer } from 'mobx-react'
import { useTranslation } from 'react-i18next'
import { storeGlobalUser } from '@/store/globalUser'

// Lucide icons
import {
  MessageSquare,
  Network,
  Database,
  FileText,
  BookOpen,
  Settings,
  ChevronLeft,
  ChevronDown,
  Check,
  RefreshCw,
  Upload,
  Search,
  Code2,
  Cpu,
  Wifi,
  WifiOff,
  HelpCircle,
} from 'lucide-react'

// Design system CSS
import '../styles/design-system.css'

/* ── Nav Items ──────────────────────────────────────────────────── */
const NAV_ITEMS = [
  {
    section: 'Workspace',
    items: [
      { path: '/Hyper/chat', label: 'Chat', icon: MessageSquare },
      { path: '/Hyper/show', label: 'Visualization', icon: Network },
      { path: '/Hyper/DB', label: 'Hypergraph DB', icon: Database },
      { path: '/Hyper/files', label: 'Documents', icon: FileText },
    ],
  },
  {
    section: 'System',
    items: [
      { path: '/API', label: 'API Docs', icon: Code2 },
      { path: '/Setting', label: 'Settings', icon: Settings },
    ],
  },
]

/* ── Database Dropdown ──────────────────────────────────────────── */
const DatabaseDropdown: React.FC = observer(() => {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const dbs = storeGlobalUser.availableDatabases
  const selected = storeGlobalUser.selectedDatabase

  const filtered = dbs.filter(
    db =>
      db.name.toLowerCase().includes(search.toLowerCase()) ||
      db.description.toLowerCase().includes(search.toLowerCase()),
  )

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
        setSearch('')
      }
    }
    if (open) {
      document.addEventListener('mousedown', handler)
    }
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const handleSelect = (name: string) => {
    storeGlobalUser.setSelectedDatabase(name)
    setOpen(false)
    setSearch('')
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await storeGlobalUser.loadDatabases()
    } finally {
      setRefreshing(false)
    }
  }

  const selectedDb = dbs.find(db => db.name === selected)
  const displayName = selectedDb?.description?.replace('Hypergraph', '').replace('Hyper-Graph', '').trim() || selected || 'Select database'

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div className="db-selector-wrapper">
        <span className="db-selector-label">Knowledge Base</span>
        <button
          className={`db-selector-trigger ${open ? 'open' : ''}`}
          onClick={() => setOpen(!open)}
          aria-label="Select knowledge base"
          aria-expanded={open}
          aria-haspopup="listbox"
        >
          <span className="db-selector-dot" />
          <span className="db-selector-name" title={displayName}>{displayName}</span>
          <ChevronDown size={12} className="db-selector-chevron" />
        </button>
      </div>

      {open && (
        <div className="db-dropdown" role="listbox" aria-label="Knowledge bases">
          {/* Search */}
          <div className="db-dropdown-search">
            <input
              autoFocus
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search databases…"
              aria-label="Search knowledge bases"
            />
          </div>

          {/* List */}
          <div className="db-dropdown-list">
            {filtered.length === 0 ? (
              <div style={{ padding: '12px 16px', fontSize: '13px', color: 'var(--text-tertiary)', textAlign: 'center' }}>
                No databases found
              </div>
            ) : (
              filtered.map(db => {
                const isSelected = db.name === selected
                const label = db.description?.replace('Hypergraph', '').replace('Hyper-Graph', '').trim() || db.name
                return (
                  <div
                    key={db.name}
                    role="option"
                    aria-selected={isSelected}
                    className={`db-dropdown-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleSelect(db.name)}
                  >
                    <Database size={14} className="db-dropdown-item-icon" />
                    <div className="db-dropdown-item-info">
                      <div className="db-dropdown-item-name">{label}</div>
                    </div>
                    <Check size={13} className="db-dropdown-item-check" />
                  </div>
                )
              })
            )}
          </div>

          {/* Footer: refresh */}
          <div className="db-dropdown-footer">
            <button
              className="btn btn-ghost btn-sm"
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw size={12} style={{ animation: refreshing ? 'spin 0.7s linear infinite' : 'none' }} />
              {refreshing ? 'Refreshing…' : 'Refresh list'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
})

/* ── API Status Badge ───────────────────────────────────────────── */
const APIStatusBadge: React.FC = () => {
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch('/databases', { signal: AbortSignal.timeout(3000) })
        setOnline(r.ok)
      } catch {
        setOnline(false)
      }
    }
    check()
    const interval = setInterval(check, 30000)
    return () => clearInterval(interval)
  }, [])

  if (online === null) return null

  return (
    <span className={`status-badge ${online ? 'online' : 'offline'}`} title={online ? 'API connected' : 'API offline'}>
      <span className="status-badge-dot" />
      {online ? 'Online' : 'Offline'}
    </span>
  )
}

/* ── App Layout ─────────────────────────────────────────────────── */
const AppLayout: React.FC = () => {
  const { t } = useTranslation()
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const pathname = location.pathname

  // Load databases on mount
  useEffect(() => {
    storeGlobalUser.restoreSelectedDatabase()
    storeGlobalUser.loadDatabases()
  }, []) // eslint-disable-line

  return (
    <div className="app-shell">
      {/* ── Sidebar ── */}
      <nav
        className={`sidebar ${collapsed ? 'collapsed' : ''}`}
        aria-label="Main navigation"
      >
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="sidebar-brand-logo" aria-hidden="true">
            <Cpu size={16} />
          </div>
          <span className="sidebar-brand-text">Hyper-RAG</span>
        </div>

        {/* Navigation */}
        <div className="sidebar-nav">
          {NAV_ITEMS.map(section => (
            <div className="sidebar-section" key={section.section}>
              <div className="sidebar-section-label">{section.section}</div>
              {section.items.map(item => {
                const Icon = item.icon
                const isActive = pathname === item.path || pathname.startsWith(item.path + '/')
                return (
                  <button
                    key={item.path}
                    role="menuitem"
                    aria-label={collapsed ? item.label : undefined}
                    className={`sidebar-item ${isActive ? 'active' : ''} ${collapsed ? 'tooltip' : ''}`}
                    data-tooltip={collapsed ? item.label : undefined}
                    onClick={() => navigate(item.path)}
                    style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer' }}
                  >
                    <span className="sidebar-item-icon">
                      <Icon />
                    </span>
                    <span className="sidebar-item-label">{item.label}</span>
                  </button>
                )
              })}
            </div>
          ))}
        </div>

        {/* Collapse toggle */}
        <div className="sidebar-toggle">
          <button
            className="sidebar-toggle-btn"
            onClick={() => setCollapsed(c => !c)}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <ChevronLeft />
          </button>
        </div>
      </nav>

      {/* ── Main Area ── */}
      <div className="main-area">
        {/* Top Header */}
        <header className="top-header" role="banner">
          <div className="top-header-left">
            <DatabaseDropdown />
            <APIStatusBadge />
          </div>
          <div className="top-header-right">
            <button
              className="icon-btn"
              title="API Documentation"
              aria-label="API Documentation"
              onClick={() => navigate('/API')}
            >
              <Code2 />
            </button>
            <button
              className="icon-btn"
              title="Settings"
              aria-label="Settings"
              onClick={() => navigate('/Setting')}
            >
              <Settings />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="page-content" role="main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default observer(AppLayout)
