export type WidgetType = 'bar' | 'line' | 'area' | 'pie' | 'kpi' | 'radar' | 'scatter' | 'funnel' | 'composed' | 'sankey';
export type WidgetSize = 'small' | 'medium' | 'large';

export interface WidgetMeta {
  isTimeSeries?: boolean;
  hasCategories?: boolean;
  numSeries?: number;
  variance?: number;
  trend?: 'up' | 'down' | 'stable';
}

export interface Widget {
  id: string;
  title: string;
  subtitle?: string;
  type: WidgetType;
  data: any; // array for most charts; { nodes, links } for sankey
  size: WidgetSize;
  xKey?: string;
  yKeys?: string[];
  insights?: string[];
  priority: number;
  meta?: WidgetMeta;
}

export type StoryPhase = 'exec' | 'define' | 'measure' | 'analyze' | 'improve' | 'control';
export type StoryIcon = 'activity' | 'target' | 'bar-chart' | 'search' | 'trending-up' | 'shield';

export interface StoryBlock {
  id: string;
  phase: StoryPhase;
  title: string;
  narrative: string;
  widgets: Widget[];
  priority: number;
  icon: StoryIcon;
}
