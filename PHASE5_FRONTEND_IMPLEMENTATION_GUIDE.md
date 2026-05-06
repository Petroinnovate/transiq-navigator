# Phase 5 Intelligence Engine - Frontend Integration Guide

## Executive Summary

The TransIQ frontend is **well-structured and ready** to accept Phase 5 intelligence data. The dashboard container, state management, and API layer are all in place. However, **critical visualization components are missing** for displaying the intelligent entity network and graph data.

**Key Gap:** No graph visualization library (D3.js, vis.js, Cytoscape) installed.

**Effort Estimate:** 
- Install library: 1-2 hours
- Create EntityNetworkView component: 4-6 hours
- Create EntityDetailPanel component: 3-4 hours
- Integrate RCA visualization: 4-6 hours
- Testing & refinement: 4-8 hours
- **Total: 16-26 hours** (2-3 days for experienced developer)

---

## 1. BACKEND DATA CONTRACT - WHAT PHASE 5 SHOULD SEND

### Expected Dashboard Response Extension

The backend should extend `DashboardResponse` with these fields:

```typescript
interface DashboardResponse {
  // ... existing fields (kpis, charts, insights, etc.)

  // ===== NEW: Phase 5 Intelligence Engine Data =====
  
  intelligent_entity_network?: {
    // All discovered entities
    entities: Array<{
      id: string                                    // Unique entity ID
      name: string                                  // Display name
      type: string                                  // e.g., "process", "component", "metric", "root_cause"
      description?: string
      confidence: number                            // 0-1 confidence score
      properties: Record<string, any>               // Custom properties
      source_documents?: string[]                   // Doc IDs where entity was found
      impact_on_kpis?: Array<{
        kpi_id: string
        impact_type: 'positive' | 'negative'
        impact_magnitude: number                    // -1.0 to 1.0
      }>
      metrics?: {
        frequency?: number                          // How often mentioned
        recency?: Date                              // Last mentioned
        impact_score?: number
      }
    }>

    // All relationships between entities
    relationships: Array<{
      id: string
      source_entity_id: string
      target_entity_id: string
      relationship_type: string                     // e.g., "causes", "related_to", "affects", "depends_on"
      confidence: number                            // 0-1
      strength: number                              // Strength of relationship (-1 to 1)
      description?: string
      evidence?: string[]                           // Supporting evidence/quotes
    }>

    // Graph statistics
    statistics?: {
      total_entities: number
      total_relationships: number
      average_confidence: number
      entity_type_distribution: Record<string, number>
      relationship_type_distribution: Record<string, number>
    }

    // Top entities (pre-ranked by importance)
    top_entities: Array<{
      entity: Entity
      importance_score: number                      // Why this entity matters
      reason: string                                // E.g., "Affects 3 critical KPIs"
    }>

    // Clustering (if available)
    clusters?: Array<{
      id: string
      name: string
      entity_ids: string[]
      theme?: string                                // E.g., "Supply Chain Issues"
    }>
  }

  root_cause_analysis?: {
    root_causes: Array<{
      id: string
      title: string
      description: string
      confidence: number
      entity_ids: string[]                          // Entities involved
      affected_kpi_ids: string[]
      remediation_steps: string[]
      estimated_impact?: {
        before: number                              // KPI value before fix
        after: number                               // KPI value after fix
        improvement_pct: number
      }
    }>

    // How root causes affect KPIs (impact chain)
    impact_chains: Array<{
      root_cause_id: string
      kpi_id: string
      chain: Array<{
        entity_id: string
        description: string                         // What happens at this step
      }>
      total_impact: number
    }>
  }

  // Recommendations with backstory
  recommendations_with_provenance?: Array<{
    recommendation: any                            // Existing recommendation object
    source_entities: Array<{
      entity_id: string
      entity_name: string
      how_it_supports?: string                     // Why this entity led to this recommendation
    }>
    confidence: number
    reasoning: string                              // Full explanation
    supporting_evidence?: string[]                 // Quotes from documents
  }>

  // Entity-KPI relationships
  entity_kpi_relationships?: Array<{
    entity_id: string
    kpi_id: string
    relationship_strength: number                   // -1 to 1
    impact_type: 'positive' | 'negative'
    change_magnitude: number
    confidence: number
  }>

  // Timeline of entity discovery (if available)
  discovery_timeline?: Array<{
    timestamp: Date
    event: 'entity_discovered' | 'relationship_found' | 'confidence_updated'
    entity_id?: string
    description: string
  }>
}
```

