import React, { useState, useRef } from 'react';
import { Modal, Button, Input, Tag, Alert, Progress, Space, Typography, Tooltip } from 'antd';
import {
  UploadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  LoadingOutlined,
  EyeOutlined
} from '@ant-design/icons';
import { SERVER_URL } from '../../utils';
import { storeGlobalUser } from '../../store/globalUser';

const { Text, Title, Paragraph } = Typography;

interface UploadKnowledgeModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: (databaseName: string) => void;
}

export const UploadKnowledgeModal: React.FC<UploadKnowledgeModalProps> = ({
  visible,
  onClose,
  onSuccess
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isPreflightLoading, setIsPreflightLoading] = useState(false);
  const [preflightReport, setPreflightReport] = useState<any>(null);
  const [customDbName, setCustomDbName] = useState<string>('');
  const [maxRecords, setMaxRecords] = useState<number>(50);

  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStage, setCurrentStage] = useState<'idle' | 'uploading' | 'inspecting' | 'parsing' | 'preparing' | 'indexing' | 'ready' | 'failed'>('idle');
  const [stageMessage, setStageMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [resultData, setResultData] = useState<any>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetState = () => {
    setSelectedFile(null);
    setIsPreflightLoading(false);
    setPreflightReport(null);
    setCustomDbName('');
    setIsProcessing(false);
    setCurrentStage('idle');
    setStageMessage('');
    setErrorMessage('');
    setResultData(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    if (!isProcessing) {
      resetState();
      onClose();
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) {
      return;
    }

    setSelectedFile(file);
    setErrorMessage('');
    setPreflightReport(null);
    setIsPreflightLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const resp = await fetch(`${SERVER_URL}/ingestion/preflight`, {
        method: 'POST',
        body: formData
      });

      const data = await resp.json();
      if (data.success && data.report) {
        setPreflightReport(data.report);
        setCustomDbName(data.report.suggested_database_name || '');
      } else {
        setErrorMessage(data.error || data.report?.error_message || 'Preflight inspection failed');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to inspect file');
    } finally {
      setIsPreflightLoading(false);
    }
  };

  const handleUploadAndProcess = async () => {
    if (!selectedFile) {
      return;
    }

    setIsProcessing(true);
    setCurrentStage('uploading');
    setStageMessage('Uploading raw document to server...');
    setErrorMessage('');

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (customDbName.trim()) {
        formData.append('database_name', customDbName.trim());
      }
      formData.append('max_records', String(maxRecords));

      // Visual stage progression timer for responsive user feedback
      const timer1 = setTimeout(() => {
        setCurrentStage('inspecting');
        setStageMessage('Automatically inspecting structure & data types...');
      }, 800);

      const timer2 = setTimeout(() => {
        setCurrentStage('preparing');
        setStageMessage('Normalizing records & synthesizing retrieval contexts...');
      }, 2200);

      const timer3 = setTimeout(() => {
        setCurrentStage('indexing');
        setStageMessage('Generating Mistral embeddings & extracting hypergraph entities...');
      }, 4000);

      const resp = await fetch(`${SERVER_URL}/ingestion/upload-and-process`, {
        method: 'POST',
        body: formData
      });

      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);

      const data = await resp.json();

      if (data.success) {
        setCurrentStage('ready');
        setStageMessage(`Knowledge base '${data.database_name}' successfully built!`);
        setResultData(data);

        // Refresh databases in global state and select newly created database
        await storeGlobalUser.loadDatabases();
        storeGlobalUser.setSelectedDatabase(data.database_name);

        if (onSuccess) {
          onSuccess(data.database_name);
        }
      } else {
        setCurrentStage('failed');
        setErrorMessage(data.error || 'Ingestion failed');
      }
    } catch (err: any) {
      setCurrentStage('failed');
      setErrorMessage(err.message || 'Network error during ingestion');
    } finally {
      setIsProcessing(false);
    }
  };

  const renderStageIndicator = () => {
    const stages = [
      { key: 'uploading', label: 'Upload' },
      { key: 'inspecting', label: 'Inspect' },
      { key: 'preparing', label: 'Normalize' },
      { key: 'indexing', label: 'Index' },
      { key: 'ready', label: 'Ready' }
    ];

    const currentIdx = stages.findIndex(s => s.key === currentStage);

    return (
      <div style={{ margin: '20px 0', padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          {stages.map((s, idx) => {
            const isDone = currentStage === 'ready' || currentIdx > idx;
            const isCurrent = currentStage === s.key;
            return (
              <div key={s.key} style={{ textAlign: 'center', flex: 1 }}>
                <div style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  margin: '0 auto 4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  background: isDone ? '#10b981' : isCurrent ? '#3b82f6' : '#e2e8f0',
                  color: isDone || isCurrent ? '#fff' : '#64748b'
                }}>
                  {isDone ? '✓' : idx + 1}
                </div>
                <Text style={{ fontSize: '11px', color: isCurrent ? '#1d4ed8' : '#64748b', fontWeight: isCurrent ? 'bold' : 'normal' }}>
                  {s.label}
                </Text>
              </div>
            );
          })}
        </div>
        <div style={{ textAlign: 'center', marginTop: '12px' }}>
          <Space>
            {isProcessing && <LoadingOutlined style={{ color: '#3b82f6' }} />}
            <Text style={{ color: currentStage === 'failed' ? '#ef4444' : '#334155', fontWeight: 500 }}>
              {stageMessage || (currentStage === 'failed' ? 'Process encountered an error' : 'Ready')}
            </Text>
          </Space>
        </div>
      </div>
    );
  };

  return (
    <Modal
      title={
        <Space align="center">
          <DatabaseOutlined style={{ color: '#3b82f6', fontSize: '20px' }} />
          <span style={{ fontSize: '18px', fontWeight: 600 }}>Upload Knowledge Base</span>
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      footer={null}
      width={640}
      destroyOnClose
    >
      <div style={{ padding: '8px 0' }}>
        <Paragraph type="secondary" style={{ marginBottom: '16px', fontSize: '13px' }}>
          Upload any document or raw dataset. Hyper-RAG automatically inspects its structure, normalizes records,
          synthesizes retrieval contexts, and builds an isolated vector and hypergraph knowledge base.
        </Paragraph>

        <div style={{ marginBottom: '16px' }}>
          <Text strong style={{ fontSize: '12px', marginRight: '8px' }}>Supported formats:</Text>
          <Tag color="blue">JSON</Tag>
          <Tag color="cyan">JSONL</Tag>
          <Tag color="green">CSV</Tag>
          <Tag color="purple">TXT</Tag>
          <Tag color="magenta">MD</Tag>
          <Tag color="orange">PDF</Tag>
          <Tag color="geekblue">DOCX</Tag>
        </div>

        {/* Dropzone / Picker */}
        {currentStage === 'idle' && (
          <div
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: '2px dashed #93c5fd',
              borderRadius: '12px',
              padding: '28px 16px',
              textAlign: 'center',
              cursor: 'pointer',
              background: '#f0f9ff',
              transition: 'all 0.2s ease',
              marginBottom: '16px'
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileChange}
              style={{ display: 'none' }}
              accept=".json,.jsonl,.csv,.txt,.md,.pdf,.docx"
            />
            <UploadOutlined style={{ fontSize: '32px', color: '#2563eb', marginBottom: '8px' }} />
            <div>
              <Text strong style={{ fontSize: '15px', color: '#1e293b' }}>
                {selectedFile ? selectedFile.name : 'Click to select or drop a dataset file'}
              </Text>
            </div>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {selectedFile
                ? `${(selectedFile.size / 1024).toFixed(1)} KB — Click to change`
                : 'Supports arbitrary structured data or text documents'}
            </Text>
          </div>
        )}

        {/* Preflight Loading */}
        {isPreflightLoading && (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <LoadingOutlined style={{ fontSize: '24px', color: '#3b82f6', marginBottom: '8px' }} />
            <div><Text type="secondary">Inspecting structure & schema locally (zero API calls)...</Text></div>
          </div>
        )}

        {/* Preflight Inspection Report */}
        {preflightReport && currentStage === 'idle' && (
          <div style={{
            background: '#ffffff',
            borderRadius: '10px',
            border: '1px solid #cbd5e1',
            padding: '16px',
            marginBottom: '16px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <Space>
                <FileTextOutlined style={{ color: '#0284c7', fontSize: '16px' }} />
                <Text strong style={{ fontSize: '14px' }}>Preflight Inspection Report</Text>
              </Space>
              <Tag color="success">✓ Verified Compatible</Tag>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginBottom: '12px', fontSize: '13px' }}>
              <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: '6px' }}>
                <Text type="secondary">File Format:</Text> <Text strong>{preflightReport.file_type.toUpperCase()}</Text>
              </div>
              <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: '6px' }}>
                <Text type="secondary">Records Detected:</Text> <Text strong>{preflightReport.record_count}</Text>
              </div>
              <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: '6px' }}>
                <Text type="secondary">Estimated Contexts:</Text> <Text strong>{preflightReport.estimated_contexts}</Text>
              </div>
              <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: '6px' }}>
                <Text type="secondary">Embedding Dim:</Text> <Text strong>1024 (Mistral)</Text>
              </div>
            </div>

            {preflightReport.schema && (
              <div style={{ marginBottom: '12px', fontSize: '12px' }}>
                <Text type="secondary">Inferred Key Fields: </Text>
                {preflightReport.schema.title_fields?.map((f: string) => (
                  <Tag key={f} color="cyan" style={{ fontSize: '11px' }}>title: {f}</Tag>
                ))}
                {preflightReport.schema.identifier_fields?.map((f: string) => (
                  <Tag key={f} color="purple" style={{ fontSize: '11px' }}>id: {f}</Tag>
                ))}
                {preflightReport.schema.categorical_fields?.slice(0, 3).map((f: string) => (
                  <Tag key={f} color="default" style={{ fontSize: '11px' }}>{f}</Tag>
                ))}
              </div>
            )}

            <div style={{ marginTop: '12px' }}>
              <Text strong style={{ fontSize: '12px', display: 'block', marginBottom: '4px' }}>
                Target Knowledge Base Name:
              </Text>
              <Input
                prefix={<DatabaseOutlined style={{ color: '#64748b' }} />}
                value={customDbName}
                onChange={e => setCustomDbName(e.target.value)}
                placeholder="database_name"
                disabled={isProcessing}
                style={{ borderRadius: '6px' }}
              />
              <Text type="secondary" style={{ fontSize: '11px', marginTop: '2px', display: 'block' }}>
                Isolated index will be created under hyperrag_cache/{customDbName || '...'}
              </Text>
            </div>
          </div>
        )}

        {/* Progress Display */}
        {currentStage !== 'idle' && renderStageIndicator()}

        {/* Error Alert */}
        {errorMessage && (
          <Alert
            message="Ingestion Error"
            description={errorMessage}
            type="error"
            showIcon
            style={{ marginBottom: '16px' }}
          />
        )}

        {/* Success Confirmation */}
        {currentStage === 'ready' && resultData && (
          <div style={{
            background: '#ecfdf5',
            border: '1px solid #6ee7b7',
            borderRadius: '10px',
            padding: '16px',
            textAlign: 'center',
            marginBottom: '16px'
          }}>
            <CheckCircleOutlined style={{ fontSize: '36px', color: '#10b981', marginBottom: '8px' }} />
            <Title level={4} style={{ color: '#065f46', marginBottom: '4px' }}>
              Knowledge Base Ready!
            </Title>
            <Paragraph style={{ color: '#047857', fontSize: '13px', marginBottom: '16px' }}>
              Successfully indexed <strong>{resultData.records_indexed}</strong> records into{' '}
              <strong>{resultData.database_name}</strong>. The database is now selected and available for query!
            </Paragraph>
            <Button
              type="primary"
              size="large"
              onClick={handleClose}
              style={{ background: '#059669', borderColor: '#059669', borderRadius: '6px' }}
            >
              Start Asking Questions
            </Button>
          </div>
        )}

        {/* Action Buttons */}
        {currentStage !== 'ready' && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
            <Button onClick={handleClose} disabled={isProcessing}>
              Cancel
            </Button>
            <Button
              type="primary"
              onClick={handleUploadAndProcess}
              disabled={!selectedFile || isProcessing || isPreflightLoading || !!errorMessage}
              loading={isProcessing}
              icon={<ThunderboltOutlined />}
              style={{ borderRadius: '6px' }}
            >
              {isProcessing ? 'Ingesting...' : 'Upload & Ingest'}
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default UploadKnowledgeModal;
