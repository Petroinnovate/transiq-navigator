/**
 * Extended dashboard types for Phase 5 Intelligence Engine
 * Add these to your existing types/dashboard.ts file
 */

/**
 * Weighted entity node in the intelligence network
 */
export interface WeightedEntity {
  id: string
  name: string
  type: string
  
  // Domain-specific weights (0.0-1.0)
  financial_weight: number
  esg_weight: number
  drilling_weight: number
  
  // Graph importance metrics
  pagerank: number
  betweenness: number
  
  // Domain-specific metrics
  financial_metrics: Record<string, any>
  esg_metrics: Record<string, any>
  drilling_metrics: Record<string, any>
}

/**
 * Weighted relationship edge in the intelligence network
 */
export interface WeightedRelationship {
  source_id: string
  target_id: string
  relationship_type: string
  confidence: number
  
  // Domain-specific impact scores
  financial_impact: number
  esg_risk_score: number
  drilling_sensitivity: number
  
  // Combined importance score
  combined_weight: number
}

/**
 * Intelligence network visualization data
 */
export interface IntelligenceNetworkVisualization {
  nodes: WeightedEntity[]
  edges: WeightedRelationship[]
  
  // Domain-specific summaries
  financial_summary: Record<string, any>
  esg_summary: Record<string, any>
  drilling_summary: Record<string, any>
  
  // Insights and recommendations
  key_insights: string[]
  recommendations: string[]
  
  // Metadata
  timestamp: string
}

/**
 * Cross-engine analysis combining all intelligence domains
 */
export interface CrossEngineAnalysis {
  primary_entity_id: string
  
  // Financial analysis
  financial_impact: number
  financial_drivers: string[]
  financial_recommendations: string[]
  
  // ESG analysis
  esg_overall_score: number
  environmental_score: number
  social_score: number
  governance_score: number
  esg_recommendations: string[]
  
  // Drilling analysis (if applicable)
  npt_metrics: Record<string, any>
  rop_metrics: Record<string, any>
  mtbf_mttr: Record<string, any>
  drilling_recommendations: string[]
  
  // Synthesis
  highest_priority: string
  estimated_value_at_stake: number
  confidence_level: 'low' | 'medium' | 'high'
}

/**
 * Unified recommendations across all engines
 */
export interface RecommendationPackage {
  primary_entity_id: string
  recommendations: Array<{
    engine: 'Financial' | 'ESG' | 'Drilling'
    priority: number
    action: string
    impact_estimate: string
    timeline: string
  }>
  portfolio_summary: Record<string, any>
  next_steps: string[]
}