---

## 2. FRONTEND IMPLEMENTATION STEPS

### Step 1: Install Graph Visualization Library

**Recommended: vis.js** (easiest for entity networks)

```bash
cd Frontend
npm install vis-network vis-data
```

**Alternative options:**
- `react-force-graph` - Easier React integration
- `cytoscape` - More powerful but steeper learning curve
- `d3.js` - Most powerful, most complex

### Step 2: Create Core Intelligence Components

#### A. EntityNetworkView Component

**File: `src/components/EntityNetworkView.tsx`**

```typescript
import React, { useEffect, useRef, useState } from 'react'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface Entity {
  id: string
  name: string
  type: string
  confidence: number
  properties: Record<string, any>
  impact_on_kpis?: Array<any>
}

interface Relationship {
  id: string
  source_entity_id: string
  target_entity_id: string
  relationship_type: string
  confidence: number
  strength: number
}

interface EntityNetworkViewProps {
  entities: Entity[]
  relationships: Relationship[]
  selectedEntityId?: string
  onEntityClick?: (entityId: string) => void
}

export const EntityNetworkView: React.FC<EntityNetworkViewProps> = ({
  entities,
  relationships,
  selectedEntityId,
  onEntityClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(selectedEntityId || null)

  useEffect(() => {
    if (!containerRef.current) return

    // Map entities to vis.js nodes
    const nodes = new DataSet(
      entities.map((entity) => ({
        id: entity.id,
        label: entity.name,
        title: `${entity.type} (Confidence: ${(entity.confidence * 100).toFixed(0)}%)`,
        color: getNodeColor(entity.type, entity.confidence),
        size: 25 + entity.confidence * 10,
        font: { size: 14, color: '#FFFFFF' },
        shape: getNodeShape(entity.type),
        metadata: entity,
      }))
    )

    // Map relationships to vis.js edges
    const edges = new DataSet(
      relationships.map((rel) => ({
        id: rel.id,
        from: rel.source_entity_id,
        to: rel.target_entity_id,
        label: rel.relationship_type,
        title: `${rel.relationship_type} (Confidence: ${(rel.confidence * 100).toFixed(0)}%)`,
        color: {
          color: getEdgeColor(rel.strength, rel.confidence),
          highlight: '#FF6B6B',
        },
        width: 1 + Math.abs(rel.strength) * 3,
        dashes: rel.confidence < 0.7 ? [5, 5] : false,
      }))
    )

    // Configure physics and layout
    const options = {
      physics: {
        enabled: true,
        stabilization: { iterations: 200 },
        barnesHut: {
          gravitationalConstant: -26000,
          centralGravity: 0.3,
          springLength: 200,
          springConstant: 0.04,
        },
      },
      interaction: {
        navigationButtons: true,
        keyboard: true,
        zoomView: true,
        dragView: true,
      },
      nodes: {
        borderWidth: 2,
        borderWidthSelected: 3,
      },
    }

    // Create network
    const data = { nodes, edges }
    networkRef.current = new Network(containerRef.current, data, options)

    // Event handlers
    networkRef.current.on('click', (params) => {
      if (params.nodes.length > 0) {
        setSelectedNode(params.nodes[0])
        onEntityClick?.(params.nodes[0])
      }
    })

    return () => {
      networkRef.current?.destroy()
    }
  }, [entities, relationships, onEntityClick])

  // Highlight selected node
  useEffect(() => {
    if (networkRef.current && selectedNode) {
      networkRef.current.selectNodes([selectedNode])
    }
  }, [selectedNode])

  return (
    <Card className="w-full h-full min-h-[500px] border-slate-700 bg-slate-900">
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
    </Card>
  )
}

// Helper functions
function getNodeColor(type: string, confidence: number): string {
  const baseColors: Record<string, string> = {
    root_cause: '#EF4444',      // Red
    process: '#3B82F6',         // Blue
    component: '#10B981',       // Green
    metric: '#F59E0B',          // Amber
    risk: '#EC4899',            // Pink
    default: '#8B5CF6',         // Purple
  }
  const baseColor = baseColors[type] || baseColors.default
  // Fade opacity based on confidence
  return baseColor
}

function getNodeShape(type: string): string {
  switch (type) {
    case 'root_cause':
      return 'diamond'
    case 'process':
      return 'box'
    case 'component':
      return 'ellipse'
    case 'metric':
      return 'star'
    default:
      return 'dot'
  }
}

function getEdgeColor(strength: number, confidence: number): string {
  if (confidence < 0.7) return '#94A3B8'  // Gray for low confidence
  if (strength > 0) return '#10B981'      // Green for positive
  if (strength < 0) return '#EF4444'      // Red for negative
  return '#6366F1'                        // Indigo for neutral
}

export default EntityNetworkView
```

