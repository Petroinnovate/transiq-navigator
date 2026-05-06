import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Widget } from '@/types/widget';
import { widgetToChartConfig } from '@/utils/visualizationEngine';
import KPIWidget from './KPIWidget';
import {
    AreaChart,
    Area,
    BarChart,
    Bar,
    LineChart,
    Line,
    ComposedChart,
    PieChart,
    Pie,
    RadarChart,
    Radar,
    RadialBarChart,
    RadialBar,
    Sankey,
    ScatterChart,
    Scatter,
    FunnelChart,
    Funnel,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Cell,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    LabelList,
    Rectangle,
    Layer,
    Brush
} from 'recharts';

interface ChartConfig {
    xAxis?: {
        dataKey: string;
        label: string;
        type: 'category' | 'number' | 'time';
    };
    yAxis?: {
        label: string;
        domain: [string | number, string | number];
    };
    series?: Array<{
        dataKey: string;
        name: string;
        type: 'bar' | 'line' | 'area';
        color?: string;
        fill?: string;
        stroke?: string;
    }>;
    composedComponents?: Array<{
        type: 'Bar' | 'Line' | 'Area';
        dataKey: string;
        name: string;
        color?: string;
        fill?: string;
        stroke?: string;
    }>;
}

interface SankeyData {
    nodes: Array<{
        name: string;
    }>;
    links: Array<{
        source: number;
        target: number;
        value: number;
    }>;
}

interface ChartData {
    id: string;
    type: 'AreaChart' | 'BarChart' | 'LineChart' | 'ComposedChart' | 'PieChart' | 'RadarChart' | 'RadialBarChart' | 'ScatterChart' | 'FunnelChart' | 'SankeyChart';
    title: string;
    subtitle?: string;
    size: 'full' | 'half' | 'third' | 'quarter';
    chartConfig: ChartConfig;
    data: Array<Record<string, any>> | SankeyData;
    insights?: string[];
}

interface ChartRendererProps {
    chartData?: ChartData;
    widget?: Widget;
}

function transformData(data: Record<string, any>[]) {
    if (!Array.isArray(data)) {
        console.warn('transformData expects an array, received:', typeof data);
        return [];
    }

    return data.map(entry => {
        if (!entry || typeof entry !== 'object') {
            return {
                name: "Unknown",
                value: 0,
                color: "#ccc",
            };
        }

        const nameKey = Object.keys(entry).find(
            key => typeof entry[key] === "string" && key !== "color"
        );
        const valueKey = Object.keys(entry).find(
            key => typeof entry[key] === "number"
        );

        return {
            name: nameKey ? entry[nameKey] : "Unknown",
            value: valueKey ? entry[valueKey] : 0,
            color: entry.color || "#ccc",
        };
    });
}

