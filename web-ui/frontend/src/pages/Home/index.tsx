import React, { useState, useEffect, useRef, useCallback } from 'react'
import { observer } from 'mobx-react'
import ReactMarkdown from 'react-markdown'
import {
  MessageSquare,
  Plus,
  Send,
  Trash2,
  RotateCcw,
  Zap,
  Layers,
  BookOpen,
  GitBranch,
  Bot,
  User,
  Database,
  GitCompare,
  Upload,
  ChevronDown,
  ChevronUp,
  Share2,
  FileText,
  Network,
} from 'lucide-react'
import { storeGlobalUser } from '../../store/globalUser'
import { SERVER_URL } from '../../utils'
import UploadKnowledgeModal from '../../components/UploadKnowledgeModal'
import RetrievalInfo from '../../components/RetrievalInfo'
import RetrievalHyperGraph from '../../components/RetrievalHyperGraph'
import { conversations as defaultConversations } from './data'

/* ── Mode config ─────────────────────────────────────────────── */
const ALL_MODES = [
  { value: 'adaptive',   label: 'Adaptive RAG',   shortLabel: 'Adaptive', icon: Zap,        color: '#6366f1', dot: 'bg-indigo-500' },
  { value: 'hyper',      label: 'Hyper-RAG Core', shortLabel: 'Core',     icon: Layers,      color: '#7c3aed', dot: 'bg-violet-600' },
  { value: 'hyper-lite', label: 'Hyper-RAG Lite', shortLabel: 'Lite',     icon: BookOpen,    color: '#059669', dot: 'bg-emerald-500' },
  { value: 'naive',      label: 'RAG',            shortLabel: 'RAG',      icon: BookOpen,    color: '#2563eb', dot: 'bg-blue-600' },
  { value: 'graph',      label: 'Graph-RAG',      shortLabel: 'Graph',    icon: GitBranch,   color: '#d97706', dot: 'bg-amber-600' },
  { value: 'llm',        label: 'LLM Direct',     shortLabel: 'LLM',      icon: Bot,         color: '#64748b', dot: 'bg-slate-500' },
]

const MODE_COLORS: Record<string, string> = {
  adaptive:   '#6366f1',
  hyper:      '#7c3aed',
  'hyper-lite': '#059669',
  naive:      '#2563eb',
  graph:      '#d97706',
  llm:        '#64748b',
}

const getModeLabel = (role: string) => {
  if (role === 'user') return 'You'
  const m = ALL_MODES.find(m => m.value === role)
  return m ? m.label : role
}

const STORAGE_KEYS = {
  CONVERSATIONS: 'hyperrag_conversations_v2',
  ACTIVE_ID: 'hyperrag_active_conversation_v2',
}

