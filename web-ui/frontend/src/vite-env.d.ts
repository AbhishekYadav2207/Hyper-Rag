/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MODE: string
  readonly SERVER_URL: string
  readonly VITE_APP_URL: string
  // Additional environment variables...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface Window {
  COS: any
}