const ChartRenderer = ({ chartData, widget }: ChartRendererProps) => {
    // Resolve: widget prop takes precedence; fall back to chartData
    const resolved: ChartData = widget ? widgetToChartConfig(widget) as ChartData : chartData!;
    const { id, type, title, subtitle, chartConfig, data, insights } = resolved;

    // KPI widget — rendered as a grid of stat cards
    if (widget?.type === 'kpi') {
        return <KPIWidget kpis={widget.data} title={widget.title} insights={widget.insights} />;
    }

    const [isExpanded, setIsExpanded] = useState(false);
    const [barLineMode, setBarLineMode] = useState<'bar' | 'line'>(
        type === 'LineChart' ? 'line' : 'bar'
    );

    const colors = ['#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6', '#f97316', '#84cc16'];

    const tooltipStyle = {
        backgroundColor: '#1e293b',
        border: '1px solid #475569',
        borderRadius: '8px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
        color: '#f1f5f9',
        fontSize: '12px',
        padding: '8px 12px',
        lineHeight: '1.4'
    };

    const tooltipLabelStyle = {
        color: '#f1f5f9',
        fontWeight: '500'
    };

    const tooltipItemStyle = {
        color: '#f1f5f9',
        fontSize: '12px'
    };

    // Custom tooltip component to ensure proper styling
    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div style={tooltipStyle}>
                    {label && (
                        <p style={tooltipLabelStyle}>{`${label}`}</p>
                    )}
                    {payload.map((entry: any, index: number) => (
                        <p key={index} style={{ ...tooltipItemStyle, color: entry.color || '#f1f5f9' }}>
                            {`${entry.name}: ${entry.value}`}
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };

    const legendStyle = {
        color: '#ffffff'
    };

    // Bar ↔ Line toggle: only applies to pure BarChart / LineChart
    const canToggleBarLine = type === 'BarChart' || type === 'LineChart';
    const effectiveType: ChartData['type'] = canToggleBarLine
        ? (barLineMode === 'line' ? 'LineChart' : 'BarChart')
        : type;

    // chartId used to namespace SVG gradient IDs so multiple charts on a page don't collide
    const chartId = (id || 'chart').replace(/[^a-zA-Z0-9_-]/g, '_');

    const renderChart = (height = 300) => {
        let dataval: any[];

        // Helper function to safely get array data
        const getArrayData = () => {
            if (Array.isArray(data)) {
                return data;
            }
            console.warn('Expected array data but received:', typeof data);
            return [];
        };

        switch (effectiveType) {
            case 'AreaChart': {
                dataval = getArrayData();
                const gradientIds = (chartConfig.series || []).map((_, i) => `grad-${chartId}-${i}`);
                return (
                    <ResponsiveContainer width="100%" height={height}>
                        <AreaChart data={dataval} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                            <defs>
                                {chartConfig.series?.map((series, index) => {
                                    const color = series.stroke || series.color || colors[index % colors.length];
                                    return (
                                        <linearGradient key={index} id={gradientIds[index]} x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor={color} stopOpacity={0.45} />
                                            <stop offset="95%" stopColor={color} stopOpacity={0.04} />
                                        </linearGradient>
                                    );
                                })}
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                            <XAxis
                                dataKey={chartConfig.xAxis?.dataKey || 'category'}
                                stroke="#94a3b8"
                                fontSize={12}
                            />
                            <YAxis
                                stroke="#94a3b8"
                                fontSize={12}
                                domain={chartConfig.yAxis?.domain || ['auto', 'auto']}
                            />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={legendStyle} />
                            {chartConfig.series?.map((series, index) => (
                                <Area
                                    key={index}
                                    type="monotone"
                                    dataKey={series.dataKey}
                                    name={series.name}
                                    stroke={series.stroke || series.color || colors[index % colors.length]}
                                    strokeWidth={2}
                                    fill={`url(#${gradientIds[index]})`}
                                    fillOpacity={1}
                                />
                            ))}
                            {dataval.length > 6 && (
                                <Brush
                                    dataKey={chartConfig.xAxis?.dataKey || 'category'}
                                    height={22}
                                    stroke="#475569"
                                    fill="#1e293b"
                                    travellerWidth={6}
                                />
                            )}
                        </AreaChart>
                    </ResponsiveContainer>
                );
            }

            case 'BarChart': {
                dataval = getArrayData();
                if (dataval.length === 0) {
                    return (
                        <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
                            No data available for this chart.
                        </div>
                    );
                }
                return (
                    <ResponsiveContainer width="100%" height={height}>
                        <BarChart data={dataval} margin={{ top: 18, bottom: 20, left: 0, right: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                            <XAxis
                                dataKey={chartConfig.xAxis?.dataKey || 'name'}
                                stroke="#94a3b8"
                                fontSize={11}
                                tick={{ fill: '#94a3b8' }}
                                angle={dataval.length > 6 ? -35 : 0}
                                textAnchor={dataval.length > 6 ? 'end' : 'middle'}
                                interval={0}
                            />
                            <YAxis
                                stroke="#94a3b8"
                                fontSize={11}
                                tick={{ fill: '#94a3b8' }}
                                domain={chartConfig.yAxis?.domain || ['auto', 'auto']}
                            />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={legendStyle} />
                            {chartConfig.series?.map((series, index) => (
                                <Bar
                                    key={index}
                                    dataKey={series.dataKey}
                                    name={series.name}
                                    fill={series.fill || series.color || colors[index % colors.length]}
                                    radius={[4, 4, 0, 0]}
                                >
                                    <LabelList
                                        dataKey={series.dataKey}
                                        position="top"
                                        fill="#94a3b8"
                                        fontSize={10}
                                    />
                                </Bar>
                            ))}
                        </BarChart>
                    </ResponsiveContainer>
                );
            }

            case 'LineChart': {
                dataval = getArrayData();
                const showBrush = dataval.length > 6;
                return (
                    <ResponsiveContainer width="100%" height={height}>
                        <LineChart data={dataval} margin={{ top: 5, right: 5, left: 0, bottom: showBrush ? 0 : 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                            <XAxis
                                dataKey={chartConfig.xAxis?.dataKey || 'category'}
                                stroke="#94a3b8"
                                fontSize={12}
                            />
                            <YAxis
                                stroke="#94a3b8"
                                fontSize={12}
                                domain={chartConfig.yAxis?.domain || ['auto', 'auto']}
                            />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={legendStyle} />
                            {chartConfig.series?.map((series, index) => (
                                <Line
                                    key={index}
                                    type="monotone"
                                    dataKey={series.dataKey}
                                    name={series.name}
                                    stroke={series.stroke || series.color || colors[index % colors.length]}
                                    strokeWidth={2}
                                    dot={{ r: 4 }}
                                    activeDot={{ r: 6 }}
                                />
                            ))}
                            {showBrush && (
                                <Brush
                                    dataKey={chartConfig.xAxis?.dataKey || 'category'}
                                    height={22}
                                    stroke="#475569"
                                    fill="#1e293b"
                                    travellerWidth={6}
                                />
                            )}
                        </LineChart>
                    </ResponsiveContainer>
                );
            }

            case 'ComposedChart':
                dataval = getArrayData();
                return (
                    <ResponsiveContainer width="100%" height={height}>
                        <ComposedChart data={dataval}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                            <XAxis
                                dataKey={chartConfig.xAxis?.dataKey || 'category'}
                                stroke="#94a3b8"
                                fontSize={12}
                            />
                            <YAxis
                                stroke="#94a3b8"
                                fontSize={12}
                                domain={chartConfig.yAxis?.domain || ['auto', 'auto']}
                            />
                            <Tooltip contentStyle={tooltipStyle} />
                            <Legend wrapperStyle={legendStyle} />
                            {chartConfig.composedComponents?.map((component, index) => {
                                const color = component.color || colors[index % colors.length];
                                switch (component.type) {
                                    case 'Bar':
                                        return (
                                            <Bar
                                                key={index}
                                                dataKey={component.dataKey}
                                                name={component.name}
                                                fill={component.fill || color}
                                                radius={[4, 4, 0, 0]}
                                            />
                                        );
                                    case 'Line':
                                        return (
                                            <Line
                                                key={index}
                                                type="monotone"
                                                dataKey={component.dataKey}
                                                name={component.name}
                                                stroke={component.stroke || color}
                                                strokeWidth={2}
                                                dot={{ r: 4 }}
                                            />
                                        );
                                    case 'Area':
                                        return (
                                            <Area
                                                key={index}
                                                type="monotone"
                                                dataKey={component.dataKey}
                                                name={component.name}
                                                stroke={component.stroke || color}
                                                strokeWidth={2}
                                                fill={component.fill || color}
                                                fillOpacity={0.3}
                                            />
                                        );
                                    default:
                                        return null;
                                }
                            })}
                        </ComposedChart>
                    </ResponsiveContainer>
                );

            case 'PieChart': {
                // transformData once — extract name/value from any field shape
                dataval = transformData(getArrayData());
                if (dataval.length === 0) {
                    return (
                        <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
                            No data available for this chart.
                        </div>
                    );
                }
                const total = dataval.reduce((sum: number, d: any) => sum + (Number(d.value) || 0), 0);
                const totalFormatted = total >= 1_000_000
                    ? (total / 1_000_000).toFixed(1) + 'M'
                    : total >= 1_000
                    ? (total / 1_000).toFixed(1) + 'k'
                    : Number.isInteger(total) ? total.toString() : total.toFixed(2);
                const innerR = Math.round(height * 0.18);
                const outerR = Math.round(height * 0.27);
                return (
                    <div className="relative">
                        <ResponsiveContainer width="100%" height={height}>
                            <PieChart>
                                <Pie
                                    data={dataval}
                                    cx="50%"
                                    cy="45%"
                                    innerRadius={innerR}
                                    outerRadius={outerR}
                                    dataKey="value"
                                    strokeWidth={2}
                                    stroke="#1e293b"
                                >
                                    {dataval.map((_entry, index) => (
                                        <Cell
                                            key={`cell-${index}`}
                                            fill={colors[index % colors.length]}
                                        />
                                    ))}
                                </Pie>
                                <Tooltip content={<CustomTooltip />} />
                                <Legend wrapperStyle={legendStyle} />
                            </PieChart>
                        </ResponsiveContainer>
                        {total > 0 && (
                            <div
                                className="absolute pointer-events-none"
                                style={{ top: '45%', left: '50%', transform: 'translate(-50%, -50%)' }}
                            >
                                <div className="text-center">
                                    <div className="text-lg font-bold text-white leading-tight">{totalFormatted}</div>
                                    <div className="text-xs text-slate-400 mt-0.5">Total</div>
                                </div>
                            </div>
                        )}
                    </div>
                );
            }

            case 'RadarChart':
                dataval = getArrayData();
                return (
                    <ResponsiveContainer width="100%" height={height}>
                        <RadarChart data={dataval}>
                            <PolarGrid />
                            <PolarAngleAxis dataKey="subject" />
                            <PolarRadiusAxis />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={legendStyle} />
                            {chartConfig.series?.map((series, index) => (
                                <Radar
                                    key={index}
                                    name={series.name}
                                    dataKey={series.dataKey}
                                    stroke={series.stroke || series.color || colors[index % colors.length]}
                                    fill={series.fill || series.color || colors[index % colors.length]}
                                    fillOpacity={0.6}
                                />
                            ))}
                        </RadarChart>
                    </ResponsiveContainer>
                );

            case 'RadialBarChart':
                dataval = getArrayData();
                return (
                    <ResponsiveContainer width="100%" height={height}>
                        <RadialBarChart data={dataval}>
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={legendStyle} />
                            {chartConfig.series?.map((series, index) => (
                                <RadialBar
                                    key={index}
                                    dataKey={series.dataKey}
                                    cornerRadius={10}
                                    fill={series.fill || series.color || colors[index % colors.length]}
                                />
                            ))}
                        </RadialBarChart>
                    </ResponsiveContainer>
                );

            case 'ScatterChart':
                dataval = getArrayData();
                return (
                    <ResponsiveContainer width="100%" height={height}>
                        <ScatterChart data={dataval}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                            <XAxis
                                dataKey={chartConfig.xAxis?.dataKey || 'x'}
                                stroke="#94a3b8"
                                fontSize={12}
                                type={chartConfig.xAxis?.type === 'time' ? 'category' : (chartConfig.xAxis?.type || 'number')}
                            />
                            <YAxis
                                stroke="#94a3b8"
                                fontSize={12}
                                domain={chartConfig.yAxis?.domain || ['auto', 'auto']}
                            />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend wrapperStyle={legendStyle} />
                            {chartConfig.series?.map((series, index) => (
                                <Scatter
                                    key={index}
                                    name={series.name}
                                    dataKey={series.dataKey}
                                    fill={series.fill || series.color || colors[index % colors.length]}
                                />
                            ))}
                        </ScatterChart>
                    </ResponsiveContainer>
                );

            case 'FunnelChart':
                dataval = transformData(getArrayData());
                return (
                    <ResponsiveContainer width="100%" height={height}>
                        <FunnelChart>
                            <Tooltip content={<CustomTooltip />} />
                            <Funnel
                                dataKey="value"
                                data={dataval}
                                isAnimationActive
                            >
                                {dataval.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={entry.color || colors[index % colors.length]}
                                    />
                                ))}
                                <LabelList position="right" fill="#ffffff" stroke="none" dataKey="name" />
                            </Funnel>
                        </FunnelChart>
                    </ResponsiveContainer>
                );

            case 'SankeyChart': {
                const sankeyData = data as SankeyData;
                const sankeyNodes = Array.isArray(sankeyData?.nodes) ? sankeyData.nodes : [];
                const sankeyLinks = Array.isArray(sankeyData?.links) ? sankeyData.links : [];
                if (sankeyNodes.length === 0 || sankeyLinks.length === 0) {
                    return (
                        <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
                            Sankey chart data is not available.
                        </div>
                    );
                }
                function Node({
                    x,
                    y,
                    width,
                    height: nodeHeight,
                    index,
                    payload,
                    containerWidth
                }: any) {
                    const isOut = x + width + 6 > containerWidth;
                    return (
                        <Layer key={`CustomNode${index}`}>
                            <Rectangle
                                x={x}
                                y={y}
                                width={width}
                                height={nodeHeight}
                                fill="#5192ca"
                                fillOpacity="1"
                            />
                            <text
                                textAnchor={isOut ? "end" : "start"}
                                x={isOut ? x - 6 : x + width + 6}
                                y={y + nodeHeight / 2}
                                fontSize="14"
                                fill="#ffffff"
                                stroke="none"
                            >
                                {payload.name}
                            </text>
                            <text
                                textAnchor={isOut ? "end" : "start"}
                                x={isOut ? x - 6 : x + width + 6}
                                y={y + nodeHeight / 2 + 13}
                                fontSize="12"
                                fill="#ffffff"
                                fillOpacity="0.7"
                                stroke="none"
                            >
                                {payload.value + "k"}
                            </text>
                        </Layer>
                    );
                }
                return (
                    <ResponsiveContainer width="100%" height={height}>
                        <Sankey data={{ nodes: sankeyNodes, links: sankeyLinks }} link={{ stroke: colors[0] }} node={<Node containerWidth={600} />}>
                            <Tooltip content={<CustomTooltip />} />
                        </Sankey>
                    </ResponsiveContainer>
                );
            }

            default:
                return (
                    <div className="flex items-center justify-center h-64 text-gray-500">
                        <div className="text-center">
                            <p className="text-lg font-medium">Unsupported Chart Type</p>
                            <p className="text-sm">Chart type "{effectiveType}" is not supported</p>
                        </div>
                    </div>
                );
        }
    };

    return (
        <>
            {/* Fullscreen expand modal */}
            {isExpanded && (
                <div
                    className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-6"
                    onClick={() => setIsExpanded(false)}
                >
                    <div
                        className="bg-slate-900 rounded-xl border border-slate-600 w-full max-w-5xl shadow-2xl"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between px-6 pt-5 pb-2">
                            <div>
                                <h2 className="text-xl font-semibold text-white">{title}</h2>
                                {subtitle && <p className="text-sm text-slate-400 mt-0.5">{subtitle}</p>}
                            </div>
                            <button
                                onClick={() => setIsExpanded(false)}
                                className="text-slate-400 hover:text-white transition-colors p-1.5 rounded hover:bg-slate-700"
                                aria-label="Close expanded chart"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                                </svg>
                            </button>
                        </div>
                        <div className="px-6 pb-6">
                            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
                                {renderChart(500)}
                            </div>
                            {insights && insights.length > 0 && (
                                <div className="mt-4 space-y-1.5">
                                    {insights.map((insight, i) => (
                                        <p key={i} className="text-sm text-slate-300 flex items-start gap-2">
                                            <span className="text-cyan-500 shrink-0 mt-0.5">•</span>
                                            {insight}
                                        </p>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm hover:border-cyan-500/50 transition-all duration-300 group">
                <CardHeader className="pb-4">
                    <div className="flex items-start gap-2">
                        <CardTitle className="text-xl font-semibold text-white text-center flex-1">
                            {title}
                        </CardTitle>
                        <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
                            {/* Bar / Line toggle — only for BarChart & LineChart */}
                            {canToggleBarLine && (
                                <div className="flex rounded overflow-hidden border border-slate-600 text-xs">
                                    <button
                                        onClick={() => setBarLineMode('bar')}
                                        className={`px-2 py-1 transition-colors ${barLineMode === 'bar' ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                                        title="Bar chart"
                                    >
                                        Bar
                                    </button>
                                    <button
                                        onClick={() => setBarLineMode('line')}
                                        className={`px-2 py-1 transition-colors ${barLineMode === 'line' ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                                        title="Line chart"
                                    >
                                        Line
                                    </button>
                                </div>
                            )}
                            {/* Fullscreen expand button */}
                            <button
                                onClick={() => setIsExpanded(true)}
                                className="text-slate-400 hover:text-cyan-400 transition-colors p-1 rounded hover:bg-slate-700"
                                title="Expand chart"
                                aria-label="Expand chart to full screen"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <polyline points="15 3 21 3 21 9" />
                                    <polyline points="9 21 3 21 3 15" />
                                    <line x1="21" y1="3" x2="14" y2="10" />
                                    <line x1="3" y1="21" x2="10" y2="14" />
                                </svg>
                            </button>
                        </div>
                    </div>
                    {subtitle && (
                        <p className="text-sm text-slate-400 text-center mt-1">{subtitle}</p>
                    )}
                </CardHeader>
                <CardContent className="pt-0">
                    <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-700/50">
                        {renderChart()}
                    </div>
                    {insights && insights.length > 0 && (
                        <div className="mt-3 space-y-1">
                            {insights.map((insight, i) => (
                                <p key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                                    <span className="text-cyan-500 shrink-0">•</span>
                                    {insight}
                                </p>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </>
    );
};

export default ChartRenderer;