/* ── Empty State ─────────────────────────────────────────────── */
const EmptyState: React.FC<{
  dbName: string
  onSuggestion: (q: string) => void
}> = ({ dbName, onSuggestion }) => {
  const suggestions = [
    'What is this knowledge base about?',
    'Summarize the available information',
    'Show the main entities and relationships',
    'What are the key topics covered?',
  ]
  const displayDb = dbName || 'selected knowledge base'

  return (
    <div className="chat-empty-state">
      <div className="chat-empty-logo" aria-hidden="true">
        <Zap size={26} />
      </div>
      <h2 className="chat-empty-title">Hyper-RAG</h2>
      <p className="chat-empty-subtitle">
        Ask questions about your knowledge base using hypergraph-enhanced retrieval.
      </p>
      <div className="chat-empty-db-info">
        <Database size={12} />
        <span>{displayDb}</span>
      </div>
      <div className="chat-empty-suggestions" role="list">
        {suggestions.map(q => (
          <button
            key={q}
            role="listitem"
            className="chat-suggestion-btn"
            onClick={() => onSuggestion(q)}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

/* ── Adaptive RAG Metadata ───────────────────────────────────── */
const AdaptiveMeta: React.FC<{ decision: any; validation: any }> = ({ decision, validation }) => {
  if (!decision && !validation) return null
  return (
    <div className="adaptive-meta" role="note" aria-label="Adaptive RAG routing decision">
      <span className="adaptive-meta-label">
        <Zap size={10} /> Adaptive
      </span>
      {decision && (
        <>
          <span className="adaptive-meta-chip">
            Path: <strong>{decision.mode?.toUpperCase()}</strong>
          </span>
          {decision.score !== undefined && (
            <span className="adaptive-meta-chip">
              Complexity: <strong>{decision.score}</strong>
            </span>
          )}
          {decision.escalated && (
            <span className="adaptive-meta-chip escalated">
              ↑ Escalated: Lite → Core
            </span>
          )}
          {decision.retrieval_sufficiency_score != null && (
            <span className="adaptive-meta-chip">
              Sufficiency: <strong>{decision.retrieval_sufficiency_score}</strong>
            </span>
          )}
        </>
      )}
      {validation && (
        <span className={`adaptive-meta-chip ${validation.valid ? 'valid' : 'invalid'}`}>
          Validation: <strong>{validation.valid ? '✓ Valid' : '⚠ Warning'} ({validation.score})</strong>
        </span>
      )}
      {decision?.escalated && decision?.escalation_reason && (
        <span style={{ fontSize: '11px', color: 'var(--warning-700)', width: '100%' }}>
          Reason: {decision.escalation_reason}
        </span>
      )}
    </div>
  )
}

/* ── Retrieval Accordion ─────────────────────────────────────── */
const RetrievalAccordion: React.FC<{
  entities: any[]
  hyperedges: any[]
  textUnits: any[]
  mode: string
  messageId: number | string
}> = ({ entities, hyperedges, textUnits, mode, messageId }) => {
  const [open, setOpen] = useState(false)
  const hasGraph = (entities.length > 0 || hyperedges.length > 0)
  const totalItems = entities.length + hyperedges.length + textUnits.length

  if (totalItems === 0) return null

  return (
    <div className="retrieval-panel" style={{ marginTop: '12px' }}>
      <button
        className="retrieval-panel-header"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <Share2 size={13} style={{ color: 'var(--text-tertiary)' }} />
        <span>Retrieved Context</span>
        {entities.length > 0 && (
          <span className="retrieval-count-badge" title="Entities" style={{ background: '#dbeafe', color: '#1d4ed8' }}>
            {entities.length} entities
          </span>
        )}
        {hyperedges.length > 0 && (
          <span className="retrieval-count-badge" title="Edges" style={{ background: '#dcfce7', color: '#15803d' }}>
            {hyperedges.length} edges
          </span>
        )}
        {textUnits.length > 0 && (
          <span className="retrieval-count-badge" title="Text chunks" style={{ background: '#f3e8ff', color: '#7e22ce' }}>
            {textUnits.length} chunks
          </span>
        )}
        <span style={{ marginLeft: 'auto' }}>
          {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </span>
      </button>
      {open && (
        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border-subtle)' }}>
          <RetrievalInfo
            entities={entities}
            hyperedges={hyperedges}
            textUnits={textUnits}
            mode={mode}
          />
          {hasGraph && (
            <div style={{ marginTop: '16px' }}>
              <RetrievalHyperGraph
                entities={entities}
                hyperedges={hyperedges}
                height="360px"
                mode={mode}
                graphId={`msg-graph-${messageId}`}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Message Bubble ──────────────────────────────────────────── */
const MessageBubble: React.FC<{ message: any }> = ({ message }) => {
  const isUser = message.role === 'user'
  const isCompare = message.isCompare
  const modeColor = MODE_COLORS[message.role] || 'var(--brand-500)'

  return (
    <div className={`message-group ${isUser ? 'user' : ''}`} role="article" aria-label={`${isUser ? 'Your' : 'Assistant'} message`}>
      {/* Avatar */}
      <div className={`message-avatar ${isUser ? 'user' : 'assistant'}`} aria-hidden="true">
        {isUser ? <User size={14} /> : isCompare ? <GitCompare size={14} /> : <Bot size={14} />}
      </div>

      {/* Content */}
      <div className="message-body">
        <div className="message-meta">
          <span className="message-author">{isCompare ? 'Comparative Analysis' : getModeLabel(message.role)}</span>
          <span className="message-timestamp">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Compare mode */}
        {isCompare && message.compareResults ? (
          <div className="compare-grid">
            {/* Mode 1 */}
            <div className="compare-panel panel-a">
              <div className="compare-panel-header">
                <Network size={14} />
                {message.compareResults.mode1.name}
              </div>
              <div className="prose-content">
                <ReactMarkdown>{message.compareResults.mode1.response}</ReactMarkdown>
              </div>
              {message.compareResults.mode1.success && (
                <RetrievalAccordion
                  entities={message.compareResults.mode1.entities || []}
                  hyperedges={message.compareResults.mode1.hyperedges || []}
                  textUnits={message.compareResults.mode1.text_units || []}
                  mode={message.compareResults.mode1.mode}
                  messageId={`${message.id}-m1`}
                />
              )}
            </div>
            {/* Mode 2 */}
            <div className="compare-panel panel-b">
              <div className="compare-panel-header">
                <Network size={14} />
                {message.compareResults.mode2.name}
              </div>
              <div className="prose-content">
                <ReactMarkdown>{message.compareResults.mode2.response}</ReactMarkdown>
              </div>
              {message.compareResults.mode2.success && (
                <RetrievalAccordion
                  entities={message.compareResults.mode2.entities || []}
                  hyperedges={message.compareResults.mode2.hyperedges || []}
                  textUnits={message.compareResults.mode2.text_units || []}
                  mode={message.compareResults.mode2.mode}
                  messageId={`${message.id}-m2`}
                />
              )}
            </div>
          </div>
        ) : isUser ? (
          /* User message */
          <div className="message-bubble user">
            <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{message.content}</p>
          </div>
        ) : (
          /* Assistant message */
          <div className="message-bubble assistant">
            {/* Adaptive RAG metadata */}
            <AdaptiveMeta decision={message.adaptive_decision} validation={message.validation} />

            <div className="prose-content">
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p>{children}</p>,
                  code: ({ children, className }) => (
                    <code className={className}>{children}</code>
                  ),
                  pre: ({ children }) => <pre>{children}</pre>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>

            {/* Retrieval info accordion */}
            <RetrievalAccordion
              entities={message.entities || []}
              hyperedges={message.hyperedges || []}
              textUnits={message.text_units || []}
              mode={message.role}
              messageId={message.id}
            />
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Main Page ───────────────────────────────────────────────── */
const HyperRAGHome: React.FC = () => {
  const [conversations, setConversations] = useState<any[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string>('')
  const [inputValue, setInputValue] = useState('')
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [queryMode, setQueryMode] = useState('adaptive')
  const [isLoading, setIsLoading] = useState(false)
  const [availableModes, setAvailableModes] = useState(['adaptive', 'hyper', 'hyper-lite', 'naive'])
  const [isCompareMode, setIsCompareMode] = useState(false)
  const [compareMode1, setCompareMode1] = useState('adaptive')
  const [compareMode2, setCompareMode2] = useState('hyper-lite')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const enabledModes = ALL_MODES.filter(m => availableModes.includes(m.value))

  /* ── Storage ── */
  const loadModeSettings = () => {
    try {
      const s = localStorage.getItem('hyperrag_mode_settings')
      if (s) {
        const p = JSON.parse(s)
        if (p.availableModes?.length > 0) {
          setAvailableModes(p.availableModes)
          if (!p.availableModes.includes(queryMode)) setQueryMode(p.availableModes[0])
        }
      }
    } catch {
      setAvailableModes(['adaptive', 'hyper', 'hyper-lite', 'naive'])
    }
  }

  const loadFromStorage = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.CONVERSATIONS) || JSON.stringify(defaultConversations)
      const savedId = localStorage.getItem(STORAGE_KEYS.ACTIVE_ID)
      if (saved) {
        const parsed = JSON.parse(saved)
        setConversations(parsed)
        if (savedId && parsed.find((c: any) => c.id === savedId)) {
          setActiveConversationId(savedId)
        } else if (parsed.length > 0) {
          setActiveConversationId(parsed[0].id)
        }
      }
    } catch {
      createNewConversation()
    }
  }

  const saveToStorage = useCallback(() => {
    localStorage.setItem(STORAGE_KEYS.CONVERSATIONS, JSON.stringify(conversations))
    localStorage.setItem(STORAGE_KEYS.ACTIVE_ID, activeConversationId)
  }, [conversations, activeConversationId])

  const createNewConversation = () => {
    const newConv = {
      id: Date.now().toString(),
      title: `Chat ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
      messages: [],
      createdAt: new Date(),
    }
    setConversations(prev => [newConv, ...prev])
    setActiveConversationId(newConv.id)
    return newConv
  }

  const deleteConversation = (id: string) => {
    setConversations(prev => prev.filter(c => c.id !== id))
    if (activeConversationId === id) {
      const remaining = conversations.filter(c => c.id !== id)
      if (remaining.length > 0) setActiveConversationId(remaining[0].id)
      else createNewConversation()
    }
  }

  const clearAllChats = () => {
    setConversations([])
    createNewConversation()
  }

  const activeConversation = conversations.find(c => c.id === activeConversationId)

  const addMessage = (content: string, role: string, extraData: any = null) => {
    const newMessage = {
      id: Date.now(),
      content,
      role,
      timestamp: new Date(),
      entities: extraData?.entities || [],
      hyperedges: extraData?.hyperedges || [],
      text_units: extraData?.text_units || [],
      isCompare: extraData?.isCompare || false,
      compareResults: extraData?.compareResults || null,
    }
    setConversations(prev =>
      prev.map(conv =>
        conv.id === activeConversationId
          ? { ...conv, messages: [...conv.messages, newMessage] }
          : conv
      )
    )
  }

  const updateLastMessage = (content: string | null, extraData: any = null) => {
    setConversations(prev =>
      prev.map(conv =>
        conv.id === activeConversationId
          ? {
              ...conv,
              messages: conv.messages.map((msg: any, idx: number) =>
                idx === conv.messages.length - 1
                  ? {
                      ...msg,
                      content: content !== undefined && content !== null ? content : msg.content,
                      entities: extraData?.entities ?? msg.entities ?? [],
                      hyperedges: extraData?.hyperedges ?? msg.hyperedges ?? [],
                      text_units: extraData?.text_units ?? msg.text_units ?? [],
                      adaptive_decision: extraData?.adaptive_decision ?? msg.adaptive_decision ?? null,
                      validation: extraData?.validation ?? msg.validation ?? null,
                      language_guard: extraData?.language_guard ?? msg.language_guard ?? null,
                      isCompare: extraData?.isCompare !== undefined ? extraData.isCompare : msg.isCompare,
                      compareResults: extraData?.compareResults ?? msg.compareResults,
                    }
                  : msg
              ),
            }
          : conv
      )
    )
  }

  /* ── Queries ── */
  const querySingleMode = async (question: string, mode: string) => {
    const response = await fetch(`${SERVER_URL}/hyperrag/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        mode,
        top_k: 60,
        max_token_for_text_unit: 1600,
        max_token_for_entity_context: 300,
        max_token_for_relation_context: 1600,
        only_need_context: false,
        response_type: 'Multiple Paragraphs',
        database: storeGlobalUser.selectedDatabase,
      }),
    })
    if (!response.ok) throw new Error(`Network error: ${response.status}`)
    return response.json()
  }

  const handleSubmit = async () => {
    if (!inputValue.trim() || isLoading) return
    const userMessage = inputValue.trim()
    setInputValue('')
    setIsLoading(true)
    addMessage(userMessage, 'user')

    if (isCompareMode) {
      addMessage('Running comparative analysis…', 'compare', { isCompare: true })
      try {
        const [r1, r2] = await Promise.all([
          querySingleMode(userMessage, compareMode1),
          querySingleMode(userMessage, compareMode2),
        ])
        const modeNames: Record<string, string> = {
          adaptive: 'Adaptive RAG', hyper: 'Hyper-RAG Core', 'hyper-lite': 'Hyper-RAG Lite',
          graph: 'Graph-RAG', naive: 'RAG', llm: 'LLM Direct',
        }
        updateLastMessage('Comparative analysis complete', {
          isCompare: true,
          compareResults: {
            mode1: { name: modeNames[compareMode1] || compareMode1, mode: compareMode1, response: r1.success ? (r1.response || r1.answer || '') : `Error: ${r1.message}`, entities: r1.entities || [], hyperedges: r1.hyperedges || [], text_units: r1.text_units || [], adaptive_decision: r1.adaptive_decision || null, validation: r1.validation || null, success: r1.success },
            mode2: { name: modeNames[compareMode2] || compareMode2, mode: compareMode2, response: r2.success ? (r2.response || r2.answer || '') : `Error: ${r2.message}`, entities: r2.entities || [], hyperedges: r2.hyperedges || [], text_units: r2.text_units || [], adaptive_decision: r2.adaptive_decision || null, validation: r2.validation || null, success: r2.success },
          },
        })
      } catch (err: any) {
        updateLastMessage(`Comparative analysis error: ${err.message || 'Unknown error'}`, { isCompare: true })
      } finally {
        setIsLoading(false)
      }
    } else {
      addMessage('Thinking…', queryMode)
      try {
        const data = await querySingleMode(userMessage, queryMode)
        if (data.success) {
          updateLastMessage(data.response || data.answer || 'No response content', {
            entities: data.entities || [],
            hyperedges: data.hyperedges || [],
            text_units: data.text_units || [],
            adaptive_decision: data.adaptive_decision || null,
            validation: data.validation || null,
            language_guard: data.language_guard || null,
          })
        } else {
          throw new Error(data.message || 'Query failed')
        }
      } catch (err: any) {
        updateLastMessage(`An error occurred: ${err.message || 'Unknown error'}`)
      } finally {
        setIsLoading(false)
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value)
    const ta = e.target
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
  }

  // Suggestion click
  const handleSuggestion = (q: string) => {
    setInputValue(q)
    textareaRef.current?.focus()
  }

  /* ── Effects ── */
  useEffect(() => {
    storeGlobalUser.restoreSelectedDatabase()
    storeGlobalUser.loadDatabases()
    loadFromStorage()
    loadModeSettings()
    const handleStorage = (e: StorageEvent) => {
      if (e.key === 'hyperrag_mode_settings') loadModeSettings()
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [])

  useEffect(() => {
    if (conversations.length > 0) saveToStorage()
  }, [conversations, activeConversationId, saveToStorage])

  useEffect(() => {
    if (availableModes.length > 0 && !availableModes.includes(queryMode)) {
      setQueryMode(availableModes[0])
    }
  }, [availableModes, queryMode])

  useEffect(() => {
    if (availableModes.length > 0) {
      if (!availableModes.includes(compareMode1)) setCompareMode1(availableModes[0])
      if (!availableModes.includes(compareMode2)) setCompareMode2(availableModes[Math.min(1, availableModes.length - 1)])
    }
  }, [availableModes, compareMode1, compareMode2])

  // Auto-scroll on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversations, activeConversationId])

  /* ── Render ── */
  return (
    <div className="chat-layout" style={{ height: '100%' }}>
      {/* ─── Chat Sidebar ─── */}
      <aside className="chat-sidebar" aria-label="Conversations and modes">
        {/* New conversation */}
        <div className="chat-sidebar-header">
          <button
            className="btn btn-secondary"
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={createNewConversation}
          >
            <Plus size={14} />
            New Chat
          </button>
        </div>

        {/* Mode selector */}
        <div className="chat-sidebar-section">
          <div className="chat-sidebar-section-label">Mode</div>

          {/* Compare toggle */}
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 8px',
              fontSize: '12px',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              userSelect: 'none',
              marginBottom: '4px',
            }}
          >
            <input
              type="checkbox"
              checked={isCompareMode}
              onChange={e => setIsCompareMode(e.target.checked)}
              style={{ width: '14px', height: '14px', cursor: 'pointer' }}
            />
            <GitCompare size={13} />
            Compare mode
          </label>

          {!isCompareMode ? (
            enabledModes.map(m => {
              const Icon = m.icon
              return (
                <button
                  key={m.value}
                  className={`chat-mode-btn ${queryMode === m.value ? 'active' : ''}`}
                  onClick={() => setQueryMode(m.value)}
                  aria-pressed={queryMode === m.value}
                  aria-label={`${m.label} mode`}
                >
                  <span
                    style={{
                      width: '7px',
                      height: '7px',
                      borderRadius: '50%',
                      background: queryMode === m.value ? m.color : 'var(--neutral-300)',
                      flexShrink: 0,
                      transition: 'background 0.15s',
                    }}
                  />
                  <Icon size={13} />
                  {m.shortLabel}
                </button>
              )
            })
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingTop: '4px' }}>
              <div>
                <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '0 8px 4px' }}>Mode A</div>
                {enabledModes.map(m => {
                  const Icon = m.icon
                  return (
                    <button key={`cmp1-${m.value}`} className={`chat-mode-btn ${compareMode1 === m.value ? 'active' : ''}`} onClick={() => setCompareMode1(m.value)} style={{ background: compareMode1 === m.value ? '#eff6ff' : '' }}>
                      <Icon size={13} />{m.shortLabel}
                    </button>
                  )
                })}
              </div>
              <div>
                <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '0 8px 4px' }}>Mode B</div>
                {enabledModes.map(m => {
                  const Icon = m.icon
                  return (
                    <button key={`cmp2-${m.value}`} className={`chat-mode-btn ${compareMode2 === m.value ? 'active' : ''}`} onClick={() => setCompareMode2(m.value)} style={{ background: compareMode2 === m.value ? '#f0fdf4' : '' }}>
                      <Icon size={13} />{m.shortLabel}
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Conversations */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', padding: '8px 4px', flexShrink: 0 }}>
          <div className="chat-sidebar-section-label" style={{ padding: '4px 8px' }}>Conversations</div>
        </div>
        <div className="chat-conv-list">
          {conversations.map(conv => (
            <div
              key={conv.id}
              className={`chat-conv-item ${activeConversationId === conv.id ? 'active' : ''}`}
              role="button"
              tabIndex={0}
              aria-current={activeConversationId === conv.id ? 'true' : undefined}
              onClick={() => setActiveConversationId(conv.id)}
              onKeyDown={e => e.key === 'Enter' && setActiveConversationId(conv.id)}
            >
              <MessageSquare size={12} style={{ flexShrink: 0, opacity: 0.5 }} />
              <span className="chat-conv-title">{conv.title}</span>
              <button
                className="chat-conv-delete"
                aria-label={`Delete ${conv.title}`}
                onClick={e => {
                  e.stopPropagation()
                  deleteConversation(conv.id)
                }}
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{ padding: '8px', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <button
            className="btn btn-ghost btn-sm"
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={clearAllChats}
          >
            <RotateCcw size={13} /> Clear all chats
          </button>
          <button
            className="btn btn-secondary btn-sm"
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={() => setIsUploadModalOpen(true)}
          >
            <Upload size={13} /> Upload Knowledge
          </button>
        </div>
      </aside>

      {/* ─── Chat Main ─── */}
      <div className="chat-main">
        {/* Messages */}
        <div className="chat-messages" role="log" aria-label="Conversation" aria-live="polite">
          {!activeConversation || activeConversation.messages.length === 0 ? (
            <EmptyState
              dbName={storeGlobalUser.availableDatabases.find(d => d.name === storeGlobalUser.selectedDatabase)?.description?.replace('Hypergraph', '').trim() || storeGlobalUser.selectedDatabase}
              onSuggestion={handleSuggestion}
            />
          ) : (
            <div style={{ maxWidth: '900px', margin: '0 auto' }}>
              {activeConversation.messages.map((msg: any) => (
                <MessageBubble key={`${msg.id}-${msg.role}`} message={msg} />
              ))}
              {isLoading && (
                <div className="message-group" aria-label="Loading" role="status">
                  <div className="message-avatar assistant" aria-hidden="true">
                    <Bot size={14} />
                  </div>
                  <div className="message-body">
                    <div className="message-meta">
                      <span className="message-author">{getModeLabel(queryMode)}</span>
                    </div>
                    <div className="message-bubble assistant" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                      <span className="spinner spinner-dark" style={{ width: '14px', height: '14px' }} />
                      <span style={{ color: 'var(--text-tertiary)', fontSize: '13px' }}>Thinking…</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={
                isCompareMode
                  ? `Compare ${enabledModes.find(m => m.value === compareMode1)?.shortLabel || compareMode1} vs ${enabledModes.find(m => m.value === compareMode2)?.shortLabel || compareMode2}…`
                  : 'Ask anything about your knowledge base…'
              }
              disabled={isLoading}
              rows={1}
              aria-label="Query input"
              style={{ minHeight: '24px' }}
            />
            <div className="chat-input-actions">
              <button
                className="chat-send-btn"
                onClick={handleSubmit}
                disabled={!inputValue.trim() || isLoading}
                aria-label="Send message"
              >
                {isLoading ? (
                  <span className="spinner" />
                ) : (
                  <Send size={15} />
                )}
              </button>
            </div>
          </div>
          <div className="chat-input-hint">
            Press Enter to send · Shift+Enter for new line
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      <UploadKnowledgeModal
        visible={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />
    </div>
  )
}

export default observer(HyperRAGHome)