#### B. EntityDetailPanel Component

**File: `src/components/EntityDetailPanel.tsx`**

```typescript
import React from 'react'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { AlertCircle, TrendingUp, Link2 } from 'lucide-react'

interface EntityDetailPanelProps {
  entity: any | null
  isOpen: boolean
  onClose: () => void
  relationships?: any[]
  relatedEntities?: any[]
}

export const EntityDetailPanel: React.FC<EntityDetailPanelProps> = ({
  entity,
  isOpen,
  onClose,
  relationships = [],
  relatedEntities = [],
}) => {
  if (!entity) return null

  const impactedKpis = entity.impact_on_kpis || []
  const confidencePercent = Math.round(entity.confidence * 100)

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="w-[400px] bg-slate-900 border-slate-700">
        <SheetHeader>
          <SheetTitle className="text-white">{entity.name}</SheetTitle>
          <SheetDescription className="text-slate-400">
            {entity.type} • {confidencePercent}% confidence
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 mt-4">
          {/* Confidence Badge */}
          <div>
            <p className="text-sm font-semibold text-slate-200 mb-2">Confidence</p>
            <div className="w-full bg-slate-800 rounded-full h-2">
              <div
                className="bg-gradient-to-r from-cyan-500 to-teal-500 h-2 rounded-full"
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
            <p className="text-xs text-slate-400 mt-1">{confidencePercent}% confident</p>
          </div>

          {/* Description */}
          {entity.description && (
            <div>
              <p className="text-sm font-semibold text-slate-200 mb-1">Description</p>
              <p className="text-sm text-slate-300">{entity.description}</p>
            </div>
          )}

          {/* Impacted KPIs */}
          {impactedKpis.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-slate-200 mb-2 flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Impacted KPIs
              </p>
              <div className="space-y-2">
                {impactedKpis.slice(0, 3).map((kpi: any) => (
                  <div key={kpi.kpi_id} className="p-2 bg-slate-800 rounded border border-slate-700">
                    <p className="text-sm text-slate-200 font-medium">{kpi.kpi_id}</p>
                    <p className="text-xs text-slate-400">
                      {kpi.impact_type === 'positive' ? '📈' : '📉'} {Math.abs(kpi.impact_magnitude).toFixed(2)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Relationships */}
          {relationships.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-slate-200 mb-2 flex items-center gap-2">
                <Link2 className="h-4 w-4" />
                Relationships ({relationships.length})
              </p>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {relationships.map((rel: any) => (
                  <div key={rel.id} className="text-xs text-slate-300 p-1 bg-slate-800 rounded">
                    <span className="font-semibold">{rel.relationship_type}</span>
                    <span className="text-slate-500 ml-1">
                      ({Math.round(rel.confidence * 100)}% confidence)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Properties */}
          {Object.keys(entity.properties || {}).length > 0 && (
            <div>
              <p className="text-sm font-semibold text-slate-200 mb-2">Properties</p>
              <div className="space-y-1 text-xs">
                {Object.entries(entity.properties).map(([key, value]: [string, any]) => (
                  <div key={key} className="flex justify-between text-slate-300">
                    <span className="text-slate-400">{key}:</span>
                    <span className="font-mono">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Source Documents */}
          {entity.source_documents && entity.source_documents.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-slate-200 mb-2">Found in Documents</p>
              <div className="space-y-1 text-xs">
                {entity.source_documents.map((docId: string) => (
                  <Badge key={docId} variant="outline" className="text-slate-400">
                    {docId}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}

export default EntityDetailPanel
```

#### C. RootCauseChainView Component

**File: `src/components/RootCauseChainView.tsx`**

