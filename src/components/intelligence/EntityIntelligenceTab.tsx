/**
 * EntityIntelligenceTab.tsx
 * Phase 5: Intelligence Engine Integration
 * 
 * Displays entity network visualization with weighted relationships
 * Integrates Financial, ESG, and Drilling intelligence analysis
 * 
 * @component
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from '@/lib/axios'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { 
  Network, 
  AlertTriangle, 
  TrendingUp, 
  Activity,
  DollarSign,
  Leaf,
  Zap,
  Info,
  ChevronDown,
  Filter,
  Download
} from 'lucide-react'
import { 
  IntelligenceNetworkVisualization, 
  WeightedEntity, 
  WeightedRelationship,
  CrossEngineAnalysis 
} from '@/types/dashboard'

interface EntityIntelligenceTabProps {
  reportId: string
  primaryEntityId?: string
}

interface EntityFilter {
  byDomain: 'all' | 'financial' | 'esg' | 'drilling'
  minConfidence: number
  entityType?: string
}

/**
 * Fetches entity network visualization data from Phase 5 backend
 */
const fetchEntityNetwork = async (entityId: string): Promise<IntelligenceNetworkVisualization> => {
  const response = await axios.get<IntelligenceNetworkVisualization>(
    `/api/v2/intelligence/graph-network/${entityId}`
  )
  return response.data
}

/**
 * Fetches cross-engine analysis for an entity
 */
const fetchCrossEngineAnalysis = async (entityId: string): Promise<CrossEngineAnalysis> => {
  const response = await axios.get<CrossEngineAnalysis>(
    `/api/v2/intelligence/cross-engine-analysis/${entityId}`
  )
  return response.data
}

/**
 * EntityNetworkVisualization Component
 * Renders interactive entity graph with vis-network
 */
const EntityNetworkVisualization: React.FC<{
  nodes: WeightedEntity[]
  edges: WeightedRelationship[]
  onEntitySelect: (entity: WeightedEntity) => void
  filter: EntityFilter
}> = ({ nodes, edges, onEntitySelect, filter }) => {
  const containerRef = React.useRef<HTMLDivElement>(null)
  const networkRef = React.useRef<any>(null)

  useEffect(() => {
    // Dynamic import of vis-network to avoid SSR issues
    const initializeNetwork = async () => {
      try {
        const { Network } = await import('vis-network')

        if (!containerRef.current) return

        // Filter nodes based on selected domain and confidence
        const filteredNodes = nodes.filter(node => {
          if (filter.byDomain === 'financial') return node.financial_weight > filter.minConfidence
          if (filter.byDomain === 'esg') return node.esg_weight > filter.minConfidence
          if (filter.byDomain === 'drilling') return node.drilling_weight > filter.minConfidence
          return true
        })

        // Convert to vis-network format
        const visNodes = filteredNodes.map(node => ({
          id: node.id,
          label: node.name,
          title: `${node.type}\nConfidence: ${(node.pagerank * 100).toFixed(1)}%`,
          size: Math.max(15, Math.min(50, node.pagerank * 100)),
          color: getNodeColor(node, filter),
          physics: true,
          borderWidth: 2,
        }))

        // Filter edges based on domain
        const filteredEdges = filter.byDomain === 'all' 
          ? edges 
          : edges.filter(edge => {
              if (filter.byDomain === 'financial') return edge.financial_impact > 0
              if (filter.byDomain === 'esg') return edge.esg_risk_score > 0
              if (filter.byDomain === 'drilling') return edge.drilling_sensitivity > 0
              return true
            })

        const visEdges = filteredEdges.map(edge => ({
          from: edge.source_id,
          to: edge.target_id,
          label: `${(edge.combined_weight * 100).toFixed(0)}%`,
          value: edge.combined_weight * 5, // Scale for visibility
          title: `${edge.relationship_type}\nConfidence: ${(edge.confidence * 100).toFixed(1)}%`,
          color: getEdgeColor(edge, filter),
          smooth: { type: 'cubicBezier' },
        }))

        const data = { nodes: visNodes, edges: visEdges }
        const options = {
          physics: {
            enabled: true,
            barnesHut: { gravitationalConstant: -30000, centralGravity: 0.3 },
            maxVelocity: 50,
            solver: 'barnesHut',
            timestep: 0.35,
          },
          interaction: {
            hover: true,
            navigationButtons: true,
            keyboard: true,
            zoomView: true,
            dragView: true,
          },
          edges: {
            smooth: { enabled: true, type: 'continuous' },
            arrows: 'to',
            font: { size: 10, align: 'middle' },
          },
          nodes: {
            font: { size: 14, face: 'Tahoma' },
            borderWidthSelected: 3,
          },
        }

        if (networkRef.current) {
          networkRef.current.destroy()
        }

        const network = new Network(containerRef.current, data, options)
        networkRef.current = network

        // Handle node clicks
        network.on('click', (params: any) => {
          if (params.nodes.length > 0) {
            const selectedNode = nodes.find(n => n.id === params.nodes[0])
            if (selectedNode) {
              onEntitySelect(selectedNode)
            }
          }
        })

      } catch (error) {
        console.error('Failed to initialize vis-network:', error)
      }
    }

    initializeNetwork()

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy()
        networkRef.current = null
      }
    }
  }, [nodes, edges, filter, onEntitySelect])

  return (
    <div 
      ref={containerRef} 
      className="w-full bg-gradient-to-br from-slate-50 to-slate-100 rounded-lg border border-slate-200"
      style={{ height: '500px' }}
    />
  )
}

