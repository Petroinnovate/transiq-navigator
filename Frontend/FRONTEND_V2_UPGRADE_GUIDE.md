# Frontend v2.0 Upgrade Guide

## Overview

This document outlines all the changes needed in the frontend to integrate with the TransIQ Backend v2.0 API.

## Key Changes Summary

### 1. API Endpoint Updates
- **Old**: `/generate` (v1.0)
- **New**: `/api/v2/generate` (v2.0)
- **New Features**: Background processing with task tracking, WebSocket progress updates

### 2. New API Endpoints Available
- `/api/v2/search` - Hybrid search across documents
- `/api/v2/documents/{doc_id}` - Get document information
- `/api/v2/documents/{doc_id}/chunks` - Get document chunks
- `/api/v2/ws/{task_id}` - WebSocket for real-time progress

### 3. Response Structure Changes
- v2.0 returns `doc_id` and `task_id` immediately (async processing)
- Dashboard data needs to be fetched separately or via WebSocket

---

## Required Updates

### 1. Update API Base URL Configuration

**File**: `src/lib/axios.ts`

**Current**:
```typescript
baseURL: import.meta.env.VITE_API_URL || "http://localhost:8001"
```

**Update to**:
```typescript
baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000"  // v2.0 uses port 8000
```

**Also add**:
```typescript
// Add API version prefix helper
export const API_V2_BASE = '/api/v2';
```

---

### 2. Update Upload Page

**File**: `src/pages/Upload.tsx`

#### Changes Needed:

1. **Update API endpoint**:
   ```typescript
   // OLD
   const response = await axios.post('/generate', formData, { headers });
   
   // NEW
   const response = await axios.post('/api/v2/generate', formData, { 
     headers,
     params: {
       provider: 'gemini', // Optional: 'gemini' | 'openai'
       enable_deduction: true,
       enable_patterns: true
     }
   });
   ```

2. **Handle async response**:
   ```typescript
   // v2.0 returns immediately with task_id
   const { doc_id, task_id, status } = response.data;
   
   // Store task_id for progress tracking
   // Connect to WebSocket for progress updates
   ```

3. **Add WebSocket progress tracking**:
   ```typescript
   import { useEffect, useRef } from 'react';
   
   const wsRef = useRef<WebSocket | null>(null);
   
   useEffect(() => {
     if (task_id) {
       const ws = new WebSocket(`ws://localhost:8000/api/v2/ws/${task_id}`);
       wsRef.current = ws;
       
       ws.onmessage = (event) => {
         const data = JSON.parse(event.data);
         if (data.type === 'progress') {
           // Update progress UI
           setProgress(data.progress);
         } else if (data.type === 'completed') {
           // Fetch dashboard data
           fetchDashboardData(doc_id);
         }
       };
       
       return () => {
         ws.close();
       };
     }
   }, [task_id]);
   ```

4. **Add provider selection UI**:
   ```typescript
   const [selectedProvider, setSelectedProvider] = useState<'gemini' | 'openai'>('gemini');
   const [enableDeduction, setEnableDeduction] = useState(true);
   const [enablePatterns, setEnablePatterns] = useState(true);
   
   // Add UI controls for these options
   ```

---

### 3. Create New API Service Module

**File**: `src/services/api.ts` (NEW FILE)

```typescript
import axios from '@/lib/axios';

const API_V2_BASE = '/api/v2';

export interface UploadResponse {
  doc_id: string;
  task_id: string;
  status: 'processing' | 'completed' | 'failed';
  message: string;
}

export interface DocumentInfo {
  document: {
    id: string;
    file_name: string;
    status: string;
    created_at: string;
  };
  chunks_count: number;
  edges_count: number;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  use_hybrid?: boolean;
}

export interface SearchResult {
  query: string;
  results: Array<{
    index: number;
    text: string;
    bm25_score: number;
    semantic_score: number;
    combined_score: number;
  }>;
  count: number;
}

