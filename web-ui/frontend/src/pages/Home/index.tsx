import React, { useState, useEffect } from 'react'
import { observer } from 'mobx-react'
import ReactMarkdown from 'react-markdown'
import {
    MessageCircle,
    Send,
    Plus,
    Database,
    Settings,
    User,
    Bot,
    Trash2,
    RotateCcw,
    Loader2,
    Zap,
    Layers,
    BookOpen,
    GitCompare,
    Upload
} from 'lucide-react'
import UploadKnowledgeModal from '../../components/UploadKnowledgeModal'
import {
    Button,
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    ScrollArea,
    Textarea,
    Separator,
    Avatar,
    AvatarFallback,
    AvatarImage
} from '../../components/ui'
import { storeGlobalUser } from '../../store/globalUser'
import { SERVER_URL } from '../../utils'
import DatabaseSelector from '../../components/DatabaseSelector'
import RetrievalInfo from '../../components/RetrievalInfo'
import RetrievalHyperGraph from '../../components/RetrievalHyperGraph'
import { conversations as defaultConversations } from './data'

const HyperRAGHome = () => {
    // State
    const [conversations, setConversations] = useState([])
    const [activeConversationId, setActiveConversationId] = useState('')
    const [inputValue, setInputValue] = useState('')
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
    const [queryMode, setQueryMode] = useState('adaptive')
    const [isLoading, setIsLoading] = useState(false)
    const [availableModes, setAvailableModes] = useState(['adaptive', 'hyper', 'hyper-lite', 'naive'])

    // Compare mode state
    const [isCompareMode, setIsCompareMode] = useState(false)
    const [compareMode1, setCompareMode1] = useState('adaptive')
    const [compareMode2, setCompareMode2] = useState('hyper-lite')

    // Storage keys
    const STORAGE_KEYS = {
        CONVERSATIONS: 'hyperrag_conversations_v2',
        ACTIVE_ID: 'hyperrag_active_conversation_v2'
    }

    // Available mode configurations
    const allModes = [
        { value: 'adaptive', label: 'Adaptive RAG', icon: Zap, color: 'bg-indigo-600' },
        { value: 'hyper', label: 'Hyper-RAG (Core)', icon: Layers, color: 'bg-purple-500' },
        { value: 'hyper-lite', label: 'Hyper-RAG Lite', icon: BookOpen, color: 'bg-green-600' },
        { value: 'naive', label: 'RAG', icon: BookOpen, color: 'bg-blue-500' },
        { value: 'graph', label: 'Graph-RAG', icon: Bot, color: 'bg-orange-500' },
        { value: 'llm', label: 'LLM Direct', icon: Bot, color: 'bg-yellow-500' }
    ]

    // Load Mode configuration from localStorage
    const loadModeSettings = () => {
        try {
            const modeSettings = localStorage.getItem('hyperrag_mode_settings')
            if (modeSettings) {
                const parsed = JSON.parse(modeSettings)
                if (parsed.availableModes && Array.isArray(parsed.availableModes) && parsed.availableModes.length > 0) {
                    setAvailableModes(parsed.availableModes)
                    // If selected mode not in available list, pick first available
                    if (!parsed.availableModes.includes(queryMode)) {
                        setQueryMode(parsed.availableModes[0])
                    }
                } else {
                    // Fallback to default modes with adaptive first
                    setAvailableModes(['adaptive', 'hyper', 'hyper-lite', 'naive'])
                }
            }
        } catch (error) {
            console.error('Failed to load mode settings:', error)
            // Fallback to default modes with adaptive first
            setAvailableModes(['adaptive', 'hyper', 'hyper-lite', 'naive'])
        }
    }

    // Listen for localStorage changes
    const handleStorageChange = (e) => {
        if (e.key === 'hyperrag_mode_settings') {
            loadModeSettings()
        }
    }

    // Get current enabled modes list
    const enabledModes = allModes.filter(mode => availableModes.includes(mode.value))

    // Function to get mode label
    const getModeLabel = (roleValue) => {
        if (roleValue === 'user') {
return 'You'
}
        const mode = allModes.find(m => m.value === roleValue)
        return mode ? mode.label : roleValue
    }

    // Utility functions
    const saveToStorage = () => {
        localStorage.setItem(STORAGE_KEYS.CONVERSATIONS, JSON.stringify(conversations))
        localStorage.setItem(STORAGE_KEYS.ACTIVE_ID, activeConversationId)
    }

    const loadFromStorage = () => {
        try {
            const savedConversations = localStorage.getItem(STORAGE_KEYS.CONVERSATIONS) || JSON.stringify(defaultConversations)
            const savedActiveId = localStorage.getItem(STORAGE_KEYS.ACTIVE_ID)

            if (savedConversations) {
                const parsed = JSON.parse(savedConversations)
                setConversations(parsed)

                if (savedActiveId && parsed.find((c) => c.id === savedActiveId)) {
                    setActiveConversationId(savedActiveId)
                } else if (parsed.length > 0) {
                    setActiveConversationId(parsed[0].id)
                }
            } else {
                // Create default conversation
                const defaultConv = {
                    id: 'default',
                    title: 'Chat 1',
                    messages: [],
                    createdAt: new Date()
                }
                setConversations([defaultConv])
                setActiveConversationId('default')
            }
        } catch (error) {
            console.error('Failed to load from storage:', error)
        }
    }

    const createNewConversation = () => {
        const newConv = {
            id: Date.now().toString(),
            title: `Chat ${new Date().toLocaleTimeString()}`,
            messages: [],
            createdAt: new Date()
        }
        setConversations(prev => [newConv, ...prev])
        setActiveConversationId(newConv.id)
    }

    const deleteConversation = (id) => {
        setConversations(prev => prev.filter(c => c.id !== id))
        if (activeConversationId === id) {
            const remaining = conversations.filter(c => c.id !== id)
            if (remaining.length > 0) {
                setActiveConversationId(remaining[0].id)
            } else {
                createNewConversation()
            }
        }
    }

    const clearAllChats = () => {
        setConversations([])
        createNewConversation()
    }

    const activeConversation = conversations.find(c => c.id === activeConversationId)

    const addMessage = (content, role, extraData = null) => {
        const newMessage = {
            id: Date.now(),
            content,
            role,
            timestamp: new Date(),
            // Add retrieval info field
            entities: extraData?.entities || [],
            hyperedges: extraData?.hyperedges || [],
            text_units: extraData?.text_units || [],
            // Add comparison mode fields
            isCompare: extraData?.isCompare || false,
            compareResults: extraData?.compareResults || null
        }

        setConversations(prev =>
            prev.map(conv =>
                conv.id === activeConversationId
                    ? { ...conv, messages: [...conv.messages, newMessage] }
                    : conv
            )
        )
    }

    const updateLastMessage = (content, extraData = null) => {
        setConversations(prev =>
            prev.map(conv =>
                conv.id === activeConversationId
                    ? {
                        ...conv,
                        messages: conv.messages.map((msg, index) =>
                            index === conv.messages.length - 1
                                ? {
                                    ...msg,
                                    content: content !== undefined && content !== null ? content : msg.content,
                                    entities: extraData?.entities || msg.entities || [],
                                    hyperedges: extraData?.hyperedges || msg.hyperedges || [],
                                    text_units: extraData?.text_units || msg.text_units || [],
                                    adaptive_decision: extraData?.adaptive_decision || msg.adaptive_decision || null,
                                    validation: extraData?.validation || msg.validation || null,
                                    language_guard: extraData?.language_guard || msg.language_guard || null,
                                    // Update compare results
                                    isCompare: extraData?.isCompare !== undefined ? extraData.isCompare : msg.isCompare,
                                    compareResults: extraData?.compareResults || msg.compareResults
                                }
                                : msg
                        )
                    }
                    : conv
            )
        )
    }

    // Single mode query function
    const querySingleMode = async (question, mode) => {
        const response = await fetch(`${SERVER_URL}/hyperrag/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                mode: mode,
                top_k: 60,
                max_token_for_text_unit: 1600,
                max_token_for_entity_context: 300,
                max_token_for_relation_context: 1600,
                only_need_context: false,
                response_type: 'Multiple Paragraphs',
                database: storeGlobalUser.selectedDatabase
            }),
        })

        if (!response.ok) {
            throw new Error(`Network error: ${response.status}`)
        }

        return response.json()
    }

    const handleSubmit = async () => {
        if (!inputValue.trim() || isLoading) {
return
}

        const userMessage = inputValue.trim()
        setInputValue('')
        setIsLoading(true)

        // Add user message
        addMessage(userMessage, 'user')

        if (isCompareMode) {
            // Compare mode: query both modes concurrently
            addMessage('Running comparative analysis...', 'compare', { isCompare: true })

            try {
                const [result1, result2] = await Promise.all([
                    querySingleMode(userMessage, compareMode1),
                    querySingleMode(userMessage, compareMode2)
                ])

                const modeNames = {
                    'adaptive': 'Adaptive RAG',
                    'hyper': 'Hyper-RAG (Core)',
                    'hyper-lite': 'Hyper-RAG Lite',
                    'graph': 'Graph-RAG',
                    'naive': 'RAG',
                    'llm': 'LLM Direct',
                }

                const compareResults = {
                    mode1: {
                        name: modeNames[compareMode1] || compareMode1,
                        mode: compareMode1,
                        response: result1.success ? (result1.response || result1.answer || 'No response content') : `Error: ${result1.message}`,
                        entities: result1.entities || [],
                        hyperedges: result1.hyperedges || [],
                        text_units: result1.text_units || [],
                        adaptive_decision: result1.adaptive_decision || null,
                        validation: result1.validation || null,
                        success: result1.success
                    },
                    mode2: {
                        name: modeNames[compareMode2] || compareMode2,
                        mode: compareMode2,
                        response: result2.success ? (result2.response || result2.answer || 'No response content') : `Error: ${result2.message}`,
                        entities: result2.entities || [],
                        hyperedges: result2.hyperedges || [],
                        text_units: result2.text_units || [],
                        adaptive_decision: result2.adaptive_decision || null,
                        validation: result2.validation || null,
                        success: result2.success
                    }
                }

                updateLastMessage('Comparative analysis complete', {
                    isCompare: true,
                    compareResults: compareResults
                })

            } catch (error) {
                console.error('Error in compare mode:', error)
                updateLastMessage(`Comparative analysis error: ${error instanceof Error ? error.message : 'Unknown error'}`, {
                    isCompare: true
                })
            } finally {
                setIsLoading(false)
            }
        } else {
            // Single mode query
            addMessage('Thinking...', queryMode)

            try {
                const data = await querySingleMode(userMessage, queryMode)

                if (data.success) {
                    const modeNames = {
                        'adaptive': 'Adaptive RAG',
                        'hyper': 'Hyper-RAG (Core)',
                        'hyper-lite': 'Hyper-RAG Lite',
                        'graph': 'Graph-RAG',
                        'naive': 'RAG',
                        'llm': 'LLM Direct',
                    }
                    const modeName = modeNames[queryMode] || queryMode

                    const responseContent = data.response || data.answer || 'No response content'

                    updateLastMessage(responseContent, {
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
            } catch (error) {
                console.error('Error sending message:', error)
                updateLastMessage(`Sorry, an error occurred: ${error instanceof Error ? error.message : 'Unknown error'}`)
            } finally {
                setIsLoading(false)
            }
        }
    }

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit()
        }
    }

    // Effects
    useEffect(() => {
        storeGlobalUser.restoreSelectedDatabase()
        storeGlobalUser.loadDatabases()
        loadFromStorage()
        loadModeSettings()

        // Add storage event listener
        window.addEventListener('storage', handleStorageChange)

        return () => {
            window.removeEventListener('storage', handleStorageChange)
        }
    }, [])

    useEffect(() => {
        if (conversations.length > 0) {
            saveToStorage()
        }
    }, [conversations, activeConversationId])

    // Ensure selected mode is in availableModes
    useEffect(() => {
        if (availableModes.length > 0 && !availableModes.includes(queryMode)) {
            setQueryMode(availableModes[0])
        }
    }, [availableModes, queryMode])

    // Ensure compare mode is in availableModes
    useEffect(() => {
        if (availableModes.length > 0) {
            if (!availableModes.includes(compareMode1)) {
                setCompareMode1(availableModes[0])
            }
            if (!availableModes.includes(compareMode2)) {
                setCompareMode2(availableModes[Math.min(1, availableModes.length - 1)])
            }
        }
    }, [availableModes, compareMode1, compareMode2])

    return (
        <div className="flex bg-gray-50">
            {/* Sidebar */}
            <div className="w-52 bg-gray-100 border-r border-gray-200 flex flex-col">

                {/* Mode Selector */}
                <div className="flex items-center space-x-1 p-3 text-base">
                    <div className="flex flex-col bg-gray-100 rounded-lg p-1 w-full space-y-1">
                        <div className="flex items-center space-x-2 mb-3">
                            <Settings className="w-5 h-5 shrink-0 text-gray-500" />
                            <span className="font-medium text-gray-700 flex-1">Mode: </span>
                            {/* Compare mode toggle */}
                            <div className=" p-2 bg-white rounded-md">
                                <label className="flex items-center cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={isCompareMode}
                                        onChange={(e) => setIsCompareMode(e.target.checked)}
                                        className="rounded"
                                    />
                                    <span className="text-sm font-medium text-gray-700 ml-1">Compare</span>
                                    <GitCompare className="w-4 h-4 text-blue-500" />
                                </label>
                            </div>
                        </div>


                        {isCompareMode ? (
                            /* Compare mode: show two mode selectors */
                            <div className="space-y-3">
                                <div>
                                    <span className="text-xs text-gray-500 mb-1 block">Mode 1:</span>
                                    <div className="space-y-1">
                                        {enabledModes.map((mode) => {
                                            const IconComponent = mode.icon
                                            return (
                                                <button
                                                    key={`mode1-${mode.value}`}
                                                    onClick={() => setCompareMode1(mode.value)}
                                                    className={`text-base flex items-center space-x-2 px-3 py-1.5 rounded-md font-medium transition-all duration-200 cursor-pointer w-full ${compareMode1 === mode.value
                                                        ? `${mode.color} text-white shadow-md`
                                                        : 'text-gray-600 hover:bg-gray-200'
                                                        }`}
                                                >
                                                    <IconComponent className="w-3 h-3 shrink-0" />
                                                    <span>{mode.label}</span>
                                                </button>
                                            )
                                        })}
                                    </div>
                                </div>
                                <div>
                                    <span className="text-xs text-gray-500 mb-1 block">Mode 2:</span>
                                    <div className="space-y-1">
                                        {enabledModes.map((mode) => {
                                            const IconComponent = mode.icon
                                            return (
                                                <button
                                                    key={`mode2-${mode.value}`}
                                                    onClick={() => setCompareMode2(mode.value)}
                                                    className={`text-base flex items-center space-x-2 px-3 py-1.5 rounded-md font-medium transition-all duration-200 cursor-pointer w-full ${compareMode2 === mode.value
                                                        ? `${mode.color} text-white shadow-md`
                                                        : 'text-gray-600 hover:bg-gray-200'
                                                        }`}
                                                >
                                                    <IconComponent className="w-3 h-3 shrink-0" />
                                                    <span>{mode.label}</span>
                                                </button>
                                            )
                                        })}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            /* Single mode: show mode selector */
                            enabledModes.map((mode) => {
                                const IconComponent = mode.icon
                                return (
                                    <button
                                        key={mode.value}
                                        onClick={() => setQueryMode(mode.value)}
                                        className={`text-base flex items-center space-x-2 px-4 py-2 rounded-md font-medium transition-all duration-200 cursor-pointer ${queryMode === mode.value
                                            ? `${mode.color} text-white shadow-md`
                                            : 'text-gray-600 hover:bg-gray-200'
                                            }`}
                                    >
                                        <IconComponent className="w-4 h-4 shrink-0" />
                                        <span>{mode.label}</span>
                                    </button>
                                )
                            })
                        )}
                    </div>
                </div>

                {/* Header */}
                <Separator className="my-3" />
                <div className="p-4 border-b border-gray-200">
                    <Button
                        onClick={createNewConversation}
                        className="w-full"
                        variant="outline"
                    >
                        <Plus className="w-4 h-4 mr-2" />
                        New Conversation
                    </Button>
                </div>

                {/* Conversations List */}
                <ScrollArea className="flex-1 p-2">
                    <div className="space-y-2">
                        {conversations.map((conv) => (
                            <div
                                key={conv.id}
                                className={`group p-1 rounded-lg cursor-pointer transition-colors ${activeConversationId === conv.id
                                    ? 'bg-blue-50 border border-blue-200'
                                    : 'hover:bg-gray-50'
                                    }`}
                                onClick={() => setActiveConversationId(conv.id)}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-2 flex-1 min-w-0">
                                        <MessageCircle className="w-4 h-4 text-gray-500" />
                                        <span className="text-sm font-medium text-gray-900 truncate">
                                            {conv.title}
                                        </span>
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="opacity-0 group-hover:opacity-100 h-6 w-6"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            deleteConversation(conv.id)
                                        }}
                                    >
                                        <Trash2 className="w-3 h-3" />
                                    </Button>
                                </div>

                            </div>
                        ))}
                    </div>
                </ScrollArea>

                {/* Controls */}
                <div className="p-4 border-t border-gray-200 space-y-4">
                    <Button
                        variant="outline"
                        onClick={clearAllChats}
                        className="w-full"
                    >
                        <RotateCcw className="w-4 h-4 mr-2" />
                        Clear All Chats
                    </Button>
                </div>

            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col">
                {/* Top Bar */}
                <div className="bg-white border-b border-gray-200 p-4">
                    <div className="flex items-center justify-between w-full">
                        <div className="flex items-center space-x-4">
                            <Database className="w-5 h-5 text-gray-500" />
                            <span className="font-medium text-gray-700">Database:</span>
                            <DatabaseSelector
                                mode="buttons"
                                showCurrent={true}
                                showRefresh={true}
                                placeholder=""
                                style={{}}
                                size="small"
                                disabled={false}
                            />
                        </div>
                        <div>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setIsUploadModalOpen(true)}
                                className="flex items-center space-x-2 text-blue-600 border-blue-300 hover:bg-blue-50 font-medium px-3 py-1.5 rounded-lg transition-colors shadow-sm"
                            >
                                <Upload className="w-4 h-4 text-blue-600" />
                                <span>Upload Knowledge</span>
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Chat Area */}
                <div className="flex-1 flex flex-col">
                    {/* Messages */}
                    <ScrollArea className="p-4 pb-0 h-[calc(100vh-210px)] bg-white">
                        {activeConversation?.messages.length === 0 ? (
                            <div className="flex-1 flex items-center justify-center mt-20">
                                <div className="text-center">
                                    <Bot className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                                        Welcome to Hyper-RAG
                                    </h3>
                                    <p className="text-gray-500 max-w-md">
                                        Ask me anything about your knowledge base. I&apos;ll help you find the
                                        information you need using advanced RAG technology.
                                    </p>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-6 mx-auto">
                                {activeConversation?.messages.map((message) => (
                                    <div key={message.id + message.content} className="flex space-x-4">
                                        <Avatar>
                                            {message.role === 'user' ? (
                                                <AvatarFallback>
                                                    <User className="w-5 h-5" />
                                                </AvatarFallback>
                                            ) : (
                                                <AvatarFallback>
                                                    {message.isCompare ? (
                                                        <GitCompare className="w-5 h-5" />
                                                    ) : (
                                                        <Bot className="w-5 h-5" />
                                                    )}
                                                </AvatarFallback>
                                            )}
                                        </Avatar>

                                        <div className="flex-1 space-y-2">
                                            <div className="flex items-center space-x-2">
                                                <span className="font-medium text-gray-900">
                                                    {message.isCompare ? 'Comparative Analysis' : getModeLabel(message.role)}
                                                </span>
                                                <span className="text-xs text-gray-500">
                                                    {new Date(message.timestamp).toLocaleTimeString()}
                                                </span>
                                            </div>

                                            {message.isCompare && message.compareResults ? (
                                                /* Compare mode message display */
                                                <div className="grid grid-cols-2 gap-4">
                                                    {/* Mode 1 result */}
                                                    <div className="flex flex-col bg-blue-50 border border-blue-200 rounded-lg p-4">
                                                        <div className="flex items-center space-x-2 mb-3">
                                                            <div className="flex items-center space-x-2">
                                                                {(() => {
                                                                    const mode = allModes.find(m => m.value === message.compareResults.mode1.mode)
                                                                    const IconComponent = mode?.icon || Bot
                                                                    return <IconComponent className="w-4 h-4" />
                                                                })()}
                                                                <span className="font-medium text-blue-800">
                                                                    {message.compareResults.mode1.name}
                                                                </span>
                                                            </div>
                                                            {!message.compareResults.mode1.success && (
                                                                <span className="text-xs text-red-500">Failed</span>
                                                            )}
                                                        </div>

                                                        <div className="flex-1 flex flex-col">
                                                            <div className="flex-1 prose prose-sm">
                                                                <ReactMarkdown
                                                                    components={{
                                                                        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                                                        code: ({ children, className }) => (
                                                                            <code className={`${className} bg-blue-100 px-1 rounded`}>
                                                                                {children}
                                                                            </code>
                                                                        ),
                                                                        pre: ({ children }) => (
                                                                            <pre className="bg-blue-100 p-3 rounded-md overflow-x-auto">
                                                                                {children}
                                                                            </pre>
                                                                        ),
                                                                    }}
                                                                >
                                                                    {message.compareResults.mode1.response}
                                                                </ReactMarkdown>
                                                            </div>

                                                            {message.compareResults.mode1.success && (
                                                                <div className='overflow-auto pl-2'>
                                                                    <RetrievalInfo
                                                                        entities={message.compareResults.mode1.entities || []}
                                                                        hyperedges={message.compareResults.mode1.hyperedges || []}
                                                                        textUnits={message.compareResults.mode1.text_units || []}
                                                                        mode={message.compareResults.mode1.mode}
                                                                    />

                                                                    {((message.compareResults.mode1.entities && message.compareResults.mode1.entities.length > 0) ||
                                                                        (message.compareResults.mode1.hyperedges && message.compareResults.mode1.hyperedges.length > 0)) && (
                                                                            <div className="mt-4">
                                                                                <RetrievalHyperGraph
                                                                                    entities={message.compareResults.mode1.entities || []}
                                                                                    hyperedges={message.compareResults.mode1.hyperedges || []}
                                                                                    height="300px"
                                                                                    mode={message.compareResults.mode1.mode}
                                                                                    graphId={`compare-graph-1-${message.id}`}
                                                                                />
                                                                            </div>
                                                                        )}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {/* Mode 2 result */}
                                                    <div className="flex flex-col bg-green-50 border border-green-200 rounded-lg p-4">
                                                        <div className="flex items-center space-x-2 mb-3">
                                                            <div className="flex items-center space-x-2">
                                                                {(() => {
                                                                    const mode = allModes.find(m => m.value === message.compareResults.mode2.mode)
                                                                    const IconComponent = mode?.icon || Bot
                                                                    return <IconComponent className="w-4 h-4" />
                                                                })()}
                                                                <span className="font-medium text-green-800">
                                                                    {message.compareResults.mode2.name}
                                                                </span>
                                                            </div>
                                                            {!message.compareResults.mode2.success && (
                                                                <span className="text-xs text-red-500">Failed</span>
                                                            )}
                                                        </div>

                                                        <div className="flex-1 flex flex-col">
                                                            <div className="flex-1 prose prose-sm">
                                                                <ReactMarkdown
                                                                    components={{
                                                                        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                                                        code: ({ children, className }) => (
                                                                            <code className={`${className} bg-green-100 px-1 rounded`}>
                                                                                {children}
                                                                            </code>
                                                                        ),
                                                                        pre: ({ children }) => (
                                                                            <pre className="bg-green-100 p-3 rounded-md overflow-x-auto">
                                                                                {children}
                                                                            </pre>
                                                                        ),
                                                                    }}
                                                                >
                                                                    {message.compareResults.mode2.response}
                                                                </ReactMarkdown>
                                                            </div>

                                                            {message.compareResults.mode2.success && (
                                                                <div className='overflow-auto pl-2'>
                                                                    <RetrievalInfo
                                                                        entities={message.compareResults.mode2.entities || []}
                                                                        hyperedges={message.compareResults.mode2.hyperedges || []}
                                                                        textUnits={message.compareResults.mode2.text_units || []}
                                                                        mode={message.compareResults.mode2.mode}
                                                                    />

                                                                    {((message.compareResults.mode2.entities && message.compareResults.mode2.entities.length > 0) ||
                                                                        (message.compareResults.mode2.hyperedges && message.compareResults.mode2.hyperedges.length > 0)) && (
                                                                            <div className="mt-4">
                                                                                <RetrievalHyperGraph
                                                                                    entities={message.compareResults.mode2.entities || []}
                                                                                    hyperedges={message.compareResults.mode2.hyperedges || []}
                                                                                    height="300px"
                                                                                    mode={message.compareResults.mode2.mode}
                                                                                    graphId={`compare-graph-2-${message.id}`}
                                                                                />
                                                                            </div>
                                                                        )}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            ) : (
                                                /* Single mode message display */
                                                <div className={`rounded-lg p-4 ${message.role === 'user'
                                                    ? 'bg-blue-50 border border-blue-200'
                                                    : 'bg-gray-50 border border-gray-200'
                                                    }`}>
                                                    {message.role !== 'user' ? (
                                                        <div className='flex flex-col'>
                                                            {message.adaptive_decision && (
                                                                <div className="mb-3 p-2.5 bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200 rounded-lg text-xs space-y-1">
                                                                    <div className="flex flex-wrap items-center gap-2">
                                                                        <span className="font-semibold text-indigo-900 flex items-center">
                                                                            <Zap className="w-3.5 h-3.5 mr-1 text-indigo-600" />
                                                                            Adaptive RAG
                                                                        </span>
                                                                        <span className="bg-white px-2 py-0.5 rounded border border-indigo-200 text-indigo-800 font-medium">
                                                                            Path: <strong className="text-indigo-900">{message.adaptive_decision.mode?.toUpperCase()}</strong>
                                                                        </span>
                                                                        <span className="bg-white px-2 py-0.5 rounded border border-indigo-200 text-indigo-800">
                                                                            Complexity: <strong>{message.adaptive_decision.score}</strong>
                                                                        </span>
                                                                        {message.adaptive_decision.escalated && (
                                                                            <span className="bg-amber-100 text-amber-900 px-2 py-0.5 rounded border border-amber-300 font-medium">
                                                                                Escalation: Lite → Core
                                                                            </span>
                                                                        )}
                                                                        {message.adaptive_decision.retrieval_sufficiency_score !== undefined && message.adaptive_decision.retrieval_sufficiency_score !== null && (
                                                                            <span className="bg-white px-2 py-0.5 rounded border border-indigo-200 text-indigo-800">
                                                                                Sufficiency: <strong>{message.adaptive_decision.retrieval_sufficiency_score}</strong>
                                                                            </span>
                                                                        )}
                                                                        {message.validation && (
                                                                            <span className={`px-2 py-0.5 rounded border font-medium ${message.validation.valid ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-rose-50 text-rose-800 border-rose-200'}`}>
                                                                                Validation: <strong>{message.validation.valid ? 'Valid' : 'Warning'} ({message.validation.score})</strong>
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                    {message.adaptive_decision.escalated && message.adaptive_decision.escalation_reason && (
                                                                        <div className="text-amber-800 text-[11px] pt-1">
                                                                            Reason: {message.adaptive_decision.escalation_reason}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            )}
                                                            {!message.adaptive_decision && message.validation && (
                                                                <div className="mb-3 p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-xs flex items-center gap-2">
                                                                    <span className="font-semibold text-emerald-900">Validation:</span>
                                                                    <span className="bg-white px-2 py-0.5 rounded border border-emerald-200 text-emerald-800 font-medium">
                                                                        Score: {message.validation.score} ({message.validation.valid ? 'Valid' : 'Warning'})
                                                                    </span>
                                                                </div>
                                                            )}
                                                            <div className='flex'>
                                                                <div className="flex-1 prose prose-sm z-0">
                                                                    <ReactMarkdown
                                                                        components={{
                                                                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                                                            code: ({ children, className }) => (
                                                                                <code className={`${className} bg-gray-100 px-1 rounded`}>
                                                                                    {children}
                                                                                </code>
                                                                            ),
                                                                            pre: ({ children }) => (
                                                                                <pre className="bg-gray-100 p-3 rounded-md overflow-x-auto">
                                                                                    {children}
                                                                                </pre>
                                                                            ),
                                                                        }}
                                                                    >
                                                                        {message.content}
                                                                    </ReactMarkdown>
                                                                </div>
                                                            <div className='flex-[0.7] overflow-auto pl-2 z-10'>
                                                                {/* Display retrieval info */}
                                                                <RetrievalInfo
                                                                    entities={message.entities || []}
                                                                    hyperedges={message.hyperedges || []}
                                                                    textUnits={message.text_units || []}
                                                                    mode={message.role}
                                                                />

                                                                {/* HyperGraph visualization */}
                                                                {((message.entities && message.entities.length > 0) ||
                                                                    (message.hyperedges && message.hyperedges.length > 0)) && (
                                                                        <div className="mt-4">
                                                                            <RetrievalHyperGraph
                                                                                entities={message.entities || []}
                                                                                hyperedges={message.hyperedges || []}
                                                                                height="400px"
                                                                                mode={message.role}
                                                                                graphId={`retrieval-graph-${message.id}`}
                                                                            />
                                                                        </div>
                                                                    )}
                                                            </div>
                                                        </div>
                                                        </div>
                                                    ) : (
                                                        <p className="text-gray-900 whitespace-pre-wrap m-0">
                                                            {message.content}
                                                        </p>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </ScrollArea>

                    {/* Input Area */}
                    <div className="border-t border-gray-200 bg-white p-2">
                        <div className="max-w-4xl mx-auto">
                            <div className="flex space-x-4 items-center">
                                <Textarea
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    placeholder={isCompareMode
                                        ? `Compare ${getModeLabel(compareMode1)} and ${getModeLabel(compareMode2)} responses...`
                                        : "Ask me anything about your knowledge base..."
                                    }
                                    className="flex-1 h-7 resize-none"
                                    disabled={isLoading}
                                />
                                <Button
                                    onClick={handleSubmit}
                                    disabled={!inputValue.trim() || isLoading}
                                    size="lg"
                                    className="px-6"
                                >
                                    {isLoading ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Send className="w-4 h-4" />
                                    )}
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <UploadKnowledgeModal
                visible={isUploadModalOpen}
                onClose={() => setIsUploadModalOpen(false)}
            />
        </div>
    )
}

export default observer(HyperRAGHome)