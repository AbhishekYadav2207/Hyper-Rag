import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  message,
  Space,
  Divider,
  Typography,
  Alert,
  Row,
  Col,
  AutoComplete,
  Checkbox,
  Tag,
  Tooltip
} from 'antd'
import {
  SettingOutlined,
  KeyOutlined,
  DatabaseOutlined,
  ApiOutlined,
  SaveOutlined,
  ReloadOutlined,
  GlobalOutlined,
  AppstoreOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  SafetyCertificateOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import LanguageSelector from '../../components/LanguageSelector'
import { PageWrapper, PageHeader } from '../../components/PageLayout'
import { SERVER_URL } from '../../utils'

const { Title, Text } = Typography
const { Option } = Select
const { Password } = Input

const Setting: React.FC = () => {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [availableDatabases, setAvailableDatabases] = useState<any[]>([])

  // Credential status states (safe previews only, never full keys)
  const [apiKeyConfigured, setApiKeyConfigured] = useState(false)
  const [apiKeyPreview, setApiKeyPreview] = useState('')
  const [embeddingApiKeyConfigured, setEmbeddingApiKeyConfigured] = useState(false)
  const [embeddingApiKeyPreview, setEmbeddingApiKeyPreview] = useState('')
  const [clearApiKeyRequested, setClearApiKeyRequested] = useState(false)
  const [clearEmbeddingApiKeyRequested, setClearEmbeddingApiKeyRequested] = useState(false)

  const [testResults, setTestResults] = useState<{
    [key: string]: { status: 'idle' | 'testing' | 'success' | 'failed'; message?: string }
  }>({
    llm: { status: 'idle' },
    embedding: { status: 'idle' }
  })

  // Default configuration
  const defaultSettings = {
    apiKey: '',
    modelProvider: 'openrouter',
    modelName: 'nvidia/nemotron-3-ultra-550b-a55b:free',
    baseUrl: 'https://openrouter.ai/api/v1',
    embeddingProvider: 'mistral',
    embeddingModel: 'mistral-embed',
    embeddingBaseUrl: 'https://api.mistral.ai/v1',
    embeddingApiKey: '',
    embeddingDim: 1024,
    selectedDatabase: '',
    maxTokens: 2000,
    temperature: 0.7,
    availableModes: ['adaptive', 'hyper', 'hyper-lite', 'naive', 'graph', 'llm']
  }

  // Available query mode configurations
  const queryModes = [
    {
      value: 'adaptive',
      label: 'Adaptive RAG',
      icon: '🧠',
      description: 'Intelligent dynamic routing between Lite and Core Hyper-RAG'
    },
    { value: 'hyper', label: 'Hyper-RAG (Core)', icon: '⚡', description: 'Comprehensive hypergraph retrieval-augmented generation' },
    {
      value: 'hyper-lite',
      label: 'Hyper-RAG Lite',
      icon: '🔸',
      description: 'Fast lightweight hypergraph retrieval-augmented generation'
    },
    { value: 'naive', label: 'RAG', icon: '📚', description: 'Baseline vector retrieval-augmented generation' },
    { value: 'graph', label: 'Graph-RAG', icon: '🕸️', description: 'Graph-based retrieval-augmented generation' },
    { value: 'llm', label: 'LLM Direct', icon: '🤖', description: 'Direct LLM response without retrieval' }
  ]

  // LLM Model provider configuration
  const modelProviders = [
    {
      value: 'openrouter',
      label: 'OpenRouter (Project Default LLM)',
      models: [
        'nvidia/nemotron-3-ultra-550b-a55b:free',
        'mistralai/mistral-large-2407',
        'meta-llama/llama-3.3-70b-instruct',
        'deepseek/deepseek-chat',
        'anthropic/claude-3.5-sonnet'
      ],
      defaultBaseUrl: 'https://openrouter.ai/api/v1'
    },
    {
      value: 'openai',
      label: 'OpenAI',
      models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
      defaultBaseUrl: 'https://api.openai.com/v1'
    },
    {
      value: 'anthropic',
      label: 'Anthropic',
      models: ['claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307'],
      defaultBaseUrl: 'https://api.anthropic.com'
    },
    {
      value: 'custom',
      label: t('settings.custom_api') || 'Custom OpenAI-Compatible API',
      models: ['custom-model'],
      defaultBaseUrl: 'http://localhost:11434/v1'
    }
  ]

  // Embedding Provider configuration
  const embeddingProviders = [
    {
      value: 'mistral',
      label: 'Mistral AI (Embeddings Only, 1024 dimensions)',
      models: ['mistral-embed'],
      defaultBaseUrl: 'https://api.mistral.ai/v1',
      defaultDim: 1024
    },
    {
      value: 'openai',
      label: 'OpenAI Embeddings',
      models: ['text-embedding-3-small', 'text-embedding-3-large'],
      defaultBaseUrl: 'https://api.openai.com/v1',
      defaultDim: 1536
    },
    {
      value: 'custom',
      label: 'Custom Embedding API',
      models: ['custom-embed'],
      defaultBaseUrl: 'http://localhost:11434/v1',
      defaultDim: 1024
    }
  ]

  // Load settings from backend
  const loadSettings = async () => {
    setLoading(true)
    try {
      // First try loading Mode configuration from localStorage
      const localModeSettings = localStorage.getItem('hyperrag_mode_settings')
      let modeSettings = {}
      if (localModeSettings) {
        try {
          modeSettings = JSON.parse(localModeSettings)
        } catch (e) {
          console.error('Failed to parse local Mode settings:', e)
        }
      }

      const response = await fetch(`${SERVER_URL}/settings`)
      if (response.ok) {
        const settings = await response.json()
        const isLlmConfigured = !!settings.apiKeyConfigured || !!settings.openrouter_configured
        const llmPreview = settings.apiKeyPreview || settings.openrouter_key_preview || ''
        const isEmbConfigured = !!settings.embeddingApiKeyConfigured || !!settings.mistral_configured
        const embPreview = settings.embeddingApiKeyPreview || settings.mistral_key_preview || ''

        setApiKeyConfigured(isLlmConfigured)
        setApiKeyPreview(llmPreview)
        setEmbeddingApiKeyConfigured(isEmbConfigured)
        setEmbeddingApiKeyPreview(embPreview)

        form.setFieldsValue({
          ...defaultSettings,
          ...settings,
          apiKey: llmPreview ? llmPreview : '',
          embeddingApiKey: embPreview ? embPreview : '',
          ...modeSettings
        })
      } else {
        form.setFieldsValue({ ...defaultSettings, ...modeSettings })
      }
    } catch (error) {
      console.error('Failed to load settings:', error)
      message.warning(t('settings.load_failed') || 'Failed to load settings from server')
    } finally {
      setLoading(false)
    }
  }

  // Load available databases list
  const loadDatabases = async () => {
    try {
      const response = await fetch(`${SERVER_URL}/databases`)
      if (response.ok) {
        const databases = await response.json()
        setAvailableDatabases(databases)
      }
    } catch (error) {
      console.error('Failed to load database list:', error)
    }
  }

  // Save settings securely
  const saveSettings = async (values: any) => {
    setSaveLoading(true)
    try {
      const { availableModes, ...otherSettings } = values

      // Save Mode settings to localStorage (UI layout preferences only)
      const modeSettings = { availableModes }
      localStorage.setItem('hyperrag_mode_settings', JSON.stringify(modeSettings))

      // Clean payload: NEVER save raw API keys in localStorage
      const payload: any = {
        modelProvider: otherSettings.modelProvider,
        modelName: otherSettings.modelName,
        baseUrl: otherSettings.baseUrl,
        maxTokens: Number(otherSettings.maxTokens) || 2000,
        temperature: Number(otherSettings.temperature) || 0.7,
        embeddingProvider: otherSettings.embeddingProvider,
        embeddingModel: otherSettings.embeddingModel,
        embeddingBaseUrl: otherSettings.embeddingBaseUrl,
        embeddingDim: Number(otherSettings.embeddingDim) || 1024,
        selectedDatabase: otherSettings.selectedDatabase,
      }

      if (clearApiKeyRequested) {
        payload.clearApiKey = true
      } else if (otherSettings.apiKey && !otherSettings.apiKey.startsWith('••') && otherSettings.apiKey !== '***') {
        payload.apiKey = otherSettings.apiKey.trim()
      }

      if (clearEmbeddingApiKeyRequested) {
        payload.clearEmbeddingApiKey = true
      } else if (otherSettings.embeddingApiKey && !otherSettings.embeddingApiKey.startsWith('••') && otherSettings.embeddingApiKey !== '***') {
        payload.embeddingApiKey = otherSettings.embeddingApiKey.trim()
      }

      const response = await fetch(`${SERVER_URL}/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })

      const resData = await response.json()
      if (response.ok && resData.success !== false) {
        message.success(t('settings.save_success') || 'Settings saved successfully')
        setClearApiKeyRequested(false)
        setClearEmbeddingApiKeyRequested(false)
        await loadSettings()
      } else {
        throw new Error(resData.message || t('settings.save_failed'))
      }
    } catch (error: any) {
      console.error('Failed to save settings:', error)
      message.error(error.message || t('settings.backend_save_failed'))
    } finally {
      setSaveLoading(false)
    }
  }

  // Test LLM Connection
  const testLLMConnection = async () => {
    const values = form.getFieldsValue()
    const rawKey = values.apiKey
    const keyToSend = (rawKey && !rawKey.startsWith('••') && rawKey !== '***') ? rawKey.trim() : undefined

    if (!keyToSend && !apiKeyConfigured) {
      message.error(t('settings.api_key_required') || 'OpenRouter API key is not configured. Please enter your API key.')
      return
    }

    setTestResults(prev => ({ ...prev, llm: { status: 'testing' } }))
    try {
      const response = await fetch(`${SERVER_URL}/test-api`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          apiKey: keyToSend || '',
          baseUrl: values.baseUrl,
          modelName: values.modelName,
          modelProvider: values.modelProvider,
          testType: 'llm'
        })
      })

      const result = await response.json()
      if (response.ok && result.success) {
        setTestResults(prev => ({ ...prev, llm: { status: 'success', message: result.message } }))
        message.success(result.message || t('settings.api_test_success'))
      } else {
        setTestResults(prev => ({ ...prev, llm: { status: 'failed', message: result.message } }))
        message.error(result.message || t('settings.api_test_failed'))
      }
    } catch (error: any) {
      setTestResults(prev => ({ ...prev, llm: { status: 'failed', message: error.message } }))
      message.error(t('settings.api_test_failed') + ': ' + error.message)
    }
  }

  // Test Embedding Connection
  const testEmbeddingConnection = async () => {
    const values = form.getFieldsValue()
    const rawKey = values.embeddingApiKey
    const keyToSend = (rawKey && !rawKey.startsWith('••') && rawKey !== '***') ? rawKey.trim() : undefined

    if (!keyToSend && !embeddingApiKeyConfigured) {
      message.error('Mistral API key is not configured. Please enter your API key.')
      return
    }

    setTestResults(prev => ({ ...prev, embedding: { status: 'testing' } }))
    try {
      const response = await fetch(`${SERVER_URL}/test-api`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          apiKey: keyToSend || '',
          baseUrl: values.embeddingBaseUrl,
          modelName: values.embeddingModel,
          modelProvider: values.embeddingProvider || 'mistral',
          testType: 'embedding'
        })
      })

      const result = await response.json()
      if (response.ok && result.success) {
        setTestResults(prev => ({ ...prev, embedding: { status: 'success', message: result.message } }))
        message.success(result.message || 'Mistral embedding connection successful')
      } else {
        setTestResults(prev => ({ ...prev, embedding: { status: 'failed', message: result.message } }))
        message.error(result.message || 'Embedding connection test failed')
      }
    } catch (error: any) {
      setTestResults(prev => ({ ...prev, embedding: { status: 'failed', message: error.message } }))
      message.error('Embedding connection test failed: ' + error.message)
    }
  }

  // Clear / Remove LLM Key
  const handleClearLLMKey = () => {
    form.setFieldsValue({ apiKey: '' })
    setClearApiKeyRequested(true)
    setApiKeyConfigured(false)
    setApiKeyPreview('')
    message.info('OpenRouter API key marked for removal. Click "Save Settings" to persist.')
  }

  // Clear / Remove Embedding Key
  const handleClearEmbeddingKey = () => {
    form.setFieldsValue({ embeddingApiKey: '' })
    setClearEmbeddingApiKeyRequested(true)
    setEmbeddingApiKeyConfigured(false)
    setEmbeddingApiKeyPreview('')
    message.info('Mistral Embedding API key marked for removal. Click "Save Settings" to persist.')
  }

  // Reset settings to verified defaults
  const resetSettings = () => {
    form.setFieldsValue(defaultSettings)
    setTestResults({ llm: { status: 'idle' }, embedding: { status: 'idle' } })
    localStorage.removeItem('hyperrag_mode_settings')
    message.info(t('settings.reset_success') || 'Reset to default configuration')
  }

  // Provider change handlers
  const handleProviderChange = (value: string) => {
    const provider = modelProviders.find(p => p.value === value)
    if (provider) {
      form.setFieldsValue({
        baseUrl: provider.defaultBaseUrl,
        modelName: provider.models[0]
      })
    }
  }

  const handleEmbeddingProviderChange = (value: string) => {
    const provider = embeddingProviders.find(p => p.value === value)
    if (provider) {
      form.setFieldsValue({
        embeddingBaseUrl: provider.defaultBaseUrl,
        embeddingModel: provider.models[0],
        embeddingDim: provider.defaultDim
      })
    }
  }

  useEffect(() => {
    loadSettings()
    loadDatabases()
  }, [])

  return (
    <PageWrapper>
      <PageHeader
        title={t('settings.title') || 'Settings'}
        subtitle={t('settings.subtitle') || 'Configure OpenRouter LLM, Mistral Embeddings, and Query Modes'}
      />
      <div style={{ overflow: 'auto', flex: 1, padding: '24px', maxWidth: '1100px', margin: '0 auto', width: '100%' }}>
        <Card bordered={false} style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.05)', borderRadius: '12px' }}>
          <Form form={form} layout="vertical" onFinish={saveSettings} initialValues={defaultSettings}>
            {/* System Language Configuration */}
            <Card
              size="small"
              title={
                <span>
                  <GlobalOutlined style={{ marginRight: '8px', color: '#1677ff' }} />
                  {t('settings.system_config') || 'System Configuration'}
                </span>
              }
              style={{ marginBottom: '24px', borderRadius: '8px' }}
            >
              <Form.Item label={t('settings.language_select') || 'Select interface language'} style={{ marginBottom: 0 }}>
                <LanguageSelector />
              </Form.Item>
            </Card>

            {/* Section 1: LLM Provider Configuration */}
            <Card
              title={
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                  <span>
                    <ApiOutlined style={{ marginRight: '8px', color: '#6366f1' }} />
                    LLM Provider Configuration (Generation)
                  </span>
                  <div>
                    {apiKeyConfigured ? (
                      <Tag color="success" icon={<CheckCircleOutlined />}>
                        Configured: {apiKeyPreview}
                      </Tag>
                    ) : (
                      <Tag color="warning" icon={<CloseCircleOutlined />}>
                        Not Configured
                      </Tag>
                    )}
                  </div>
                </div>
              }
              style={{ marginBottom: '24px', borderRadius: '8px' }}
            >
              <Alert
                message="Authoritative LLM Configuration"
                description="OpenRouter serves as the primary LLM provider (NVIDIA Nemotron). Credentials entered here are stored securely server-side and used at runtime for all LLM calls."
                type="info"
                showIcon
                style={{ marginBottom: '20px' }}
              />

              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="modelProvider"
                    label={t('settings.model_provider') || 'LLM Provider'}
                    rules={[{ required: true, message: t('settings.provider_required') }]}
                  >
                    <Select onChange={handleProviderChange}>
                      {modelProviders.map(provider => (
                        <Option key={provider.value} value={provider.value}>
                          {provider.label}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="modelName"
                    label={t('settings.model_name') || 'Model Name'}
                    rules={[{ required: true, message: t('settings.model_required') }]}
                    extra="Project verified default: nvidia/nemotron-3-ultra-550b-a55b:free"
                  >
                    <AutoComplete
                      placeholder="e.g. nvidia/nemotron-3-ultra-550b-a55b:free"
                      allowClear
                      filterOption={(inputValue, option) =>
                        option!.value.toLowerCase().includes(inputValue.toLowerCase())
                      }
                      options={
                        form.getFieldValue('modelProvider')
                          ? modelProviders
                              .find(p => p.value === form.getFieldValue('modelProvider'))
                              ?.models.map(model => ({
                                value: model,
                                label: model
                              })) || []
                          : []
                      }
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="baseUrl"
                label={t('settings.api_base_url') || 'LLM API Base URL'}
                rules={[{ required: true, message: t('settings.base_url_required') }]}
              >
                <Input placeholder="https://openrouter.ai/api/v1" />
              </Form.Item>

              <Form.Item
                name="apiKey"
                label={
                  <Space>
                    <span>{t('settings.api_key') || 'OpenRouter API Key'}</span>
                    <SafetyCertificateOutlined style={{ color: '#52c41a' }} />
                  </Space>
                }
                extra={
                  apiKeyConfigured ? (
                    <span style={{ color: '#52c41a', fontSize: '13px' }}>
                      Key is configured on server ({apiKeyPreview}). Enter a new key only to update it.
                    </span>
                  ) : (
                    <span style={{ color: '#faad14', fontSize: '13px' }}>
                      No key configured. Please enter your OpenRouter API key to enable LLM responses.
                    </span>
                  )
                }
              >
                <Password
                  placeholder={apiKeyConfigured ? `Key configured (${apiKeyPreview}) — enter new key to replace` : "sk-or-v1-..."}
                  iconRender={visible => (visible ? <KeyOutlined /> : <KeyOutlined />)}
                />
              </Form.Item>

              <div style={{ marginBottom: '20px' }}>
                <Space wrap>
                  <Button
                    type="default"
                    icon={<ThunderboltOutlined />}
                    onClick={testLLMConnection}
                    loading={testResults.llm?.status === 'testing'}
                  >
                    Test LLM Connection
                  </Button>
                  {apiKeyConfigured && (
                    <Button
                      danger
                      type="dashed"
                      icon={<DeleteOutlined />}
                      onClick={handleClearLLMKey}
                    >
                      Clear / Remove LLM Key
                    </Button>
                  )}
                  {testResults.llm?.status === 'success' && (
                    <Text type="success" style={{ marginLeft: '8px' }}>
                      {testResults.llm.message || 'Connection successful'}
                    </Text>
                  )}
                  {testResults.llm?.status === 'failed' && (
                    <Text type="danger" style={{ marginLeft: '8px' }}>
                      {testResults.llm.message || 'Connection failed'}
                    </Text>
                  )}
                </Space>
              </div>

              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="maxTokens"
                    label={t('settings.max_tokens') || 'Max Tokens'}
                    rules={[{ required: true, message: t('settings.max_tokens_required') }]}
                  >
                    <Input type="number" min={1} max={8000} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="temperature"
                    label={t('settings.temperature') || 'Temperature'}
                    rules={[{ required: true, message: t('settings.temperature_required') }]}
                  >
                    <Input type="number" min={0} max={2} step={0.1} />
                  </Form.Item>
                </Col>
              </Row>
            </Card>

            {/* Section 2: Embedding Provider Configuration */}
            <Card
              title={
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                  <span>
                    <DatabaseOutlined style={{ marginRight: '8px', color: '#059669' }} />
                    Embedding Provider Configuration (Retrieval & Indexing)
                  </span>
                  <div>
                    {embeddingApiKeyConfigured ? (
                      <Tag color="success" icon={<CheckCircleOutlined />}>
                        Configured: {embeddingApiKeyPreview}
                      </Tag>
                    ) : (
                      <Tag color="warning" icon={<CloseCircleOutlined />}>
                        Not Configured
                      </Tag>
                    )}
                  </div>
                </div>
              }
              style={{ marginBottom: '24px', borderRadius: '8px' }}
            >
              <Alert
                message="Authoritative Embedding Configuration (Mistral AI — 1024 Dimensions)"
                description="Mistral AI (mistral-embed) is the dedicated embedding provider. It generates the exact 1024-dimensional vectors required for hypergraph entity/relation indices."
                type="info"
                showIcon
                style={{ marginBottom: '20px' }}
              />

              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="embeddingProvider"
                    label="Embedding Provider"
                    rules={[{ required: true, message: 'Please select embedding provider' }]}
                  >
                    <Select onChange={handleEmbeddingProviderChange}>
                      {embeddingProviders.map(p => (
                        <Option key={p.value} value={p.value}>
                          {p.label}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item
                    name="embeddingModel"
                    label="Embedding Model"
                    rules={[{ required: true, message: 'Please enter embedding model' }]}
                    extra="Project verified default: mistral-embed"
                  >
                    <AutoComplete
                      placeholder="mistral-embed"
                      allowClear
                      options={
                        form.getFieldValue('embeddingProvider')
                          ? embeddingProviders
                              .find(p => p.value === form.getFieldValue('embeddingProvider'))
                              ?.models.map(m => ({ value: m, label: m })) || []
                          : []
                      }
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} md={16}>
                  <Form.Item
                    name="embeddingBaseUrl"
                    label="Embedding API Base URL"
                    rules={[{ required: true, message: 'Please enter embedding base URL' }]}
                  >
                    <Input placeholder="https://api.mistral.ai/v1" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    name="embeddingDim"
                    label="Embedding Dimension"
                    rules={[{ required: true, message: 'Please enter embedding dimension' }]}
                    extra="Must be 1024 for Mistral"
                  >
                    <Input type="number" disabled />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="embeddingApiKey"
                label={
                  <Space>
                    <span>Mistral Embedding API Key</span>
                    <SafetyCertificateOutlined style={{ color: '#52c41a' }} />
                  </Space>
                }
                extra={
                  embeddingApiKeyConfigured ? (
                    <span style={{ color: '#52c41a', fontSize: '13px' }}>
                      Embedding key configured on server ({embeddingApiKeyPreview}). Enter a new key only to replace it.
                    </span>
                  ) : (
                    <span style={{ color: '#faad14', fontSize: '13px' }}>
                      No key configured. Please enter your Mistral API key for vector search and file embedding.
                    </span>
                  )
                }
              >
                <Password
                  placeholder={embeddingApiKeyConfigured ? `Key configured (${embeddingApiKeyPreview}) — enter new key to replace` : "Enter Mistral API Key"}
                  iconRender={visible => (visible ? <KeyOutlined /> : <KeyOutlined />)}
                />
              </Form.Item>

              <div style={{ marginBottom: '10px' }}>
                <Space wrap>
                  <Button
                    type="default"
                    icon={<ThunderboltOutlined />}
                    onClick={testEmbeddingConnection}
                    loading={testResults.embedding?.status === 'testing'}
                  >
                    Test Embedding Connection
                  </Button>
                  {embeddingApiKeyConfigured && (
                    <Button
                      danger
                      type="dashed"
                      icon={<DeleteOutlined />}
                      onClick={handleClearEmbeddingKey}
                    >
                      Clear / Remove Embedding Key
                    </Button>
                  )}
                  {testResults.embedding?.status === 'success' && (
                    <Text type="success" style={{ marginLeft: '8px' }}>
                      {testResults.embedding.message || 'Connection successful'}
                    </Text>
                  )}
                  {testResults.embedding?.status === 'failed' && (
                    <Text type="danger" style={{ marginLeft: '8px' }}>
                      {testResults.embedding.message || 'Connection failed'}
                    </Text>
                  )}
                </Space>
              </div>
            </Card>

            {/* Section 3: Query Mode Configuration */}
            <Card
              title={
                <span>
                  <AppstoreOutlined style={{ marginRight: '8px', color: '#d97706' }} />
                  Query Mode Configuration
                </span>
              }
              style={{ marginBottom: '24px', borderRadius: '8px' }}
            >
              <Alert
                message="Query Modes"
                description="Select query modes displayed in the chat interface. Preferences are remembered in browser."
                type="info"
                showIcon
                style={{ marginBottom: '20px' }}
              />

              <Form.Item name="availableModes" style={{ marginBottom: 0 }}>
                <Checkbox.Group style={{ width: '100%' }}>
                  <Row gutter={[16, 16]}>
                    {queryModes.map(mode => (
                      <Col xs={24} sm={12} key={mode.value}>
                        <Card size="small" style={{ height: '100%', borderColor: '#e2e8f0', borderRadius: '8px' }}>
                          <Checkbox value={mode.value} style={{ width: '100%' }}>
                            <div style={{ marginLeft: '8px' }}>
                              <div style={{ fontWeight: 600, fontSize: '14px' }}>
                                <span style={{ marginRight: '6px' }}>{mode.icon}</span>
                                {mode.label}
                              </div>
                              <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                                {mode.description}
                              </div>
                            </div>
                          </Checkbox>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </Checkbox.Group>
              </Form.Item>
            </Card>

            <Divider />

            {/* Form Actions */}
            <Form.Item style={{ marginBottom: 0 }}>
              <Space size="middle">
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SaveOutlined />}
                  loading={saveLoading}
                  size="large"
                  style={{ minWidth: '160px', height: '42px', fontWeight: 600 }}
                >
                  {t('settings.save_settings') || 'Save Settings'}
                </Button>
                <Button
                  type="default"
                  onClick={resetSettings}
                  icon={<ReloadOutlined />}
                  size="large"
                  style={{ height: '42px' }}
                >
                  {t('settings.reset_settings') || 'Reset Defaults'}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </PageWrapper>
  )
}

export default Setting
