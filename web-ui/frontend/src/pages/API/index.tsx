import React, { useState } from 'react'
import { Alert } from 'antd'
import { SERVER_URL } from '../../utils'
import { PageWrapper, PageHeader } from '../../components/PageLayout'
import { Code2 } from 'lucide-react'

const APIPage = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  return (
    <PageWrapper>
      <PageHeader
        title="API Documentation"
        subtitle={`Interactive API reference — connected to ${SERVER_URL}/docs`}
      />
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {error && (
          <Alert
            message="Failed to load API documentation"
            description={`Please ensure the backend service is running at ${SERVER_URL}`}
            type="error"
            showIcon
            style={{ margin: 16 }}
          />
        )}
        {loading && !error && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              color: 'var(--text-tertiary)',
              fontSize: '14px',
            }}
          >
            <Code2 size={32} style={{ opacity: 0.3 }} />
            <span>Loading API documentation…</span>
          </div>
        )}
        <iframe
          src={`${SERVER_URL}/docs`}
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            display: error ? 'none' : 'block',
          }}
          onLoad={() => setLoading(false)}
          onError={() => {
            setLoading(false)
            setError(true)
          }}
          title="API Documentation"
        />
      </div>
    </PageWrapper>
  )
}

export default APIPage