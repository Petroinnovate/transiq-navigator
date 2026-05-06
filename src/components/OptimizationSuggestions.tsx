
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, AlertTriangle, Zap, Shield, Award } from 'lucide-react';

interface OptimizationSuggestion {
  id: string;
  title: string;
  category: string;
  impact: string;
  savings: {
    value: number;
    unit: string;
    percentage: string;
    timeframe: string;
  };
  description: string;
  implementation: string;
  metrics: string[];
  priority: string;
  confidence: string | number;
  tags: string[];
  actionable: boolean;
  color?: string;
}

// Converts numeric confidence (0-1) or any value to a label string
const confidenceLabel = (confidence: string | number | any): string => {
  if (typeof confidence === 'string') return confidence;
  if (typeof confidence === 'number') {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.5) return 'medium';
    return 'low';
  }
  return String(confidence ?? 'medium');
};

interface OptimizationSuggestionsProps {
  suggestions: OptimizationSuggestion[];
}

const OptimizationSuggestions = ({ suggestions }: OptimizationSuggestionsProps) => {
  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'cost':
        return <TrendingUp className="h-5 w-5" />;
      case 'efficiency':
        return <Zap className="h-5 w-5" />;
      case 'performance':
        return <Award className="h-5 w-5" />;
      case 'risk':
        return <Shield className="h-5 w-5" />;
      default:
        return <AlertTriangle className="h-5 w-5" />;
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'low':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'low':
        return 'bg-green-500';
      default:
        return 'bg-slate-500';
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white mb-6 flex items-center">
        <div className="w-6 h-6 bg-gradient-to-r from-cyan-400 to-teal-400 rounded-full flex items-center justify-center mr-3">
          <span className="text-white text-sm">🎯</span>
        </div>
        Optimization Opportunities
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {suggestions.map((suggestion) => (
          <Card key={suggestion.id} className="bg-slate-800/50 border-slate-700 hover:border-cyan-500/50 transition-all duration-300 group backdrop-blur-sm">
            <CardHeader className="pb-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-lg bg-gradient-to-r from-cyan-400/20 to-teal-400/20 group-hover:from-cyan-400/30 group-hover:to-teal-400/30 transition-all duration-300">
                    <div className="text-cyan-400">
                      {getCategoryIcon(suggestion.category)}
                    </div>
                  </div>
                  <div className={`w-3 h-3 rounded-full ${getPriorityColor(suggestion.priority)}`}></div>
                </div>
                <Badge className={`${getImpactColor(suggestion.impact)} border font-medium`}>
                  {suggestion.impact.toUpperCase()}
                </Badge>
              </div>

              <CardTitle className="text-lg font-semibold text-white mt-3 group-hover:text-cyan-100 transition-colors">
                {suggestion.title}
              </CardTitle>

              <div className="flex items-center space-x-4 text-sm text-slate-400">
                <span className="capitalize">{suggestion.category}</span>
                <span className="text-slate-600">•</span>
                <span className="capitalize">{confidenceLabel(suggestion.confidence)} confidence</span>
              </div>
            </CardHeader>

            <CardContent className="pt-0">
              <p className="text-slate-300 mb-4 leading-relaxed">
                {suggestion.description}
              </p>

              {(suggestion.metrics || []).length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-slate-200 mb-2">Key Metrics:</h4>
                  <div className="flex flex-wrap gap-2">
                    {(suggestion.metrics || []).map((metric, index) => (
                      <Badge key={index} variant="outline" className="text-xs bg-slate-700/50 border-slate-600 text-slate-300">
                        {metric}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {(suggestion.tags || []).length > 0 && (
                <div className="mb-4">
                  <div className="flex flex-wrap gap-2">
                    {(suggestion.tags || []).map((tag, index) => (
                      <Badge key={index} variant="outline" className="text-xs bg-cyan-500/10 border-cyan-500/30 text-cyan-400">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between pt-4 border-t border-slate-700">
                <div className="text-sm text-slate-400">
                  Potential: <span className="text-green-400 font-medium">{suggestion.savings?.percentage ?? '—'}</span>
                </div>
                <div className="text-sm text-slate-400">
                  <span className="text-cyan-400 font-medium">
                    {confidenceLabel(suggestion.confidence).toUpperCase()}
                  </span> confidence
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default OptimizationSuggestions;
