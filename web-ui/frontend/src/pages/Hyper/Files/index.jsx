import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Upload,
  FileText,
  Trash2,
  CheckCircle,
  AlertCircle,
  Clock,
  RefreshCw,
  Play,
  X,
  ChevronRight,
  Database,
  HardDrive,
  Terminal,
} from 'lucide-react';
import { SERVER_URL } from '../../../utils/index';

const DocumentManager = () => {
  const { t } = useTranslation();
  const [files, setFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isEmbedding, setIsEmbedding] = useState(false);
  const [embeddingProgress, setEmbeddingProgress] = useState({});
  const [notification, setNotification] = useState(null);
  const [progressDetails, setProgressDetails] = useState({});
  const [logs, setLogs] = useState([]);
  const [showLogs, setShowLogs] = useState(false);
  const fileInputRef = useRef(null);
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  useEffect(() => {
    fetchFiles();
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const wsUrl = SERVER_URL.replace('http', 'ws') + '/ws';
      wsRef.current = new WebSocket(wsUrl);
      wsRef.current.onopen = () => console.log('WebSocket connected');
      wsRef.current.onmessage = (event) => {
        try {
          handleProgressUpdate(JSON.parse(event.data));
        } catch (e) {
          console.error('WS parse error', e);
        }
      };
      wsRef.current.onclose = () => setTimeout(connectWebSocket, 3000);
      wsRef.current.onerror = (e) => console.error('WS error', e);
    } catch (e) {
      console.error('WS connect failed', e);
    }
  };

  const handleProgressUpdate = (data) => {
    switch (data.type) {
      case 'progress':
        setEmbeddingProgress(prev => ({ ...prev, current: data.current, total: data.total, percentage: data.percentage, message: data.message }));
        break;
      case 'file_processing':
        setProgressDetails(prev => ({ ...prev, [data.file_id]: { filename: data.filename, stage: data.stage, message: data.message } }));
        break;
      case 'file_completed':
        setProgressDetails(prev => { const u = { ...prev }; delete u[data.file_id]; return u; });
        setFiles(prev => prev.map(f => f.file_id === data.file_id ? { ...f, status: 'embedded' } : f));
        break;
      case 'file_error':
        setProgressDetails(prev => ({ ...prev, [data.file_id]: { error: data.error, message: `Error: ${data.error}` } }));
        setFiles(prev => prev.map(f => f.file_id === data.file_id ? { ...f, status: 'error' } : f));
        break;
      case 'all_completed':
        setIsEmbedding(false);
        setEmbeddingProgress({});
        setProgressDetails({});
        setSelectedFiles(new Set());
        showNotification(t('files.all_completed'), 'success');
        fetchFiles();
        break;
      case 'error':
        setIsEmbedding(false);
        setEmbeddingProgress({});
        setProgressDetails({});
        showNotification(data.error, 'error');
        break;
      case 'log':
        setLogs(prev => [...prev.slice(-49), { id: Date.now() + Math.random(), timestamp: new Date(data.timestamp * 1000).toLocaleTimeString(), level: data.level, message: data.message }]);
        setTimeout(() => logsEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
        break;
      default: break;
    }
  };

  const fetchFiles = async () => {
    try {
      const res = await fetch(`${SERVER_URL}/files`);
      const data = await res.json();
      setFiles(data.files || []);
    } catch {
      showNotification(t('files.fetch_files_failed'), 'error');
    }
  };

  const showNotification = (message, type = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const handleFileSelect = (e) => uploadFiles(Array.from(e.target.files));
  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e) => { e.preventDefault(); setIsDragging(false); uploadFiles(Array.from(e.dataTransfer.files)); };

  const uploadFiles = async (filesToUpload) => {
    if (!filesToUpload.length) return;
    setIsUploading(true);
    const formData = new FormData();
    filesToUpload.forEach(f => formData.append('files', f));
    try {
      const res = await fetch(`${SERVER_URL}/files/upload`, { method: 'POST', body: formData });
      const data = await res.json();
      if (data.files) {
        const ok = data.files.filter(f => f.status === 'uploaded').length;
        const err = data.files.filter(f => f.status === 'error').length;
        if (ok > 0) { showNotification(t('files.upload_success', { count: ok }), 'success'); fetchFiles(); }
        if (err > 0) showNotification(t('files.upload_failed', { count: err }), 'error');
      }
    } catch {
      showNotification(t('files.upload_error'), 'error');
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileSelection = (fileId) => {
    const s = new Set(selectedFiles);
    if (s.has(fileId)) s.delete(fileId); else s.add(fileId);
    setSelectedFiles(s);
  };

  const handleSelectAll = () => {
    setSelectedFiles(selectedFiles.size === files.length ? new Set() : new Set(files.map(f => f.file_id)));
  };

  const handleEmbedDocuments = async () => {
    if (!selectedFiles.size) { showNotification(t('files.select_files_first'), 'warning'); return; }
    setIsEmbedding(true);
    setEmbeddingProgress({});
    setProgressDetails({});
    setLogs([]);
    setShowLogs(true);
    try {
      const res = await fetch(`${SERVER_URL}/files/embed-with-progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_ids: Array.from(selectedFiles), chunk_size: 1000, chunk_overlap: 200 }),
      });
      const data = await res.json();
      if (data.processing) {
        showNotification(t('files.start_processing', { count: data.total_files }), 'info');
      } else {
        setIsEmbedding(false);
        showNotification(t('files.processing_failed'), 'error');
      }
    } catch {
      setIsEmbedding(false);
      showNotification(t('files.embedding_failed'), 'error');
    }
  };

  const handleDeleteFile = async (fileId) => {
    try {
      const res = await fetch(`${SERVER_URL}/files/${fileId}`, { method: 'DELETE' });
      if (res.ok) {
        showNotification(t('files.delete_success'), 'success');
        fetchFiles();
        setSelectedFiles(prev => { const s = new Set(prev); s.delete(fileId); return s; });
      }
    } catch {
      showNotification(t('files.delete_failed'), 'error');
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatDate = (ds) => new Date(ds).toLocaleString();

  const getStatusBadge = (status) => {
    if (status === 'embedded') return <span className="badge badge-green"><CheckCircle size={10} /> Indexed</span>;
    if (status === 'uploaded') return <span className="badge badge-blue"><Clock size={10} /> Uploaded</span>;
    if (status === 'error') return <span className="badge badge-red"><AlertCircle size={10} /> Error</span>;
    return <span className="badge badge-gray">{status}</span>;
  };

  return (
    <div style={{ padding: '24px', maxWidth: '960px', margin: '0 auto' }}>
      {/* Toast */}
      {notification && (
        <div className={`toast toast-${notification.type}`} role="alert">
          {notification.message}
        </div>
      )}

      {/* Upload Section */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 4px', letterSpacing: '-0.02em' }}>
          {t('files.upload_document')}
        </h1>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 16px' }}>
          Upload documents to embed into the knowledge base vector store.
        </p>

        <div
          className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Upload documents"
          onKeyDown={e => e.key === 'Enter' && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            accept=".txt,.pdf,.docx,.md,.json,.jsonl,.csv"
          />
          <div className="upload-dropzone-icon">
            <Upload size={20} />
          </div>
          {isUploading ? (
            <>
              <div className="upload-dropzone-title">Uploading…</div>
              <div className="upload-dropzone-subtitle">Please wait</div>
            </>
          ) : isDragging ? (
            <>
              <div className="upload-dropzone-title">Release to upload</div>
              <div className="upload-dropzone-subtitle">Drop your files here</div>
            </>
          ) : (
            <>
              <div className="upload-dropzone-title">{t('files.drag_drop_files')}</div>
              <div className="upload-dropzone-subtitle">{t('files.supported_formats')}</div>
            </>
          )}
          <div className="upload-format-chips">
            {['TXT', 'PDF', 'DOCX', 'MD', 'JSON', 'JSONL', 'CSV'].map(f => (
              <span key={f} className="upload-format-chip">.{f.toLowerCase()}</span>
            ))}
          </div>
        </div>
      </div>

      {/* File List */}
      <div className="page-section">
        <div className="page-section-header">
          <div>
            <h2 className="page-section-title">{t('files.document_list')}</h2>
            {files.length > 0 && (
              <p className="page-section-subtitle">{files.length} document{files.length !== 1 ? 's' : ''} · {selectedFiles.size} selected</p>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {files.length > 0 && (
              <button className="btn btn-ghost btn-sm" onClick={handleSelectAll}>
                {selectedFiles.size === files.length ? 'Deselect all' : 'Select all'}
              </button>
            )}
            {isEmbedding && (
              <button
                className="btn btn-danger btn-sm"
                onClick={() => { setIsEmbedding(false); setEmbeddingProgress({}); setProgressDetails({}); showNotification(t('files.processing_cancelled'), 'warning'); }}
              >
                <X size={13} /> Cancel
              </button>
            )}
            <button
              className="btn btn-primary btn-sm"
              onClick={handleEmbedDocuments}
              disabled={selectedFiles.size === 0 || isEmbedding}
              style={{ minWidth: '120px' }}
            >
              {isEmbedding ? (
                <><span className="spinner" /> Embedding…</>
              ) : (
                <><Play size={13} /> Embed ({selectedFiles.size})</>
              )}
            </button>
          </div>
        </div>

        {/* Embedding Progress */}
        {isEmbedding && embeddingProgress.total && (
          <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-raised)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              <span>{embeddingProgress.message || 'Processing…'}</span>
              <span>{embeddingProgress.current}/{embeddingProgress.total} ({embeddingProgress.percentage || 0}%)</span>
            </div>
            <div style={{ height: '4px', background: 'var(--neutral-200)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ height: '100%', background: 'var(--brand-500)', borderRadius: '2px', width: `${embeddingProgress.percentage || 0}%`, transition: 'width 0.3s' }} />
            </div>
          </div>
        )}

        {/* Table */}
        {files.length === 0 ? (
          <div style={{ padding: '64px 24px', textAlign: 'center' }}>
            <HardDrive size={32} style={{ color: 'var(--neutral-300)', margin: '0 auto 12px', display: 'block' }} />
            <p style={{ color: 'var(--text-tertiary)', fontSize: '14px', margin: 0 }}>{t('files.no_documents')}</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
                    <input
                      type="checkbox"
                      checked={selectedFiles.size === files.length && files.length > 0}
                      onChange={handleSelectAll}
                      aria-label="Select all files"
                    />
                  </th>
                  <th>{t('files.filename')}</th>
                  <th>{t('files.database')}</th>
                  <th>{t('files.size')}</th>
                  <th>{t('files.upload_time')}</th>
                  <th>{t('files.status')}</th>
                  <th>{t('files.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {files.map(file => (
                  <tr key={file.file_id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedFiles.has(file.file_id)}
                        onChange={() => handleFileSelection(file.file_id)}
                        aria-label={`Select ${file.filename}`}
                      />
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <FileText size={14} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
                        <span style={{ fontWeight: 500 }}>{file.filename}</span>
                        {progressDetails[file.file_id] && (
                          <span style={{ fontSize: '11px', color: 'var(--brand-600)' }}>
                            {progressDetails[file.file_id].stage || 'processing'}…
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-gray">
                        <Database size={10} />
                        {file.database_name || t('files.default_db')}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>{formatFileSize(file.file_size)}</td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>{formatDate(file.upload_time)}</td>
                    <td>{getStatusBadge(file.status)}</td>
                    <td>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => handleDeleteFile(file.file_id)}
                        style={{ color: 'var(--error-500)' }}
                        aria-label={`Delete ${file.filename}`}
                      >
                        <Trash2 size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Logs Panel */}
      {(isEmbedding || showLogs) && logs.length > 0 && (
        <div className="page-section">
          <div className="page-section-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={14} style={{ color: 'var(--text-tertiary)' }} />
              <h3 className="page-section-title">{t('files.processing_logs')}</h3>
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setLogs([])}>
                {t('files.clear_logs')}
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowLogs(v => !v)}>
                {showLogs ? t('files.hide_logs') : t('files.show_logs')}
              </button>
            </div>
          </div>
          {showLogs && (
            <div style={{ background: 'var(--neutral-900)', padding: '16px', maxHeight: '280px', overflowY: 'auto', fontFamily: 'var(--font-mono)', fontSize: '12px', lineHeight: 1.6 }}>
              {logs.map(log => (
                <div key={log.id} style={{ color: log.level === 'ERROR' ? '#f87171' : log.level === 'WARNING' ? '#fbbf24' : '#d1d5db', marginBottom: '2px' }}>
                  <span style={{ color: '#6b7280', marginRight: '8px' }}>{log.timestamp}</span>
                  {log.message}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DocumentManager;