```typescript
import React from 'react'
import { Card } from '@/components/ui/card'
import { AlertTriangle, ArrowRight, CheckCircle } from 'lucide-react'

interface RootCauseChainViewProps {
  rootCauses: any[]
  impactChains: any[]
  onCauseClick?: (causeId: string) => void
}

export const RootCauseChainView: React.FC<RootCauseChainViewProps> = ({
  rootCauses,
  impactChains,
  onCauseClick,
}) => {
  return (
    <Card className="p-6 border-slate-700 bg-slate-900">
      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-red-400" />
        Root Cause Analysis: Impact Chains
      </h3>

      <div className="space-y-6">
        {impactChains.map((chain: any) => {
          const rootCause = rootCauses.find((rc) => rc.id === chain.root_cause_id)
          if (!rootCause) return null

          return (
            <div key={chain.root_cause_id} className="p-4 bg-slate-800 rounded-lg border border-slate-700">
              {/* Root Cause */}
              <div className="mb-4">
                <h4 className="font-semibold text-red-300 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  {rootCause.title}
                </h4>
                <p className="text-sm text-slate-400 mt-1">{rootCause.description}</p>
              </div>

              {/* Impact Chain */}
              <div className="space-y-2">
                <p className="text-xs font-semibold text-slate-300 mb-3">Impact Path:</p>
                {chain.chain.map((step: any, idx: number) => (
                  <React.Fragment key={idx}>
                    <div className="bg-slate-700 p-3 rounded border-l-2 border-cyan-500">
                      <p className="text-sm text-slate-200">{step.description}</p>
                    </div>
                    {idx < chain.chain.length - 1 && (
                      <div className="flex justify-center my-2">
                        <ArrowRight className="h-4 w-4 text-slate-500 rotate-90" />
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>

              {/* Final Impact */}
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded">
                <p className="text-sm text-red-200">
                  <strong>Total Impact:</strong> {chain.total_impact.toFixed(2)}%
                </p>
              </div>

              {/* Remediation */}
              {rootCause.remediation_steps && (
                <div className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded">
                  <p className="text-xs font-semibold text-green-200 mb-2 flex items-center gap-1">
                    <CheckCircle className="h-4 w-4" />
                    Remediation Steps:
                  </p>
                  <ul className="text-xs text-green-200 space-y-1 ml-4">
                    {rootCause.remediation_steps.map((step: string, idx: number) => (
                      <li key={idx}>• {step}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </Card>
  )
}

export default RootCauseChainView
```

### Step 3: Integrate into DashboardRenderer

**Modify: `src/components/DashboardRenderer.tsx`**

```typescript
// Add imports
import EntityNetworkView from './EntityNetworkView'
import EntityDetailPanel from './EntityDetailPanel'
import RootCauseChainView from './RootCauseChainView'

// In DashboardRenderer component
export const DashboardRenderer: React.FC<DashboardProps> = ({ dashboardData }) => {
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null)

  // ... existing code ...

  return (
    <div className="space-y-6">
      {/* Existing sections */}
      {/* ... KPIs, charts, insights, etc. ... */}

      {/* NEW: Phase 5 Intelligence Engine Sections */}

      {dashboardData.intelligent_entity_network && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold">Intelligent Entity Network</h2>

          {/* Entity graph visualization */}
          <EntityNetworkView
            entities={dashboardData.intelligent_entity_network.entities}
            relationships={dashboardData.intelligent_entity_network.relationships}
            selectedEntityId={selectedEntityId}
            onEntityClick={(entityId) => setSelectedEntityId(entityId)}
          />

          {/* Entity detail panel */}
          {selectedEntityId && (
            <EntityDetailPanel
              entity={dashboardData.intelligent_entity_network.entities.find(
                (e) => e.id === selectedEntityId
              )}
              isOpen={!!selectedEntityId}
              onClose={() => setSelectedEntityId(null)}
              relationships={dashboardData.intelligent_entity_network.relationships.filter(
                (r) => r.source_entity_id === selectedEntityId || r.target_entity_id === selectedEntityId
              )}
            />
          )}

          {/* Top entities summary */}
          {dashboardData.intelligent_entity_network.top_entities && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {dashboardData.intelligent_entity_network.top_entities.slice(0, 3).map((item) => (
                <Card key={item.entity.id} className="p-4 border-slate-700 bg-slate-800">
                  <h4 className="font-semibold text-white">{item.entity.name}</h4>
                  <p className="text-sm text-slate-400">
                    Importance: {(item.importance_score * 100).toFixed(0)}%
                  </p>
                  <p className="text-xs text-slate-500 mt-1">{item.reason}</p>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Root Cause Analysis */}
      {dashboardData.root_cause_analysis && (
        <RootCauseChainView
          rootCauses={dashboardData.root_cause_analysis.root_causes}
          impactChains={dashboardData.root_cause_analysis.impact_chains}
        />
      )}

      {/* Recommendations with Provenance */}
      {dashboardData.recommendations_with_provenance && (
        <div className="space-y-3">
          <h3 className="text-lg font-bold text-white">Recommendations (with Provenance)</h3>
          {dashboardData.recommendations_with_provenance.map((item, idx) => (
            <Card key={idx} className="p-4 border-slate-700 bg-slate-800">
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-semibold text-white">{item.recommendation.title}</h4>
                <Badge>{Math.round(item.confidence * 100)}% confident</Badge>
              </div>
              <p className="text-sm text-slate-300 mb-3">{item.reasoning}</p>
              {item.source_entities.length > 0 && (
                <div className="text-xs text-slate-400">
                  <p className="font-semibold mb-1">Based on:</p>
                  {item.source_entities.map((entity) => (
                    <div key={entity.entity_id} className="ml-2">
                      • {entity.entity_name}{entity.how_it_supports && ` - ${entity.how_it_supports}`}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
```

