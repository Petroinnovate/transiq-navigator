// ============================================================================
// ChartRenderer - Universal Schema-Driven Chart Component
// Purpose: Dynamic visualization with annotations, compare mode, Sankey support
// ============================================================================

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ChartBlock } from '@/types/dashboard'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  RadialBarChart,
  RadialBar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
  ReferenceDot,
  Label,
} from 'recharts'
import { BarChart3, LineChart as LineChartIcon, PieChart as PieChartIcon, Activity, TrendingUp, Target, Zap, GitBranch } from 'lucide-react'

interface ChartRendererProps {
  chart: ChartBlock
}

const CHART_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#14b8a6', // teal
  '#f97316', // orange
]

export const ChartRenderer: React.FC<ChartRendererProps> = ({ chart }) => {
  const getChartTypeIcon = () => {
    switch (chart.type) {
      case 'line':
        return <LineChartIcon className="h-4 w-4" />
      case 'bar':
        return <BarChart3 className="h-4 w-4" />
      case 'pie':
        return <PieChartIcon className="h-4 w-4" />
      case 'area':
        return <TrendingUp className="h-4 w-4" />
      case 'scatter':
        return <Activity className="h-4 w-4" />
      case 'radar':
        return <Target className="h-4 w-4" />
      case 'radialbar':
        return <Target className="h-4 w-4" />
      case 'histogram':
        return <BarChart3 className="h-4 w-4" />
      case 'boxplot':
        return <Activity className="h-4 w-4" />
      case 'funnel':
        return <GitBranch className="h-4 w-4" />
      case 'sankey':
        return <GitBranch className="h-4 w-4" />
      case 'heatmap':
        return <Zap className="h-4 w-4" />
      default:
        return <BarChart3 className="h-4 w-4" />
    }
  }

  const renderAnnotations = () => {
    if (!chart.annotations || chart.annotations.length === 0) return null

    return chart.annotations.map((annotation, index) => {
      switch (annotation.type) {
        case 'threshold':
          return (
            <ReferenceLine
              key={`annotation-${index}`}
              y={annotation.position as number}
              stroke="#ef4444"
              strokeDasharray="3 3"
              label={{
                value: annotation.label,
                position: 'right',
                fill: '#ef4444',
                fontSize: 12,
              }}
            />
          )
        case 'target':
          return (
            <ReferenceLine
              key={`annotation-${index}`}
              y={annotation.position as number}
              stroke="#10b981"
              strokeDasharray="5 5"
              label={{
                value: annotation.label,
                position: 'right',
                fill: '#10b981',
                fontSize: 12,
              }}
            />
          )
        case 'event':
          return (
            <ReferenceLine
              key={`annotation-${index}`}
              x={annotation.position as string}
              stroke="#f59e0b"
              strokeDasharray="3 3"
              label={{
                value: annotation.label,
                position: 'top',
                fill: '#f59e0b',
                fontSize: 12,
              }}
            />
          )
        default:
          return null
      }
    })
  }

  const renderChart = () => {
    const commonProps = {
      data: chart.data,
      margin: { top: 5, right: 30, left: 20, bottom: 5 },
    }

    switch (chart.type) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey={chart.xAxis || 'name'} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
              {renderAnnotations()}
              {Object.keys(chart.data[0] || {})
                .filter(key => key !== chart.xAxis && key !== 'name')
                .map((key, index) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={CHART_COLORS[index % CHART_COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                ))}
            </LineChart>
          </ResponsiveContainer>
        )

      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey={chart.xAxis || 'name'} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
              {renderAnnotations()}
              {Object.keys(chart.data[0] || {})
                .filter(key => key !== chart.xAxis && key !== 'name')
                .map((key, index) => (
                  <Bar
                    key={key}
                    dataKey={key}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                    radius={[4, 4, 0, 0]}
                  />
                ))}
            </BarChart>
          </ResponsiveContainer>
        )

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey={chart.xAxis || 'name'} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
              {renderAnnotations()}
              {Object.keys(chart.data[0] || {})
                .filter(key => key !== chart.xAxis && key !== 'name')
                .map((key, index) => (
                  <Area
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={CHART_COLORS[index % CHART_COLORS.length]}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                    fillOpacity={0.6}
                  />
                ))}
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'pie':
        const dataKey = Object.keys(chart.data[0] || {}).find(key => key !== 'name') || 'value'
        return (
          <ResponsiveContainer width="100%" height={400}>
            <PieChart>
              <Pie
                data={chart.data}
                dataKey={dataKey}
                nameKey={chart.xAxis || 'name'}
                cx="50%"
                cy="50%"
                outerRadius={120}
                label={(entry) => `${entry.name}: ${entry.value}`}
                labelLine={true}
              >
                {chart.data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        )

      case 'scatter':
        const xKey = chart.xAxis || Object.keys(chart.data[0] || {})[0]
        const yKey = chart.yAxis || Object.keys(chart.data[0] || {})[1]
        return (
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey={xKey} name={xKey} fontSize={12} />
              <YAxis dataKey={yKey} name={yKey} fontSize={12} />
              <Tooltip 
                cursor={{ strokeDasharray: '3 3' }}
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
              {renderAnnotations()}
              <Scatter
                name={chart.title}
                data={chart.data}
                fill={CHART_COLORS[0]}
              />
            </ScatterChart>
          </ResponsiveContainer>
        )

      case 'sankey':
        // Sankey charts require a specialized library (react-sankey or recharts extensions)
        // For now, display a placeholder with instructions
        return (
          <div className="flex items-center justify-center h-[400px] bg-muted/30 rounded-lg border-2 border-dashed">
            <div className="text-center space-y-2 p-6">
              <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground" />
              <h3 className="font-semibold text-lg">Sankey Diagram</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Flow visualization showing relationships and proportions between entities. 
                Requires specialized Sankey chart library for rendering.
              </p>
              <Badge variant="outline">Data Available: {chart.data.length} nodes</Badge>
            </div>
          </div>
        )

      case 'heatmap':
        // Heatmaps require specialized rendering
        return (
          <div className="flex items-center justify-center h-[400px] bg-muted/30 rounded-lg border-2 border-dashed">
            <div className="text-center space-y-2 p-6">
              <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground" />
              <h3 className="font-semibold text-lg">Heatmap</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Intensity-based visualization showing patterns and correlations. 
                Requires specialized heatmap library for rendering.
              </p>
              <Badge variant="outline">Data Available: {chart.data.length} points</Badge>
            </div>
          </div>
        )

      case 'radar':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <RadarChart {...commonProps}>
              <PolarGrid />
              <PolarAngleAxis dataKey={chart.xAxis || 'name'} fontSize={12} />
              <PolarRadiusAxis fontSize={12} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
              {Object.keys(chart.data[0] || {})
                .filter(key => key !== chart.xAxis && key !== 'name')
                .map((key, index) => (
                  <Radar
                    key={key}
                    name={key}
                    dataKey={key}
                    stroke={CHART_COLORS[index % CHART_COLORS.length]}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                    fillOpacity={0.6}
                  />
                ))}
            </RadarChart>
          </ResponsiveContainer>
        )

      case 'radialbar':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <RadialBarChart
              innerRadius="10%"
              outerRadius="80%"
              data={chart.data}
              startAngle={180}
              endAngle={0}
            >
              <PolarGrid />
              <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
              <RadialBar
                background
                dataKey={Object.keys(chart.data[0] || {}).find(key => key !== 'name') || 'value'}
                cornerRadius={10}
                label={{ position: 'insideStart', fill: '#fff' }}
              >
                {chart.data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </RadialBar>
              <Legend iconSize={10} layout="vertical" verticalAlign="middle" align="right" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
            </RadialBarChart>
          </ResponsiveContainer>
        )

      case 'histogram':
        // Histogram uses bar chart with calculated bins
        return (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey={chart.xAxis || 'bin'} fontSize={12} label={{ value: 'Range', position: 'insideBottom', offset: -5 }} />
              <YAxis fontSize={12} label={{ value: 'Frequency', angle: -90, position: 'insideLeft' }} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
              <Bar
                dataKey={Object.keys(chart.data[0] || {}).find(key => key !== chart.xAxis && key !== 'bin') || 'frequency'}
                fill={CHART_COLORS[0]}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )

      case 'boxplot':
        // BoxPlot representation using custom rendering
        return (
          <div className="h-[400px] p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart {...commonProps} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis type="number" fontSize={12} />
                <YAxis dataKey={chart.xAxis || 'name'} type="category" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                    border: '1px solid #ccc',
                    borderRadius: '8px'
                  }} 
                />
                <Legend />
                {['min', 'q1', 'median', 'q3', 'max'].map((key, index) => {
                  if (chart.data[0] && key in chart.data[0]) {
                    return (
                      <Bar
                        key={key}
                        dataKey={key}
                        fill={CHART_COLORS[index % CHART_COLORS.length]}
                        fillOpacity={0.7}
                      />
                    )
                  }
                  return null
                })}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )

      case 'funnel':
        // Funnel chart using trapezoid bars
        const maxValue = Math.max(...chart.data.map(d => Number(Object.values(d).find(v => typeof v === 'number') || 0)))
        return (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              {...commonProps}
              layout="vertical"
              margin={{ top: 20, right: 50, left: 50, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis type="number" domain={[0, maxValue]} fontSize={12} />
              <YAxis dataKey={chart.xAxis || 'name'} type="category" fontSize={12} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
              <Bar
                dataKey={Object.keys(chart.data[0] || {}).find(key => key !== chart.xAxis && key !== 'name') || 'value'}
                fill={CHART_COLORS[0]}
                radius={[0, 8, 8, 0]}
              >
                {chart.data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )

      default:
        return (
          <div className="flex items-center justify-center h-[400px] bg-muted/30 rounded-lg">
            <p className="text-muted-foreground">Unsupported chart type: {chart.type}</p>
          </div>
        )
    }
  }

  return (
    <Card className="border-primary/20">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            {getChartTypeIcon()}
            {chart.title}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="capitalize">
              {chart.type}
            </Badge>
            {chart.compareMode && (
              <Badge variant="secondary">Compare Mode</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {renderChart()}
        
        {/* Annotations Legend */}
        {chart.annotations && chart.annotations.length > 0 && (
          <div className="mt-4 p-3 bg-muted/30 rounded-lg">
            <p className="text-xs font-semibold mb-2">Annotations:</p>
            <div className="flex flex-wrap gap-3 text-xs">
              {chart.annotations.map((annotation, index) => (
                <div key={index} className="flex items-center gap-2">
                  <div 
                    className={`w-8 h-0.5 ${
                      annotation.type === 'threshold' ? 'bg-red-600' :
                      annotation.type === 'target' ? 'bg-green-600' :
                      'bg-yellow-600'
                    }`}
                    style={{ 
                      borderTop: annotation.type === 'threshold' ? '2px dashed' :
                                annotation.type === 'target' ? '2px dashed' :
                                '2px dashed'
                    }}
                  />
                  <span className="text-muted-foreground">{annotation.label}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