export const api = {
  // Upload document
  async uploadDocument(
    file: File,
    options?: {
      provider?: 'gemini' | 'openai';
      enable_deduction?: boolean;
      enable_patterns?: boolean;
    }
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const params = new URLSearchParams();
    if (options?.provider) params.append('provider', options.provider);
    if (options?.enable_deduction !== undefined) {
      params.append('enable_deduction', String(options.enable_deduction));
    }
    if (options?.enable_patterns !== undefined) {
      params.append('enable_patterns', String(options.enable_patterns));
    }
    
    const response = await axios.post(
      `${API_V2_BASE}/generate?${params.toString()}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    
    return response.data;
  },
  
  // Get document info
  async getDocument(docId: string): Promise<DocumentInfo> {
    const response = await axios.get(`${API_V2_BASE}/documents/${docId}`);
    return response.data;
  },
  
  // Get document chunks
  async getDocumentChunks(docId: string) {
    const response = await axios.get(`${API_V2_BASE}/documents/${docId}/chunks`);
    return response.data;
  },
  
  // Search documents
  async searchDocuments(request: SearchRequest): Promise<SearchResult> {
    const response = await axios.post(`${API_V2_BASE}/search`, request);
    return response.data;
  },
  
  // Health check
  async healthCheck() {
    const response = await axios.get(`${API_V2_BASE}/health`);
    return response.data;
  },
};

// WebSocket helper
export class ProgressWebSocket {
  private ws: WebSocket | null = null;
  private callbacks: Map<string, Function> = new Map();
  
  connect(taskId: string, onMessage: (data: any) => void) {
    const wsUrl = `ws://${window.location.hostname}:8000${API_V2_BASE}/ws/${taskId}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket closed');
    };
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
```

---

### 4. Update Dashboard Context

**File**: `src/contexts/DashboardContext.tsx`

#### Add new state:
```typescript
interface DashboardContextType {
  // ... existing fields
  docId: string | null;
  taskId: string | null;
  progress: number;
  setDocId: (id: string | null) => void;
  setTaskId: (id: string | null) => void;
  setProgress: (progress: number) => void;
}
```

#### Add progress tracking:
```typescript
const [docId, setDocId] = useState<string | null>(null);
const [taskId, setTaskId] = useState<string | null>(null);
const [progress, setProgress] = useState(0);
```

---

### 5. Create Progress Component

**File**: `src/components/ProcessingProgress.tsx` (NEW FILE)

```typescript
import React, { useEffect, useRef } from 'react';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { ProgressWebSocket } from '@/services/api';

interface ProcessingProgressProps {
  taskId: string;
  docId: string;
  onComplete: (docId: string) => void;
  onError: (error: string) => void;
}

export const ProcessingProgress: React.FC<ProcessingProgressProps> = ({
  taskId,
  docId,
  onComplete,
  onError,
}) => {
  const [progress, setProgress] = React.useState(0);
  const [currentStep, setCurrentStep] = React.useState('initializing');
  const wsRef = useRef<ProgressWebSocket | null>(null);
  
  useEffect(() => {
    const ws = new ProgressWebSocket();
    wsRef.current = ws;
    
    ws.connect(taskId, (data) => {
      if (data.type === 'progress') {
        setProgress(data.progress || 0);
        setCurrentStep(data.step || 'processing');
      } else if (data.type === 'completed') {
        setProgress(100);
        onComplete(docId);
      } else if (data.type === 'error') {
        onError(data.message || 'Processing failed');
      }
    });
    
    return () => {
      ws.disconnect();
    };
  }, [taskId, docId, onComplete, onError]);
  
  const stepLabels: Record<string, string> = {
    initializing: 'Initializing...',
    reading_file: 'Reading file...',
    chunking: 'Chunking text...',
    embedding: 'Generating embeddings...',
    saving_chunks: 'Saving chunks...',
    indexing: 'Indexing...',
    deduction: 'Extracting facts...',
    patterns: 'Analyzing patterns...',
  };
  
  return (
    <Card className="bg-slate-800/50 border-slate-700">
      <CardContent className="p-6">
        <div className="space-y-4">
          <div className="flex items-center space-x-3">
            <Loader2 className="h-5 w-5 animate-spin text-cyan-400" />
            <div className="flex-1">
              <p className="text-white font-medium">Processing Document</p>
              <p className="text-sm text-slate-400">{stepLabels[currentStep] || 'Processing...'}</p>
            </div>
            <span className="text-sm text-slate-400">{progress}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </CardContent>
    </Card>
  );
};
```

---

### 6. Update Upload Page with Progress

**File**: `src/pages/Upload.tsx`

#### Replace handleUpload function:
```typescript
const handleUpload = async () => {
  if (files.length === 0) {
    toast({
      title: "No files selected",
      description: "Please select files to upload",
      variant: "destructive",
    });
    return;
  }

  setIsLoading(true);
  try {
    // Upload first file (v2.0 currently handles single file)
    const file = files[0];
    const response = await api.uploadDocument(file, {
      provider: selectedProvider,
      enable_deduction: enableDeduction,
      enable_patterns: enablePatterns,
    });
    
    // Store IDs for progress tracking
    setDocId(response.doc_id);
    setTaskId(response.task_id);
    
    toast({
      title: "Upload successful!",
      description: "Document is being processed. You'll be notified when complete.",
    });
    
    // Show progress component
    // Progress component will handle WebSocket and navigation
  } catch (error: any) {
    toast({
      title: "Upload failed",
      description: error.response?.data?.detail || "There was an error processing your file",
      variant: "destructive",
    });
  } finally {
    setIsLoading(false);
  }
};
```

---

### 7. Add Search Feature (Optional)

**File**: `src/pages/Search.tsx` (NEW FILE)

```typescript
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { api } from '@/services/api';
import { useToast } from '@/hooks/use-toast';

export const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const { toast } = useToast();
  
  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setIsSearching(true);
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
    } finally {
      setIsSearching(false);
    }
  };
  
  return (
    <div className="container mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>Search Documents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex space-x-2 mb-4">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter search query..."
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button onClick={handleSearch} disabled={isSearching}>
              Search
            </Button>
          </div>
          
          <div className="space-y-2">
            {results.map((result, idx) => (
              <Card key={idx}>
                <CardContent className="p-4">
                  <p className="text-sm text-slate-400 mb-2">
                    Score: {result.combined_score.toFixed(3)}
                  </p>
                  <p>{result.text}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
```

---

### 8. Update Environment Variables

**File**: `.env` or `.env.local`

```env
VITE_API_URL=http://localhost:8000
```

---

### 9. Update Package Dependencies (if needed)

**File**: `package.json`

No new dependencies required, but ensure:
- `axios` is installed (already present)
- WebSocket support is built into browsers (no library needed)

---

## Migration Checklist

### Phase 1: Core API Updates
- [ ] Update `src/lib/axios.ts` base URL to port 8000
- [ ] Create `src/services/api.ts` with v2.0 API functions
- [ ] Update `src/pages/Upload.tsx` to use new endpoint
- [ ] Test basic upload functionality

### Phase 2: Async Processing
- [ ] Create `src/components/ProcessingProgress.tsx`
- [ ] Integrate WebSocket progress tracking
- [ ] Update upload flow to handle async responses
- [ ] Test progress updates

### Phase 3: Enhanced Features
- [ ] Add provider selection UI (Gemini/OpenAI)
- [ ] Add feature flags UI (deduction, patterns)
- [ ] Create search page (optional)
- [ ] Add document management features (optional)

### Phase 4: Testing & Polish
- [ ] Test all API endpoints
- [ ] Test WebSocket connections
- [ ] Test error handling
- [ ] Update error messages
- [ ] Add loading states

---

## Breaking Changes

1. **API Endpoint**: `/generate` → `/api/v2/generate`
2. **Response Format**: Immediate dashboard → async with `doc_id` and `task_id`
3. **Port Change**: 8001 → 8000 (default)
4. **File Upload**: Single file per request (v2.0 current implementation)

---

## Backward Compatibility

To support both v1.0 and v2.0:

1. Add feature flag:
   ```typescript
   const USE_V2_API = import.meta.env.VITE_USE_V2_API === 'true';
   ```

2. Conditional API calls:
   ```typescript
   const endpoint = USE_V2_API ? '/api/v2/generate' : '/generate';
   ```

---

## Additional Features to Consider

1. **Document List Page**: Show all processed documents
2. **Document Details Page**: View document info, chunks, knowledge graph
3. **Search Integration**: Add search bar to header/navigation
4. **Batch Upload**: Support multiple files (when backend supports it)
5. **Settings Page**: Configure default provider, feature flags

---

## Testing Guide

1. **Test Upload Flow**:
   - Upload a file
   - Verify WebSocket connection
   - Check progress updates
   - Verify dashboard loads after completion

2. **Test Error Handling**:
   - Invalid file types
   - Network errors
   - WebSocket disconnection
   - Backend errors

3. **Test Search** (if implemented):
   - Basic search
   - Empty results
   - Error handling

---

## Notes

- v2.0 backend currently processes files synchronously in the worker, but returns immediately
- WebSocket progress updates are implemented but may need backend enhancements
- Search feature requires documents to be processed first
- Knowledge graph visualization would be a nice addition

---

**Last Updated**: 2025-01-27  
**Version**: 2.0.0

