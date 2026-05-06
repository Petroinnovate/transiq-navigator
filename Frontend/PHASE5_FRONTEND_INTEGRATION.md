# Phase 5: EntityIntelligenceTab Integration Guide

## Overview
This guide shows how to integrate `EntityIntelligenceTab.tsx` into your existing TransIQ dashboard.

---

## STEP 1: Install Dependency

```bash
npm install vis-network vis-data
```

You may also need these for TypeScript support:
```bash
npm install --save-dev @types/node
```

---

## STEP 2: Update Imports in Dashboard.tsx

**File**: `src/pages/Dashboard.tsx`

Add this import at the top with your other component imports:

```typescript
// Existing imports
import { DashboardRenderer } from '@/components/DashboardRenderer'
// ... other imports ...

// Add this new import for Phase 5
import EntityIntelligenceTab from '@/components/intelligence/EntityIntelligenceTab'
```

---

## STEP 3: Add EntityIntelligenceTab to DashboardRenderer

**File**: `src/components/DashboardRenderer.tsx`

In the component's main render section, add a new section after the **DMAIC Compiler Panel** or in the **Visualizations & Analytics** section.

### Option A: Insert as New Section (Recommended)

Find this section in DashboardRenderer:

```typescript
{/* Six Sigma Analysis Section */}
<SixSigmaSection data={data.sixSigma} />
```

**Add BEFORE it:**

```typescript
{/* Phase 5: Intelligence Engine Integration */}
{data.reportId && (
  <div className="my-6">
    <EntityIntelligenceTab 
      reportId={data.reportId} 
      primaryEntityId={data.meta?.documentId || data.reportId}
    />
  </div>
)}

{/* Six Sigma Analysis Section */}
<SixSigmaSection data={data.sixSigma} />
```

### Option B: Add as Third Tab in Visualizations Section

If you want it as a tab alongside "Charts" and "Predictive", modify the **Visualizations & Analytics** section:

```typescript
{/* Visualizations & Analytics */}
<Card className="my-6 border-primary/30">
  <CardHeader className="pb-3 bg-primary/5">
    <CardTitle className="flex items-center gap-2">
      <BarChart3 className="h-5 w-5 text-primary" />
      Visualizations & Analytics
    </CardTitle>
  </CardHeader>
  <CardContent className="pt-6">
    <Tabs defaultValue="charts" className="w-full">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="charts">Charts</TabsTrigger>
        <TabsTrigger value="predictive">Predictive</TabsTrigger>
        <TabsTrigger value="intelligence">Entity Intelligence</TabsTrigger>  {/* NEW */}
      </TabsList>

      {/* Existing Charts Tab */}
      <TabsContent value="charts">
        {renderChartsSection()}
      </TabsContent>

      {/* Existing Predictive Tab */}
      <TabsContent value="predictive">
        {renderPredictiveSection()}
      </TabsContent>

      {/* NEW Entity Intelligence Tab */}
      <TabsContent value="intelligence" className="mt-4">
        <EntityIntelligenceTab 
          reportId={data.reportId}
          primaryEntityId={data.meta?.documentId || data.reportId}
        />
      </TabsContent>
    </Tabs>
  </CardContent>
</Card>
```

---

## STEP 4: Update DashboardResponse Type

**File**: `src/types/dashboard.ts`

Make sure your `DashboardResponse` interface has these fields (if not already present):

```typescript
export interface DashboardResponse {
  // ... existing fields ...
  reportId?: string  // Needed for EntityIntelligenceTab
  meta?: MetaInfo & { documentId?: string }
  // ... rest of fields ...
}
```

---

## STEP 5: Configure API Endpoints

**Verify**: `src/api/dashboardApi.ts` has the axios instance properly configured

The component expects these endpoints to exist (they are already deployed on your backend):

```
GET /api/v2/intelligence/graph-network/{entityId}
GET /api/v2/intelligence/cross-engine-analysis/{entityId}
GET /api/v2/intelligence/unified-recommendations/{entityId}
```

No changes needed here - just verify your axios is properly configured with the backend URL.

---

## STEP 6: Add API Queries (Optional but Recommended)

**File**: `src/api/dashboardApi.ts`

Add these helper functions for consistency with your existing patterns:

