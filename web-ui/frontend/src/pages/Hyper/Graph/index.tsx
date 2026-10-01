import React, { useEffect, useState } from 'react';
import { Select, Card, Tag, Spin } from 'antd';
import { observer } from 'mobx-react';
import { useTranslation } from 'react-i18next';
import { storeGlobalUser } from '../../../store/globalUser';
import HyperGraph from '../../../components/HyperGraph';
import DatabaseSelector from '../../../components/DatabaseSelector';
import { PageWrapper, PageHeader } from '../../../components/PageLayout';
import { DatabaseOutlined } from '@ant-design/icons';
import { SERVER_URL } from '../../../utils';

const GraphPage = () => {
  const { t } = useTranslation();
  const [keys, setKeys] = useState(undefined);
  const [key, setKey] = useState(undefined);
  const [loading, setLoading] = useState(false);
  const [item, setItem] = useState({
    entity_name: '',
    entity_type: '',
    descriptions: [''],
    properties: ['']
  });
  const [verticesList, setVerticesList] = useState([]);
  const [verticesPage, setVerticesPage] = useState(1);
  const [verticesTotal, setVerticesTotal] = useState(0);
  const [verticesLoading, setVerticesLoading] = useState(false);

  // Initialize database
  useEffect(() => {
    storeGlobalUser.restoreSelectedDatabase();
    storeGlobalUser.loadDatabases();
  }, []);

  // Paginated fetch of vertices
  const loadVertices = async (page = 1, append = false) => {
    setVerticesLoading(true);
    const pageSize = 50;
    const url = `${SERVER_URL}/db/vertices?database=${encodeURIComponent(storeGlobalUser.selectedDatabase)}&page=${page}&page_size=${pageSize}`;
    const res = await fetch(url);
    const data = await res.json();
    const list = data.data || data;
    setVerticesTotal(data.total || list.length);
    setVerticesPage(page);
    setVerticesList(prev => append ? [...prev, ...list] : list);
    setVerticesLoading(false);
  };

  // Get vertices list
  useEffect(() => {
    if (!storeGlobalUser.selectedDatabase) return;

    setLoading(true);
    const url = `${SERVER_URL}/db/vertices?database=${encodeURIComponent(storeGlobalUser.selectedDatabase)}`;
    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        // Process paginated data format
        const vertices = data.data || data;
        setKeys(vertices);
        // Default select first vertex
        if (vertices && vertices.length > 0) {
          setKey(vertices[0]);
        }
        setLoading(false);
      })
      .catch((error) => {
        console.error(t('graph.fetch_vertices_failed') + ':', error);
        setLoading(false);
      });
  }, [storeGlobalUser.selectedDatabase, t]);

  // Load first page on init and db switch
  useEffect(() => {
    if (storeGlobalUser.selectedDatabase) {
      setVerticesList([]);
      setVerticesPage(1);
      setVerticesTotal(0);
      loadVertices(1, false);
    }
  }, [storeGlobalUser.selectedDatabase]);

  // Get selected entity details (for right detail panel)
  useEffect(() => {
    if (!key || !storeGlobalUser.selectedDatabase) return;

    const url = `${SERVER_URL}/db/vertices_neighbor/${encodeURIComponent(key)}?database=${encodeURIComponent(storeGlobalUser.selectedDatabase)}`;
    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        const item = data.vertices[key];
        if (item) {
          setItem({
            entity_name: item.entity_name,
            entity_type: item.entity_type,
            descriptions: item.description ? item.description.split('<SEP>') : [''],
            properties: item.additional_properties ? item.additional_properties.split('<SEP>') : ['']
          });
        }
      })
      .catch((error) => {
        console.error(t('graph.fetch_neighbor_data_failed') + ':', error);
      });
  }, [key, storeGlobalUser.selectedDatabase, t]);

  // Handle database switch
  const onDatabaseChange = () => {
    // Clear selection
    setKey(undefined);
    setItem({
      entity_name: '',
      entity_type: '',
      descriptions: [''],
      properties: ['']
    });
  };

  // Render loading state
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '400px',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <Spin size="large" />
        <div>{t('graph.loading_data')}</div>
      </div>
    );
  }

  // Render unselected database state
  if (!storeGlobalUser.selectedDatabase) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '400px',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <DatabaseOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
        <div>{t('graph.select_database_first')}</div>
        <DatabaseSelector
          mode="select"
          showRefresh={true}
          size="middle"
          onChange={onDatabaseChange}
        />
      </div>
    );
  }

  // Render empty data state
  if (!keys || keys.length === 0) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '400px',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <DatabaseOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
        <div>{t('graph.no_entity_data')}</div>
        <div style={{ color: '#999' }}>{t('graph.database_label')}: {storeGlobalUser.selectedDatabase}</div>
        <DatabaseSelector
          mode="select"
          showRefresh={true}
          size="middle"
          onChange={onDatabaseChange}
        />
      </div>
    );
  }

  return (
    <PageWrapper>
      <PageHeader
        title={t('graph.hypergraph_database') || 'Hypergraph Visualization'}
        subtitle={`Exploring: ${storeGlobalUser.selectedDatabase}`}
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{t('graph.select_entity')}:</span>
            <Select
              value={key}
              style={{ width: 240 }}
              showSearch
              loading={verticesLoading}
              placeholder={t('graph.select_entity_placeholder')}
              onChange={setKey}
              size="small"
              onPopupScroll={e => {
                const target = e.target as HTMLElement;
                if (target.scrollTop + target.offsetHeight >= target.scrollHeight - 10) {
                  if (verticesList.length < verticesTotal && !verticesLoading) {
                    loadVertices(verticesPage + 1, true);
                  }
                }
              }}
            >
              {verticesList.map(vertexKey => (
                <Select.Option key={vertexKey} value={vertexKey}>
                  {vertexKey}
                </Select.Option>
              ))}
            </Select>
          </div>
        }
      />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <HyperGraph
            vertexId={key}
            database={storeGlobalUser.selectedDatabase}
            height="100%"
            width="100%"
            showTooltip={true}
            graphId="graph-page-hypergraph"
          />
        </div>
        <Card
          title={t('graph.entity_details')}
          size="small"
          style={{ width: '280px', overflow: 'auto', borderLeft: '1px solid var(--border-subtle)', borderRadius: 0, flexShrink: 0 }}
        >
          <p><strong>{t('graph.entity_name')}:</strong> {item.entity_name}</p>
          <p><strong>{t('graph.entity_type')}:</strong> <Tag color="blue">{item.entity_type}</Tag></p>
          <p><strong>{t('graph.description')}:</strong></p>
          <ul style={{ paddingLeft: '16px', marginTop: '4px' }}>
            {item.descriptions.map((desc, idx) => (
              <li key={idx} style={{ fontSize: '12px', marginBottom: '4px' }}>{desc}</li>
            ))}
          </ul>
          <p><strong>{t('graph.properties')}:</strong></p>
          <ul style={{ paddingLeft: '16px', marginTop: '4px' }}>
            {item.properties.map((prop, idx) => (
              <li key={idx} style={{ fontSize: '12px', marginBottom: '4px' }}>{prop}</li>
            ))}
          </ul>
        </Card>
      </div>
    </PageWrapper>
  );
};

export default observer(GraphPage);