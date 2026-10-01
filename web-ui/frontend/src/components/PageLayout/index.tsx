import React from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
}

/**
 * Consistent page header for interior pages
 */
export const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, actions }) => (
  <div
    style={{
      padding: '20px 24px 16px',
      borderBottom: '1px solid var(--border-subtle)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: 'var(--surface-base)',
      flexShrink: 0,
    }}
  >
    <div>
      <h1
        style={{
          margin: 0,
          fontSize: '18px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
          lineHeight: 1.3,
        }}
      >
        {title}
      </h1>
      {subtitle && (
        <p
          style={{
            margin: '2px 0 0',
            fontSize: '13px',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
          }}
        >
          {subtitle}
        </p>
      )}
    </div>
    {actions && (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {actions}
      </div>
    )}
  </div>
)

interface PageBodyProps {
  children: React.ReactNode
  padding?: string
}

/**
 * Page body with consistent padding
 */
export const PageBody: React.FC<PageBodyProps> = ({ children, padding = '24px' }) => (
  <div
    style={{
      padding,
      overflow: 'auto',
      height: '100%',
    }}
  >
    {children}
  </div>
)

interface PageWrapperProps {
  children: React.ReactNode
}

/**
 * Full-height page wrapper
 */
export const PageWrapper: React.FC<PageWrapperProps> = ({ children }) => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
    }}
  >
    {children}
  </div>
)
