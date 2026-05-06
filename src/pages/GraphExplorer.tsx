import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, Search, Network, GitBranch, BarChart3, Info,
  Loader2, ChevronRight, Target, X, Maximize2, Filter
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts';
import {
  searchEntities, getEntity, getRelatedEntities, getRelationships,
  findPaths, getCentrality, listEntities,
  type GraphEntity, type EntityDetail, type GraphRelationship,
  type PathResult, type CentralityResult
} from '@/api/graphClient';

// ── Entity Search ───────────────────────────────────────────────────────────

const EntitySearch: React.FC<{
  onSelect: (entity: GraphEntity) => void;
}> = ({ onSelect }) => {
  const [query, setQuery] = useState('');
  const [activeQuery, setActiveQuery] = useState('');

  const searchQ = useQuery({
    queryKey: ['graph-search', activeQuery],
    queryFn: () => searchEntities(activeQuery, undefined, 20),
    enabled: activeQuery.length >= 2,
  });

  const handleSearch = () => {
    if (query.length >= 2) setActiveQuery(query);
  };

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <Search className="h-5 w-5 text-cyan-400" />
          Entity Search
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2 mb-4">
          <Input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Search entities (e.g. 'well', 'rig', 'cost')..."
            className="bg-slate-700/50 border-slate-600 text-slate-200"
          />
          <Button onClick={handleSearch} disabled={query.length < 2} className="bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 border-cyan-500/30" variant="outline">
            <Search className="h-4 w-4" />
          </Button>
        </div>

        {searchQ.isLoading && (
          <div className="flex items-center justify-center py-6"><Loader2 className="h-5 w-5 animate-spin text-cyan-400" /></div>
        )}

        {searchQ.data && searchQ.data.results.length === 0 && (
          <p className="text-sm text-slate-500 text-center py-4">No entities found for "{activeQuery}"</p>
        )}

        {searchQ.data && searchQ.data.results.length > 0 && (
          <div className="space-y-1 max-h-64 overflow-auto">
            {searchQ.data.results.map(entity => (
              <button
                key={entity.entity_id}
                onClick={() => onSelect(entity)}
                className="w-full flex items-center justify-between p-2.5 rounded-lg bg-slate-700/30 hover:bg-slate-700/50 transition-colors text-left"
              >
                <div>
                  <span className="text-sm font-medium text-slate-200">{entity.name}</span>
                  <Badge variant="outline" className="text-xs ml-2 text-slate-400">{entity.entity_type}</Badge>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">{entity.mention_count} mentions</span>
                  <ChevronRight className="h-4 w-4 text-slate-500" />
                </div>
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ── Entity Detail Drawer ────────────────────────────────────────────────────

const EntityDetailPanel: React.FC<{
  entityId: string;
  onClose: () => void;
  onNavigate: (entity: GraphEntity) => void;
}> = ({ entityId, onClose, onNavigate }) => {
  const detailQ = useQuery({
    queryKey: ['graph-entity', entityId],
    queryFn: () => getEntity(entityId),
    enabled: !!entityId,
  });

  const relatedQ = useQuery({
    queryKey: ['graph-related', entityId],
    queryFn: () => getRelatedEntities(entityId),
    enabled: !!entityId,
  });

  const relsQ = useQuery({
    queryKey: ['graph-relationships', entityId],
    queryFn: () => getRelationships(entityId),
    enabled: !!entityId,
  });

  const entity = detailQ.data;
  const loading = detailQ.isLoading;

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <Info className="h-5 w-5 text-cyan-400" />
          Entity Detail
          <Button variant="ghost" size="sm" className="ml-auto text-slate-400" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-32 w-full" />
        ) : entity ? (
          <div className="space-y-4">
            {/* Entity info */}
            <div className="bg-slate-700/30 rounded-lg p-3">
              <h3 className="text-base font-semibold text-white">{entity.name}</h3>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className="text-xs">{entity.entity_type}</Badge>
                <span className="text-xs text-slate-500">{entity.mention_count} mentions</span>
                {entity.pagerank !== undefined && <span className="text-xs text-slate-500">PR: {entity.pagerank.toFixed(3)}</span>}
              </div>
            </div>

            {/* Mentions */}
            {entity.mentions && entity.mentions.length > 0 && (
              <div>
                <span className="text-xs font-medium text-slate-400 mb-1 block">Mentions ({entity.mentions.length})</span>
                <div className="space-y-1 max-h-32 overflow-auto">
                  {entity.mentions.slice(0, 5).map((m, i) => (
                    <div key={i} className="text-xs text-slate-400 bg-slate-700/20 rounded p-2">
                      <span className="text-cyan-400">"{m.text}"</span> — {m.context?.slice(0, 100) || 'No context'}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Relationships */}
            {relsQ.data?.relationships && relsQ.data.relationships.length > 0 && (
              <div>
                <span className="text-xs font-medium text-slate-400 mb-1 block">Relationships ({relsQ.data.relationships.length})</span>
                <div className="space-y-1 max-h-32 overflow-auto">
                  {relsQ.data.relationships.map((rel, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs bg-slate-700/20 rounded p-2">
                      <span className="text-slate-300">{rel.source_name || rel.source_entity_id}</span>
                      <Badge variant="outline" className="text-xs text-cyan-400 border-cyan-500/30">{rel.relationship_type}</Badge>
                      <span className="text-slate-300">{rel.target_name || rel.target_entity_id}</span>
                      <span className="text-slate-500 ml-auto">{(rel.confidence * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Related entities */}
            {relatedQ.data?.related && relatedQ.data.related.length > 0 && (
              <div>
                <span className="text-xs font-medium text-slate-400 mb-1 block">Related Entities</span>
                <div className="flex flex-wrap gap-1">
                  {relatedQ.data.related.slice(0, 10).map(re => (
                    <button
                      key={re.entity_id}
                      onClick={() => onNavigate(re)}
                      className="text-xs bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded-full px-2 py-0.5 hover:bg-cyan-500/20 transition-colors"
                    >
                      {re.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-500 text-center py-4">Entity not found</p>
        )}
      </CardContent>
    </Card>
  );
};

// ── Path Finder ─────────────────────────────────────────────────────────────

const PathFinderPanel: React.FC = () => {
  const [sourceId, setSourceId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [activeSearch, setActiveSearch] = useState<{ s: string; t: string } | null>(null);

  const pathQ = useQuery({
    queryKey: ['graph-path', activeSearch?.s, activeSearch?.t],
    queryFn: () => findPaths(activeSearch!.s, activeSearch!.t),
    enabled: !!activeSearch,
  });

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <GitBranch className="h-5 w-5 text-cyan-400" />
          Path Finder
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-4">
          <Input value={sourceId} onChange={e => setSourceId(e.target.value)} placeholder="Source entity ID" className="bg-slate-700/50 border-slate-600 text-slate-200" />
          <Input value={targetId} onChange={e => setTargetId(e.target.value)} placeholder="Target entity ID" className="bg-slate-700/50 border-slate-600 text-slate-200" />
          <Button
            onClick={() => setActiveSearch({ s: sourceId, t: targetId })}
            disabled={!sourceId || !targetId}
            className="bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 border-cyan-500/30"
            variant="outline"
          >
            <Target className="h-4 w-4 mr-1" /> Find Path
          </Button>
        </div>

        {pathQ.isLoading && <div className="flex items-center justify-center py-6"><Loader2 className="h-5 w-5 animate-spin text-cyan-400" /></div>}

        {pathQ.data && (
          <div>
            <div className="flex items-center gap-1 mb-2">
              <Badge variant="outline" className="text-xs text-cyan-400 border-cyan-500/30">
                {pathQ.data.length} hops
              </Badge>
            </div>
            {pathQ.data.path && pathQ.data.path.length > 0 ? (
              <div className="flex items-center gap-1 flex-wrap">
                {pathQ.data.path.map((node, i) => (
                  <React.Fragment key={node.entity_id}>
                    <span className="text-sm bg-slate-700/40 rounded-lg px-2 py-1 text-slate-200">{node.name}</span>
                    {i < pathQ.data!.path.length - 1 && (
                      <ChevronRight className="h-4 w-4 text-cyan-400" />
                    )}
                  </React.Fragment>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No path found between these entities</p>
            )}
            {pathQ.data.hops && pathQ.data.hops.length > 0 && (
              <div className="mt-3 space-y-1">
                {pathQ.data.hops.map((hop, i) => (
                  <div key={i} className="text-xs text-slate-400 flex items-center gap-1">
                    <span className="text-slate-300">{hop.from}</span>
                    <Badge variant="outline" className="text-xs text-cyan-400 border-cyan-500/30">{hop.relationship}</Badge>
                    <span className="text-slate-300">{hop.to}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ── Centrality Panel ────────────────────────────────────────────────────────

const CentralityPanel: React.FC = () => {
  const [metric, setMetric] = useState<'degree' | 'closeness' | 'betweenness'>('degree');

  const centralityQ = useQuery({
    queryKey: ['graph-centrality', metric],
    queryFn: () => getCentrality(metric, 15),
  });

  const data = centralityQ.data?.results || [];
  const chartData = data.slice(0, 15).map(r => ({
    name: r.entity.name.length > 18 ? r.entity.name.slice(0, 18) + '…' : r.entity.name,
    score: Number(r.score.toFixed(4)),
  }));

  const COLORS = ['#06b6d4', '#0891b2', '#0e7490', '#155e75', '#164e63'];

  return (
    <Card className="bg-slate-800/60 border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-white">
          <BarChart3 className="h-5 w-5 text-cyan-400" />
          Centrality Analysis
          <div className="ml-auto flex gap-1">
            {(['degree', 'closeness', 'betweenness'] as const).map(m => (
              <Button
                key={m}
                variant="outline"
                size="sm"
                onClick={() => setMetric(m)}
                className={`text-xs capitalize ${metric === m ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' : 'text-slate-400 border-slate-600'}`}
              >
                {m}
              </Button>
            ))}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {centralityQ.isLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : chartData.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">No centrality data available</p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis type="category" dataKey="name" width={130} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }} />
                <Bar dataKey="score" barSize={14} radius={[0, 4, 4, 0]}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ── Main Graph Explorer Page ────────────────────────────────────────────────

const GraphExplorer: React.FC = () => {
  const [selectedEntity, setSelectedEntity] = useState<GraphEntity | null>(null);

  const handleEntitySelect = (entity: GraphEntity) => {
    setSelectedEntity(entity);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Link to="/">
            <Button variant="ghost" size="sm" className="text-cyan-400 hover:text-cyan-300">
              <ArrowLeft className="h-4 w-4 mr-1" /> Home
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Network className="h-6 w-6 text-cyan-400" />
            <h1 className="text-2xl font-bold text-white">Knowledge Graph Explorer</h1>
          </div>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="search" className="w-full">
          <TabsList className="bg-slate-800/80 border border-slate-700">
            <TabsTrigger value="search" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Search & Browse</TabsTrigger>
            <TabsTrigger value="paths" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Path Finder</TabsTrigger>
            <TabsTrigger value="centrality" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400">Centrality</TabsTrigger>
          </TabsList>

          <TabsContent value="search" className="mt-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <EntitySearch onSelect={handleEntitySelect} />
              {selectedEntity ? (
                <EntityDetailPanel
                  entityId={selectedEntity.entity_id}
                  onClose={() => setSelectedEntity(null)}
                  onNavigate={handleEntitySelect}
                />
              ) : (
                <Card className="bg-slate-800/60 border-slate-700">
                  <CardContent className="py-16 text-center text-slate-400">
                    <Network className="h-16 w-16 mx-auto mb-4 opacity-30" />
                    <p className="text-lg">Select an entity to explore</p>
                    <p className="text-sm text-slate-500 mt-1">Search and click on an entity to see its details, relationships, and connections</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          <TabsContent value="paths" className="mt-4">
            <PathFinderPanel />
          </TabsContent>

          <TabsContent value="centrality" className="mt-4">
            <CentralityPanel />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default GraphExplorer;
