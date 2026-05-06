
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Lightbulb, TrendingUp, AlertTriangle, CheckCircle, Info, AlertCircle } from 'lucide-react';

interface Insights {
  summary: string;
  trends: string[];
  alerts: Array<{
    type: string;
    message: string;
    severity: 'high' | 'medium' | 'low';
    action: string;
    threshold?: number;
    currentValue?: number;
    metric?: string;
  }>;
  recommendations: string[];
}

interface InsightsSectionProps {
  insights: Insights;
}

const InsightsSection = ({ insights }: InsightsSectionProps) => {
  const getAlertIcon = (severity: string) => {
    switch (severity) {
      case 'high':   return <AlertCircle   className="h-5 w-5 text-red-400" />;
      case 'medium': return <AlertTriangle className="h-5 w-5 text-yellow-400" />;
      default:       return <Info          className="h-5 w-5 text-blue-400" />;
    }
  };

  const getAlertColor = (severity: string) => {
    switch (severity) {
      case 'high':   return 'border-l-red-500 bg-red-500/10';
      case 'medium': return 'border-l-yellow-500 bg-yellow-500/10';
      default:       return 'border-l-blue-500 bg-blue-500/10';
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'high':
        return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">HIGH</Badge>;
      case 'medium':
        return <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">MEDIUM</Badge>;
      case 'low':
        return <Badge className="bg-green-500/20 text-green-400 border-green-500/30">LOW</Badge>;
      default:
        return <Badge className="bg-slate-500/20 text-slate-400 border-slate-500/30">LOW</Badge>;
    }
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Summary Card */}
        <Card className="bg-slate-800/50 border-slate-700/60 backdrop-blur-sm">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center text-sm font-semibold text-white gap-2">
              <Lightbulb className="h-4 w-4 text-yellow-400" />
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-slate-300 text-sm leading-relaxed">{insights.summary}</p>
          </CardContent>
        </Card>

        {/* Trends Card */}
        {(insights.trends || []).length > 0 && (
          <Card className="bg-slate-800/50 border-slate-700/60 backdrop-blur-sm">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center text-sm font-semibold text-white gap-2">
                <TrendingUp className="h-4 w-4 text-green-400" />
                Key Trends
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {(insights.trends || []).map((trend, index) => (
                  <li key={index} className="flex items-start text-slate-300 gap-2">
                    <span className="w-1.5 h-1.5 bg-green-400 rounded-full mt-1.5 flex-shrink-0"></span>
                    <span className="text-sm leading-relaxed">{trend}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Alerts Section */}
      {(insights.alerts || []).length > 0 && (
        <Card className="bg-slate-800/50 border-slate-700/60 backdrop-blur-sm">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center text-sm font-semibold text-white gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-400" />
              Alerts & Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(insights.alerts || []).map((alert, index) => {
                const thresholdPct = alert.threshold && alert.currentValue != null
                  ? Math.round((alert.currentValue / alert.threshold) * 100) : null;
                const overThreshold = thresholdPct !== null && thresholdPct > 100;
                return (
                  <div key={index} className={`border-l-4 p-3 rounded-r-lg ${getAlertColor(alert.severity)}`}>
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex items-start gap-2">
                        {getAlertIcon(alert.severity)}
                        <span className="font-medium text-white text-xs leading-snug">{alert.message}</span>
                      </div>
                      {getSeverityBadge(alert.severity)}
                    </div>
                    {thresholdPct !== null && (
                      <div className="mt-2 ml-7">
                        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${overThreshold ? 'bg-red-500' : 'bg-amber-400'}`}
                            style={{ width: `${Math.min(thresholdPct, 100)}%` }} />
                        </div>
                      </div>
                    )}
                    <p className="text-xs text-slate-400 mt-1.5 ml-7"><strong className="text-slate-300">Action:</strong> {alert.action}</p>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {(insights.recommendations || []).length > 0 && (
        <Card className="bg-slate-800/50 border-slate-700/60 backdrop-blur-sm">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center text-sm font-semibold text-white gap-2">
              <CheckCircle className="h-4 w-4 text-blue-400" />
              Strategic Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(insights.recommendations || []).map((recommendation, index) => (
                <div key={index} className="flex items-start gap-2 p-3 bg-blue-500/8 rounded-lg border border-blue-500/20">
                  <span className="flex-shrink-0 w-5 h-5 bg-blue-500/20 text-blue-400 text-[10px] font-bold rounded-full flex items-center justify-center mt-0.5">
                    {index + 1}
                  </span>
                  <p className="text-slate-300 text-xs leading-relaxed">{recommendation}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default InsightsSection;