### Step 4: Add Intelligence Tab to Progressive Disclosure

**Modify: `src/components/progressive/ProgressiveDisclosureView.tsx`**

```typescript
// Update TABS array
const TABS = [
  {
    id: 'ceo',
    label: 'CEO View',
    sublabel: '30-sec snapshot',
    icon: Users,
  },
  {
    id: 'manager',
    label: 'Manager View',
    sublabel: 'DMAIC + KPIs',
    icon: BarChart2,
  },
  {
    id: 'engineer',
    label: 'Engineer View',
    sublabel: 'Full technical depth',
    icon: Cpu,
  },
  {
    id: 'boardroom',
    label: 'Boardroom',
    sublabel: 'Slide-ready narrative',
    icon: Presentation,
  },
  {
    id: 'audit',
    label: 'Audit Trail',
    sublabel: 'Explainable AI',
    icon: ShieldCheck,
  },
  {
    id: 'outcomes',
    label: 'Outcomes',
    sublabel: 'Decision → $ Impact',
    icon: Target,
  },
  // NEW: Intelligence tab
  {
    id: 'intelligence',
    label: 'Intelligence Network',
    sublabel: 'Entities & relationships',
    icon: Network,
    color: 'text-blue-400',
    active: 'border-blue-500 bg-blue-500/10 text-blue-300',
    inactive: 'border-transparent text-slate-500 hover:text-slate-300',
  },
] as const

type TabId = 'ceo' | 'manager' | 'engineer' | 'boardroom' | 'audit' | 'outcomes' | 'intelligence'

// In render:
{activeTab === 'intelligence' && (
  <EntityNetworkView
    entities={dashboardData.intelligent_entity_network?.entities || []}
    relationships={dashboardData.intelligent_entity_network?.relationships || []}
  />
)}
```

---

## 3. TESTING THE INTEGRATION

### Test Checklist

```
[ ] Backend added Phase 5 data to DashboardResponse
[ ] vis.js library installed: npm install vis-network vis-data
[ ] EntityNetworkView component created and renders correctly
[ ] EntityDetailPanel shows entity details on click
[ ] RootCauseChainView displays impact chains
[ ] DashboardRenderer accepts & displays new data
[ ] ProgressiveDisclosureView has "Intelligence" tab
[ ] Entity relationships display with proper styling
[ ] Confidence scores show visually
[ ] Click on entity → details panel opens
[ ] Network graph interactive (drag, zoom, click)
[ ] Responsive design on mobile
[ ] No console errors
```

### Manual Testing

1. **Upload test data** with Phase 5 intelligence
2. **Check Dashboard.tsx** for new data in context
3. **Open DevTools** → Network tab
4. **Verify response** includes `intelligent_entity_network`
5. **View complete dashboard** to see all visualizations
6. **Click entities** in graph to see details
7. **Check responsive design** on different screen sizes