/**
 * EntityDetailPanel Component
 * Shows detailed analysis for selected entity
 */
const EntityDetailPanel: React.FC<{
  entity: WeightedEntity
  analysis?: CrossEngineAnalysis
  isLoading?: boolean
}> = ({ entity, analysis, isLoading }) => {
  if (isLoading) {
    return (
      <Card className="border border-slate-200">
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-l-4 border-l-primary bg-slate-50">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">{entity.name}</CardTitle>
            <p className="text-sm text-slate-600 mt-1">
              {entity.type} • Centrality: {(entity.pagerank * 100).toFixed(1)}%
            </p>
          </div>
          <Badge variant="outline" className="ml-2">
            {(entity.pagerank * 100).toFixed(0)}% Central
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Domain Weights */}
        <div className="grid grid-cols-3 gap-3">
          {/* Financial Weight */}
          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-blue-600" />
              <span className="text-xs font-semibold text-slate-700">Financial</span>
            </div>
            <div className="text-2xl font-bold text-blue-600">
              {(entity.financial_weight * 100).toFixed(0)}%
            </div>
            {entity.financial_metrics?.daily_cost && (
              <p className="text-xs text-slate-600 mt-1">
                ${(entity.financial_metrics.daily_cost / 1000).toFixed(0)}K/day
              </p>
            )}
          </div>

          {/* ESG Weight */}
          <div className="p-3 bg-green-50 rounded-lg border border-green-200">
            <div className="flex items-center gap-2 mb-2">
              <Leaf className="h-4 w-4 text-green-600" />
              <span className="text-xs font-semibold text-slate-700">ESG Risk</span>
            </div>
            <div className="text-2xl font-bold text-green-600">
              {(entity.esg_weight * 100).toFixed(0)}%
            </div>
            {entity.esg_metrics?.score && (
              <p className="text-xs text-slate-600 mt-1">
                Score: {entity.esg_metrics.score.toFixed(1)}/100
              </p>
            )}
          </div>

          {/* Drilling Weight */}
          <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="h-4 w-4 text-amber-600" />
              <span className="text-xs font-semibold text-slate-700">Drilling</span>
            </div>
            <div className="text-2xl font-bold text-amber-600">
              {(entity.drilling_weight * 100).toFixed(0)}%
            </div>
            {entity.drilling_metrics?.npt_hours && (
              <p className="text-xs text-slate-600 mt-1">
                NPT: {entity.drilling_metrics.npt_hours.toFixed(1)}h
              </p>
            )}
          </div>
        </div>

        {/* Cross-Engine Analysis */}
        {analysis && (
          <div className="space-y-3 pt-3 border-t border-slate-200">
            <h4 className="font-semibold text-sm text-slate-700 flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Cross-Engine Analysis
            </h4>

            {analysis.financial_impact > 0 && (
              <div className="text-sm bg-blue-50 p-2 rounded border border-blue-200">
                <span className="font-semibold text-blue-900">Financial:</span>
                <span className="text-blue-800"> ${(analysis.financial_impact / 1000).toFixed(0)}K impact</span>
              </div>
            )}

            {analysis.esg_overall_score > 0 && (
              <div className="text-sm bg-green-50 p-2 rounded border border-green-200">
                <span className="font-semibold text-green-900">ESG Score:</span>
                <span className="text-green-800"> {analysis.esg_overall_score.toFixed(1)}/100</span>
              </div>
            )}

            {analysis.highest_priority && (
              <div className="text-sm bg-amber-50 p-2 rounded border border-amber-200">
                <span className="font-semibold text-amber-900">Priority:</span>
                <span className="text-amber-800"> {analysis.highest_priority}</span>
              </div>
            )}
          </div>
        )}

        {/* Metrics Display */}
        {Object.keys(entity.drilling_metrics || {}).length > 0 && (
          <div className="space-y-2 pt-3 border-t border-slate-200">
            <h4 className="font-semibold text-sm text-slate-700">Drilling Metrics</h4>
            {Object.entries(entity.drilling_metrics || {}).map(([key, value]) => (
              <div key={key} className="flex justify-between text-xs text-slate-600">
                <span>{key}:</span>
                <span className="font-semibold text-slate-900">
                  {typeof value === 'number' ? value.toFixed(2) : value}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * Main EntityIntelligenceTab Component
 */
export const EntityIntelligenceTab: React.FC<EntityIntelligenceTabProps> = ({
  reportId,
  primaryEntityId = reportId,
}) => {
  const [selectedEntity, setSelectedEntity] = useState<WeightedEntity | null>(null)
  const [filter, setFilter] = useState<EntityFilter>({
    byDomain: 'all',
    minConfidence: 0.5,
  })

  // Fetch entity network data
  const { 
    data: networkData, 
    isLoading: isNetworkLoading, 
    error: networkError 
  } = useQuery({
    queryKey: ['entityNetwork', primaryEntityId],
    queryFn: () => fetchEntityNetwork(primaryEntityId),
    staleTime: 10 * 60 * 1000, // 10 minutes
  })

  // Fetch cross-engine analysis for selected entity
  const { 
    data: analysisData, 
    isLoading: isAnalysisLoading 
  } = useQuery({
    queryKey: ['entityAnalysis', selectedEntity?.id],
    queryFn: () => selectedEntity ? fetchCrossEngineAnalysis(selectedEntity.id) : null,
    enabled: !!selectedEntity,
    staleTime: 10 * 60 * 1000,
  })

  const handleExportData = useCallback(() => {
    if (!networkData) return

    const exportData = {
      nodes: networkData.nodes,
      edges: networkData.edges,
      summary: {
        financial: networkData.financial_summary,
        esg: networkData.esg_summary,
        drilling: networkData.drilling_summary,
      },
      timestamp: networkData.timestamp,
    }

    const dataStr = JSON.stringify(exportData, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `entity-intelligence-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }, [networkData])

  if (networkError) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Failed to load entity intelligence data: {(networkError as Error).message}
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-4 w-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="h-5 w-5 text-primary" />
          <h3 className="font-semibold text-lg text-slate-900">Entity Intelligence Network</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportData}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
          >
            <Download className="h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="graph" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="graph" className="flex items-center gap-2">
            <Network className="h-4 w-4" />
            Network Graph
          </TabsTrigger>
          <TabsTrigger value="entities" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Entities ({networkData?.nodes.length || 0})
          </TabsTrigger>
          <TabsTrigger value="insights" className="flex items-center gap-2">
            <Info className="h-4 w-4" />
            Insights
          </TabsTrigger>
        </TabsList>

        {/* Graph Tab */}
        <TabsContent value="graph" className="space-y-4 mt-4">
          {isNetworkLoading ? (
            <div className="h-96 bg-slate-100 rounded-lg animate-pulse" />
          ) : networkData ? (
            <>
              {/* Filter Bar */}
              <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
                <Filter className="h-4 w-4 text-slate-600" />
                <select
                  value={filter.byDomain}
                  onChange={(e) =>
                    setFilter(prev => ({ ...prev, byDomain: e.target.value as any }))
                  }
                  className="text-sm px-2 py-1 rounded border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="all">All Domains</option>
                  <option value="financial">Financial Only</option>
                  <option value="esg">ESG Only</option>
                  <option value="drilling">Drilling Only</option>
                </select>
                <select
                  value={filter.minConfidence}
                  onChange={(e) =>
                    setFilter(prev => ({ ...prev, minConfidence: parseFloat(e.target.value) }))
                  }
                  className="text-sm px-2 py-1 rounded border border-slate-300 focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="0">All Confidence</option>
                  <option value="0.5">50%+ Confidence</option>
                  <option value="0.7">70%+ Confidence</option>
                  <option value="0.9">90%+ Confidence</option>
                </select>
              </div>

              {/* Network Graph */}
              <EntityNetworkVisualization
                nodes={networkData.nodes}
                edges={networkData.edges}
                onEntitySelect={setSelectedEntity}
                filter={filter}
              />

              {/* Legend */}
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="p-2 bg-blue-50 rounded border border-blue-200">
                  <p className="font-semibold text-blue-900">Financial Weight</p>
                  <p className="text-blue-700">Cost impact & ROI</p>
                </div>
                <div className="p-2 bg-green-50 rounded border border-green-200">
                  <p className="font-semibold text-green-900">ESG Risk Score</p>
                  <p className="text-green-700">Environmental & Social</p>
                </div>
                <div className="p-2 bg-amber-50 rounded border border-amber-200">
                  <p className="font-semibold text-amber-900">Drilling Sensitivity</p>
                  <p className="text-amber-700">Operations impact</p>
                </div>
              </div>
            </>
          ) : null}
        </TabsContent>

        {/* Entities Tab */}
        <TabsContent value="entities" className="space-y-4 mt-4">
          {isNetworkLoading ? (
            <Skeleton className="h-96 w-full" />
          ) : networkData ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Entity List */}
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {networkData.nodes.map(entity => (
                  <div
                    key={entity.id}
                    onClick={() => setSelectedEntity(entity)}
                    className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                      selectedEntity?.id === entity.id
                        ? 'border-primary bg-primary/5'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="font-semibold text-slate-900">{entity.name}</div>
                    <div className="text-xs text-slate-600 mt-1">{entity.type}</div>
                    <div className="flex gap-1 mt-2">
                      {entity.financial_weight > 0 && (
                        <Badge variant="outline" className="text-xs bg-blue-50">
                          F: {(entity.financial_weight * 100).toFixed(0)}%
                        </Badge>
                      )}
                      {entity.esg_weight > 0 && (
                        <Badge variant="outline" className="text-xs bg-green-50">
                          E: {(entity.esg_weight * 100).toFixed(0)}%
                        </Badge>
                      )}
                      {entity.drilling_weight > 0 && (
                        <Badge variant="outline" className="text-xs bg-amber-50">
                          D: {(entity.drilling_weight * 100).toFixed(0)}%
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Entity Detail Panel */}
              <div>
                {selectedEntity ? (
                  <EntityDetailPanel
                    entity={selectedEntity}
                    analysis={analysisData}
                    isLoading={isAnalysisLoading}
                  />
                ) : (
                  <Card className="border border-slate-200 h-full flex items-center justify-center">
                    <div className="text-center text-slate-600">
                      <p className="text-sm">Select an entity to view details</p>
                    </div>
                  </Card>
                )}
              </div>
            </div>
          ) : null}
        </TabsContent>

        {/* Insights Tab */}
        <TabsContent value="insights" className="space-y-4 mt-4">
          {isNetworkLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : networkData ? (
            <div className="space-y-4">
              {/* Key Insights */}
              {networkData.key_insights.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <TrendingUp className="h-4 w-4" />
                      Key Insights
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {networkData.key_insights.map((insight, idx) => (
                        <li key={idx} className="text-sm text-slate-700 flex gap-2">
                          <span className="text-primary font-bold">•</span>
                          {insight}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Recommendations */}
              {networkData.recommendations.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <ChevronDown className="h-4 w-4" />
                      Recommendations
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {networkData.recommendations.map((rec, idx) => (
                        <li key={idx} className="text-sm text-slate-700 flex gap-2">
                          <span className="text-primary font-bold">→</span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Domain Summaries */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {Object.keys(networkData.financial_summary || {}).length > 0 && (
                  <Card className="border-l-4 border-l-blue-500">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <DollarSign className="h-4 w-4 text-blue-600" />
                        Financial Summary
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-600">
                      {JSON.stringify(networkData.financial_summary).substring(0, 100)}...
                    </CardContent>
                  </Card>
                )}

                {Object.keys(networkData.esg_summary || {}).length > 0 && (
                  <Card className="border-l-4 border-l-green-500">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Leaf className="h-4 w-4 text-green-600" />
                        ESG Summary
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-600">
                      {JSON.stringify(networkData.esg_summary).substring(0, 100)}...
                    </CardContent>
                  </Card>
                )}

                {Object.keys(networkData.drilling_summary || {}).length > 0 && (
                  <Card className="border-l-4 border-l-amber-500">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Zap className="h-4 w-4 text-amber-600" />
                        Drilling Summary
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-600">
                      {JSON.stringify(networkData.drilling_summary).substring(0, 100)}...
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          ) : null}
        </TabsContent>
      </Tabs>
    </div>
  )
}

/**
 * Helper: Get node color based on domain weights
 */
function getNodeColor(entity: WeightedEntity, filter: EntityFilter): string {
  if (filter.byDomain === 'financial' && entity.financial_weight > 0)
    return '#3B82F6'
  if (filter.byDomain === 'esg' && entity.esg_weight > 0)
    return '#10B981'
  if (filter.byDomain === 'drilling' && entity.drilling_weight > 0)
    return '#F59E0B'

  // Mixed weights - gradient approach
  if (entity.financial_weight > 0.6) return '#3B82F6'
  if (entity.esg_weight > 0.6) return '#10B981'
  if (entity.drilling_weight > 0.6) return '#F59E0B'
  return '#6B7280'
}

/**
 * Helper: Get edge color based on domain weights
 */
function getEdgeColor(
  edge: WeightedRelationship,
  filter: EntityFilter
): string {
  if (filter.byDomain === 'financial' && edge.financial_impact > 0) return '#93C5FD'
  if (filter.byDomain === 'esg' && edge.esg_risk_score > 0) return '#A7F3D0'
  if (filter.byDomain === 'drilling' && edge.drilling_sensitivity > 0) return '#FCD34D'

  // Mixed weights - pick strongest
  const max = Math.max(edge.financial_impact, edge.esg_risk_score, edge.drilling_sensitivity)
  if (max === edge.financial_impact) return '#93C5FD'
  if (max === edge.esg_risk_score) return '#A7F3D0'
  if (max === edge.drilling_sensitivity) return '#FCD34D'
  return '#D1D5DB'
}

export default EntityIntelligenceTab
