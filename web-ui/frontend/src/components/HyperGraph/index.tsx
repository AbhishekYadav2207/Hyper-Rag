import React, { useEffect, useMemo, useState } from 'react';
import { Graphin } from '@antv/graphin';
import { Spin, message } from 'antd';
import { SERVER_URL } from '../../utils';

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
    '#c8ff00',
];

const entityTypeColors = {
    'PERSON': '#00C9C9',
    'CONCEPT': '#a68fff',
    'ORGANIZATION': '#F08F56',
    'LOCATION': '#16f69c',
    'EVENT': '#004ac9',
    'PRODUCT': '#f056d1',
}

const HyperGraph = ({
    vertexId,
    database,
    height = '400px',
    width = '100%',
    showTooltip = true,
    containerStyle = {},
    graphId = 'hypergraph-viewer'
}) => {
    const [data, setData] = useState(undefined);
    const [loading, setLoading] = useState(false);

    // Get vertex neighbor data
    const fetchVertexNeighbor = async (vId, db) => {
        if (!vId) {
return;
}

        setLoading(true);
        try {
            const url = db
                ? `${SERVER_URL}/db/vertices_neighbor/${encodeURIComponent(vId)}?database=${encodeURIComponent(db)}`
                : `${SERVER_URL}/db/vertices_neighbor/${encodeURIComponent(vId)}`;

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`API failed: ${response.status}`);
            }
            const neighborData = await response.json();
            setData(neighborData);
        } catch (error) {
            console.error('Failed to fetch vertex neighbor:', error);
            message.error(`Failed to fetch graph data: ${error.message}`);
        }
        setLoading(false);
    };

    useEffect(() => {
        if (vertexId) {
            fetchVertexNeighbor(vertexId, database);
        }
    }, [vertexId, database]);

    const options = useMemo(() => {
        const hyperData = {
            nodes: [],
            edges: [],
        };
        const plugins = [];

        if (data) {
            // Add vertices
            for (const key in data.vertices) {
                hyperData.nodes.push({
                    id: key,
                    label: key,
                    ...data.vertices[key],
                });
            }

            // Create style function
            const createStyle = (baseColor) => ({
                fill: baseColor,
                stroke: baseColor,
                // labelFill: '#fff',
                // labelPadding: 2,
                // labelBackgroundFill: baseColor,
                // labelBackgroundRadius: 5,
                // labelPlacement: 'center',
                // labelAutoRotate: false,
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
                virtualEdges: true,
            });

            // Add hyperedges
            const edgeKeys = Object.keys(data.edges);
            for (let i = 0; i < edgeKeys.length; i++) {
                const key = edgeKeys[i];
                const edge = data.edges[key];
                const nodes = key.split('|#|');

                plugins.push({
                    key: `bubble-sets-${key}`,
                    type: 'bubble-sets',
                    members: nodes,
                    // labelText: edge.keywords || '',
                    ...createStyle(colors[i % colors.length]),
                });
            }

            // Add tooltip plugin
            if (showTooltip) {
                plugins.push({
                    type: 'tooltip',
                    getContent: (e, items) => {
                        let result = '';
                        items.forEach((item) => {
                            result += `<h4>${item.id}</h4>`;
                            if (item.entity_type) {
                                result += `<p><strong>Type:</strong> ${item.entity_type}</p>`;
                            }
                            if (item.description) {
                                result += `<p><strong>Description:</strong> ${item.description.split('<SEP>').slice(0, 2).join('; ')}</p>`;
                            }
                        });
                        return result;
                    },
                });
            }
        }

        return {
            autoResize: true,
            data: hyperData,
            node: {
                palette: { field: 'cluster' },
                style: {
                    size: 25,
                    labelText: d => d.id,
                    fill: d => {
                        // If current vertex being viewed, highlight red
                        if (d.id === vertexId) {
                            return 'black';
                        }
                        // Set different colors according to entity_type
                        if (d.entity_type) {
                            return entityTypeColors[d.entity_type] || '#8566CC' ;
                        }
                        // Default color
                        return '#8566CC';
                    },
                }
            },
            edge: {
                style: {
                    size: 2,
                }
            },
            animate: false,
            behaviors: [
                'zoom-canvas',
                'drag-canvas',
                'drag-element',
            ],
            autoFit: 'center',
            layout: {
                type: 'force',
                clustering: true,
                preventOverlap: true,
                nodeClusterBy: 'entity_type',
                gravity: 20,
                linkDistance: 150,
            },
            plugins,
        };
    }, [data, vertexId, showTooltip]);

    if (loading) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height,
                ...containerStyle
            }}>
                <Spin size="large" tip="Loading hypergraph data..." />
            </div>
        );
    }

    if (!data || !vertexId) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height,
                color: '#999',
                ...containerStyle
            }}>
                {!vertexId ? 'Please select a vertex' : 'No graph data'}
            </div>
        );
    }

    return (
        <div style={{ height, width, ...containerStyle }}>
            <Graphin
                options={options}
                id={graphId}
                style={{ width: '100%', height: '100%' }}
                error={() => {
                    return <div>
                        <div>

                        </div>
                    </div>
                }}
            />
        </div>
    );
};

export default HyperGraph;