```typescript
import { 
  IntelligenceNetworkVisualization, 
  CrossEngineAnalysis 
} from '@/types/intelligence'

// Entity Intelligence queries
export const intelligenceQueries = {
  network: (entityId: string) => ({
    queryKey: ['intelligence', 'network', entityId],
    queryFn: async () => {
      const response = await axios.get<IntelligenceNetworkVisualization>(
        `/api/v2/intelligence/graph-network/${entityId}`
      )
      return response.data
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  }),
  
  analysis: (entityId: string) => ({
    queryKey: ['intelligence', 'analysis', entityId],
    queryFn: async () => {
      const response = await axios.get<CrossEngineAnalysis>(
        `/api/v2/intelligence/cross-engine-analysis/${entityId}`
      )
      return response.data
    },
    staleTime: 10 * 60 * 1000,
  }),

  recommendations: (entityId: string) => ({
    queryKey: ['intelligence', 'recommendations', entityId],
    queryFn: async () => {
      const response = await axios.get(
        `/api/v2/intelligence/unified-recommendations/${entityId}`
      )
      return response.data
    },
    staleTime: 10 * 60 * 1000,
  }),
}
```

Then use in EntityIntelligenceTab if you want to replace the inline queries:

```typescript
const { data: networkData, isLoading } = useQuery(
  intelligenceQueries.network(primaryEntityId)
)
```

---

## STEP 7: Test the Integration

### In Development:

1. **Start Frontend**:
   ```bash
   npm run dev
   ```

2. **Start Backend** (if not already running):
   ```bash
   python -m uvicorn app.main:app --port 8000
   ```

3. **Upload Test Document**:
   - Go to Upload page
   - Upload your 800-page DPR or test document
   - ProcessLets process

4. **View Dashboard**:
   - Go to Dashboard page
   - Scroll to new **Entity Intelligence** section/tab
   - You should see the entity network graph

### Expected Behavior:

- **Graph loads**: Interactive network visualization with nodes and edges
- **Click entity**: Side panel shows details and cross-engine analysis
- **Filter works**: Domain and confidence filters update graph instantly
- **Export works**: Can download entity data as JSON

---

## STEP 8: Troubleshooting

### Issue: "vis-network is not defined"
**Solution**: Make sure package is installed:
```bash
npm install vis-network vis-data
```

### Issue: Component not rendering
**Solution**: Check browser console for errors. Verify:
1. Backend is running and accessible at `localhost:8000`
2. API endpoints are responding (test at `/docs`)
3. reportId is being passed correctly

### Issue: "Cannot read property 'nodes' of undefined"
**Solution**: Backend query might be failing. Check:
1. Network tab in browser DevTools
2. Look for failed requests to `/api/v2/intelligence/*`
3. Verify backend is returning data in correct format

### Issue: Graph is blank
**Solution**: 
1. Check if entity data exists (should have nodes)
2. Verify vis-network CSS is loaded
3. Clear browser cache and reload

---

## STEP 9: Styling Adjustments (If Needed)

The component uses Tailwind classes that should match your theme. If colors don't match:

**File**: `src/components/intelligence/EntityIntelligenceTab.tsx`

Update color classes:

```typescript
// Around line 300 - Update these color values
className="p-3 bg-blue-50 rounded-lg border border-blue-200"    // Financial
className="p-3 bg-green-50 rounded-lg border border-green-200"  // ESG
className="p-3 bg-amber-50 rounded-lg border border-amber-200"  // Drilling
```

Change to match your brand colors if needed.

---

## STEP 10: Performance Optimization

For large datasets (your 800-page DPR + 200 rigs), consider:

### 1. Lazy Load Component
```typescript
const EntityIntelligenceTab = lazy(() => 
  import('@/components/intelligence/EntityIntelligenceTab')
)
```

### 2. Add Virtual Scrolling for Entity List
If you have 500+ entities, add react-window:
```bash
npm install react-window
```

### 3. Pagination for Large Networks
Add pagination to entity list:
```typescript
const [page, setPage] = useState(0)
const itemsPerPage = 20
const paginatedNodes = networkData.nodes.slice(
  page * itemsPerPage,
  (page + 1) * itemsPerPage
)
```

---

## FINAL CHECKLIST

- [ ] vis-network installed
- [ ] EntityIntelligenceTab.tsx created in `src/components/intelligence/`
- [ ] intelligence.ts types file created in `src/types/`
- [ ] EntityIntelligenceTab imported in Dashboard.tsx
- [ ] Component added to DashboardRenderer
- [ ] Backend is running and accessible
- [ ] Test document uploaded
- [ ] Graph visualization displays
- [ ] Click entity shows details
- [ ] Filters work correctly

---

## NEXT STEPS

1. **Test with real data**: Upload your 800-page DPR
2. **Monitor performance**: Watch for slow renders with 200+ entities
3. **Gather feedback**: See how users interact with the graph
4. **Iterate**: Adjust colors, filters, layout based on needs
5. **Deploy**: Push to production when satisfied

---

## Support

If you encounter issues:

1. Check browser console for errors
2. Verify backend endpoints in Swagger: http://localhost:8000/docs
3. Check network requests in DevTools ("Network" tab)
4. Refer to vis-network docs: https://visjs.github.io/vis-network/
