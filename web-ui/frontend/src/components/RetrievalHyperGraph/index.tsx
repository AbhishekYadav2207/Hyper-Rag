import React, { useMemo } from 'react'
import { Graphin } from '@antv/graphin'
import { useTranslation } from 'react-i18next'

const colors = [
  '#F6BD16',
  '#00C9C9',
  '#F08F56',
  '#D580FF',
  '#FF3D00',
  '#16f69c',
  '#004ac9',
  '#f056d1',
  '#a680ff',
  '#c8ff00'
]

// Darken colors
const entityTypeColors = {
  PERSON: '#00C9C9',
  CONCEPT: '#a68fff',
  ORGANIZATION: '#F08F56',
  LOCATION: '#16f69c',
  EVENT: '#004ac9',
  PRODUCT: '#f056d1'
}

const RetrievalHyperGraph = ({
  entities = [],
  hyperedges = [],
  height = '300px',
  width = '100%',
  showTooltip = true,
  containerStyle = {},
  graphId = 'retrieval-hypergraph',
  mode = 'hyper' // mode parameter, default to hyper
}) => {
  const { t } = useTranslation()
  const edgesName = mode === 'hyper' ? t('retrieval.hyperedge_count') : t('retrieval.edge_count')
  // Transform data into HyperGraph format
  const convertedData = useMemo(() => {
    // Return empty if no data
    if (!entities.length && !hyperedges.length) {
      return null
    }

    const vertices = {}
    const edges = {}

    // Process entity data
    entities.forEach(entity => {
      const entityName = String(entity.entity_name || entity.name || `Entity_${Math.random()}`)
      vertices[entityName] = {
        ...entity,
        entity_type: String(entity.entity_type || t('retrieval.unknown')),
        description: String(entity.description || ''),
        label: String(entity.entity_name || entity.name || '')
      }
    })

    // Process hyperedge data
    hyperedges.forEach((edge, index) => {
      // Construct hyperedge key, delimit entities with |#|
      let edgeKey
      if (Array.isArray(edge.entity_set)) {
        edgeKey = edge.entity_set.map(e => String(e)).join('|#|')
      } else if (typeof edge.entity_set === 'string') {
        edgeKey = edge.entity_set
      } else if (edge.id_set) {
        // If no entity_set but id_set exists, use id_set
        edgeKey = Array.isArray(edge.id_set)
          ? edge.id_set.map(e => String(e)).join('|#|')
          : String(edge.id_set)
      } else {
        edgeKey = `edge_${index}`
      }

      // Ensure hyperedge entities are in vertices
      const entityNames = edgeKey.split('|#|')
      entityNames.forEach(entityName => {
        if (!vertices[entityName]) {
          vertices[entityName] = {
            entity_type: t('retrieval.unknown'),
            description: `${t('retrieval.entity_from_hyperedge')}: ${entityName}`
          }
        }
      })

      edges[edgeKey] = {
        keywords: String(edge.keywords || edge.description || ''),
        description: String(edge.description || ''),
        weight: edge.weight || 1,
        ...edge
      }
    })

    return { vertices, edges }
  }, [entities, hyperedges, t])

  const options = useMemo(() => {
    const hyperData = {
      nodes: [],
      edges: []
    }
    const plugins = []

    if (convertedData) {
      // Add vertices
      for (const key in convertedData.vertices) {
        hyperData.nodes.push({
          ...convertedData.vertices[key],
          id: key,
          label: String(key) // Ensure label is string
        })
      }

      if (mode === 'graph') {
        // graph mode: set standard edge format without plugins
        const edgeKeys = Object.keys(convertedData.edges)
        for (let i = 0; i < edgeKeys.length; i++) {
          const key = edgeKeys[i]
          const nodes = key.split('|#|')

          // Create edges for each node pair
          for (let j = 0; j < nodes.length; j++) {
            for (let k = j + 1; k < nodes.length; k++) {
              hyperData.edges.push({
                source: nodes[j],
                target: nodes[k],
                ...convertedData.edges[key]
              })
            }
          }
        }
      } else {
        // hyper mode: use bubble-sets plugin
        // Create style function
        const createStyle = baseColor => ({
          fill: baseColor,
          stroke: baseColor,
          labelFill: '#fff',
          labelPadding: 2,
          labelBackgroundFill: baseColor,
          labelBackgroundRadius: 5,
          labelPlacement: 'center',
          labelAutoRotate: false,
          // BubbleSets configuration
          maxRoutingIterations: 100,
          maxMarchingIterations: 20,
          pixelGroup: 4,
          edgeR0: 10,
          edgeR1: 60,
          nodeR0: 15,
          nodeR1: 50,
          morphBuffer: 10,
          threshold: 4,
          memberInfluenceFactor: 1,
          edgeInfluenceFactor: 4,
          nonMemberInfluenceFactor: -0.8,
          virtualEdges: true
        })

        // Add hyperedges
        const edgeKeys = Object.keys(convertedData.edges)
        for (let i = 0; i < edgeKeys.length; i++) {
          const key = edgeKeys[i]
          const edge = convertedData.edges[key]
          const nodes = key.split('|#|')

          plugins.push({
            key: `bubble-sets-${key}`,
            type: 'bubble-sets',
            members: nodes,
            // labelText: String(edge.keywords || ''), // Ensure labelText is string
            ...createStyle(colors[i % colors.length])
          })
        }
      }

      // Add tooltip plugin
      if (showTooltip) {
        plugins.push({
          type: 'tooltip',
          getContent: (e, items) => {
            let result = ''
            items.forEach(item => {
              result += `<h4>${String(item.id)}</h4>`
              if (item.entity_type) {
                result += `<p><strong>${t('retrieval.entity_type')}:</strong> ${String(
                  item.entity_type
                )}</p>`
              }
              if (item.description) {
                const desc = String(item.description)
                result += `<p><strong>${t('retrieval.description')}:</strong> ${desc
                  .split('<SEP>')
                  .slice(0, 2)
                  .join('; ')}</p>`
              }
            })
            return result
          }
        })
      }
    }

    return {
      autoResize: true,
      data: hyperData,
      node: {
        palette: { field: 'cluster' },
        style: {
          size: mode === 'graph' ? 20 : 25,
          labelText: d => d.id,
          fill: d => {
            // Set colors by entity_type
            if (d.entity_type) {
              return entityTypeColors[d.entity_type] || '#8566CC'
            }
            // Default color
            return '#8566CC'
          }
        }
      },
      edge: {
        style: {
          stroke: '#a68fff', // Edge color
          lineWidth: 3
        }
      },
      animate: false,
      behaviors: ['zoom-canvas', 'drag-canvas', 'drag-element'],
      autoFit: { type: 'view' as const },
      layout: {
        type: 'force-atlas2',
        // clustering: true,
        preventOverlap: true,
        // nodeClusterBy: 'entity_type',
        kr: mode === 'graph' ? 5 : 80,
        gravity: 20,
        linkDistance: 10
      },
      plugins: mode === 'graph' ? (showTooltip ? plugins : []) : plugins
    }
  }, [convertedData, showTooltip, mode, t])

  // If no data, do not display
  if (!convertedData || (!entities.length && !hyperedges.length)) {
    return null
  }

  return (
    <div style={{ height, width, ...containerStyle }}>
      <div
        style={{
          marginBottom: '8px',
          fontSize: '14px',
          color: '#666',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <span>
          {t('retrieval.title')} - {mode}
        </span>
        <span style={{ fontSize: '12px' }}>
          {edgesName}: {hyperedges.length}
        </span>
      </div>
      <Graphin
        options={options}
        id={graphId}
        style={{
          width: '100%',
          height: 'calc(100% - 30px)',
          border: '1px solid #e0e0e0',
          borderRadius: '6px'
        }}
      />
    </div>
  )
}

export default RetrievalHyperGraph
