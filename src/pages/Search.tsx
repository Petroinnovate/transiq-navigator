import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api, SearchResult } from '@/services/api';
import { useToast } from '@/hooks/use-toast';
import { Search as SearchIcon, Loader2 } from 'lucide-react';

export const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult['results']>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const { toast } = useToast();
  
  const handleSearch = async () => {
    if (!query.trim()) {
      toast({
        title: "Empty query",
        description: "Please enter a search query",
        variant: "destructive",
      });
      return;
    }
    
    setIsSearching(true);
    setHasSearched(true);
    try {
      const response = await api.searchDocuments({
        query,
        top_k: 10,
        use_hybrid: true,
      });
      
      setResults(response.results);
      
      toast({
        title: "Search complete",
        description: `Found ${response.count} results`,
      });
    } catch (error: any) {
      toast({
        title: "Search failed",
        description: error.response?.data?.detail || "Error performing search",
        variant: "destructive",
      });
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Search Documents</h1>
          <p className="text-slate-400">Search across all processed documents using hybrid search</p>
        </div>

        <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm mb-6">
          <CardContent className="p-6">
            <div className="flex space-x-2">
              <div className="flex-1 relative">
                <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Enter search query..."
                  onKeyPress={(e) => e.key === 'Enter' && !isSearching && handleSearch()}
                  className="pl-10 bg-slate-700/50 border-slate-600 text-white placeholder:text-slate-400"
                />
              </div>
              <Button 
                onClick={handleSearch} 
                disabled={isSearching}
                className="bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600 text-white px-6"
              >
                {isSearching ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <SearchIcon className="h-4 w-4 mr-2" />
                    Search
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
        
        {/* Results */}
        {hasSearched && (
          <div className="space-y-4">
            {results.length === 0 && !isSearching && (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-8 text-center">
                  <p className="text-slate-400">No results found for your query.</p>
                </CardContent>
              </Card>
            )}
            
            {results.map((result, idx) => (
              <Card key={idx} className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <Badge variant="secondary" className="bg-cyan-500/20 text-cyan-400 border-cyan-500/50">
                        #{result.index + 1}
                      </Badge>
                      <Badge variant="secondary" className="bg-purple-500/20 text-purple-400 border-purple-500/50">
                        Combined: {result.combined_score.toFixed(3)}
                      </Badge>
                    </div>
                    <div className="flex items-center space-x-2 text-xs text-slate-400">
                      <span>BM25: {result.bm25_score.toFixed(3)}</span>
                      <span>•</span>
                      <span>Semantic: {result.semantic_score.toFixed(3)}</span>
                    </div>
                  </div>
                  <p className="text-white leading-relaxed">{result.text}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchPage;