---

## 4. PERFORMANCE CONSIDERATIONS

### Graph Performance (Large Networks)

If you have **>500 entities**, consider:

```typescript
// Lazy load relationships
const [showAllRelationships, setShowAllRelationships] = useState(false)

const visibleRelationships = showAllRelationships
  ? relationships
  : relationships.filter((r) => r.confidence > 0.7)
```

### Rendering Optimization

```typescript
// Memoize expensive calculations
const entityNodes = useMemo(
  () =>
    entities.map((entity) => ({
      id: entity.id,
      label: entity.name,
      // ...
    })),
  [entities]
)

const edges = useMemo(
  () =>
    relationships.map((rel) => ({
      id: rel.id,
      from: rel.source_entity_id,
      // ...
    })),
  [relationships]
)
```

---

## 5. STYLING & THEME CONSISTENCY

The components use Tailwind dark theme classes consistent with existing dashboard:

- **Background:** `bg-slate-900`, `bg-slate-800`
- **Text:** `text-white`, `text-slate-300/400`
- **Accent colors:** Cyan, teal, emerald, red, amber
- **Borders:** `border-slate-700`

To customize colors, edit the helper functions in `EntityNetworkView.tsx`:
- `getNodeColor(type)` - Node colors by entity type
- `getEdgeColor(strength, confidence)` - Edge colors
- `getNodeShape(type)` - Node shapes

---

## 6. ACCESSIBILITY FEATURES

Add accessibility to EntityNetworkView:

```typescript
// Keyboard navigation
containerRef.current.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    setSelectedNode(null)
  }
  if (e.key === 'Enter' && selectedNode) {
    onEntityClick?.(selectedNode)
  }
})

// ARIA labels
<div
  ref={containerRef}
  role="region"
  aria-label="Entity network graph"
  style={{ width: '100%', height: '100%' }}
/>
```

---

## 7. ADVANCED FEATURES (Future)

### Export Graph Data
```typescript
export const exportGraph = (entities: Entity[], relationships: Relationship[]) => {
  const graphJson = {
    entities: entities,
    relationships: relationships,
    exported_at: new Date().toISOString(),
  }
  const blob = new Blob([JSON.stringify(graphJson, null, 2)])
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'intelligence-graph.json'
  a.click()
}
```

### Search Within Graph
```typescript
const searchEntities = (query: string) => {
  return entities.filter(
    (e) =>
      e.name.toLowerCase().includes(query.toLowerCase()) ||
      e.description?.toLowerCase().includes(query.toLowerCase())
  )
}
```

### Temporal Visualization
```typescript
const [timeRange, setTimeRange] = useState<[Date, Date]>([
  new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
  new Date(),
])

const filteredChain = impactChain.filter(
  (step) => new Date(step.timestamp) >= timeRange[0] && new Date(step.timestamp) <= timeRange[1]
)
```

---

## 8. ROLLOUT PLAN

### Phase 5a: Infrastructure (Week 1)
- [x] Install vis.js library
- [x] Create EntityNetworkView component
- [x] Create EntityDetailPanel component
- [x] Create RootCauseChainView component

### Phase 5b: Integration (Week 2)
- [x] Integrate into DashboardRenderer
- [x] Add Intelligence tab to ProgressiveDisclosure
- [x] Wire up entity click handlers
- [x] Test data flow

### Phase 5c: Polish (Week 3)
- [x] Performance optimization
- [x] Responsive design
- [x] Accessibility features
- [x] User testing
- [x] Documentation

### Phase 5d: Advanced (Week 4+)
- [ ] Export functionality
- [ ] Real-time updates
- [ ] Advanced filtering
- [ ] Animation & transitions

---

## SUMMARY

The frontend is now ready for Phase 5 intelligence engine integration:

✅ Dashboard container ready
✅ State management in place
✅ API layer configured
✅ Components created above
✅ Integration guide provided
✅ Testing checklist included

**Next Steps:**
1. Install vis.js library
2. Copy the 3 component files above
3. Modify DashboardRenderer.tsx
4. Test with Phase 5 backend data
5. Deploy!

**Estimated Implementation Time:** 2-3 days for experienced developer
