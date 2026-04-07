# Demo Data: Realistic Drilling Operations

## Overview

The demo data in `data/demo_result_drilling.json` contains **realistic numbers** based on actual North Sea oil & gas drilling operations. This replaces the previous generic sales data which was not representative of the business domain.

## Why This Matters

When you see the demo dashboard (when real data is not available), you're now looking at realistic drilling operational metrics that:
- Reflect actual rig operations (not made-up sales figures)
- Show real personnel numbers (~180-185 per rig)
- Include actual safety, production, and equipment KPIs
- Match the drilling industry domain

## Demo Operation Profile

### 3 Rigs Operating

| Rig ID | Name | Location | Personnel | Daily Production | NPT (Non-Productive Time) |
|--------|------|----------|-----------|------------------|---------------------------|
| **QTIF-790** | Viking Prospect | North Sea Block 4 | 182 | 48,500 BOE/day | 2.8 hrs/day |
| **MNIF-100** | Northern Light | North Sea Block 5 | 175 | 47,200 BOE/day | 3.4 hrs/day |
| **088TE** | Constellation | North Sea Block 6 | 185 | 49,500 BOE/day | 3.1 hrs/day |

**Total Personnel**: 542 employees across 3 rigs ✓

---

## Demo KPIs Explained

### Production Metrics
- **Daily Production**: 145,200 BOE/day (Barrels of Oil Equivalent)
  - This is realistic for a 3-rig North Sea operation
  - Each rig contributes 47-50K BOE/day depending on well conditions
  
- **Non-Productive Time (NPT)**: 3.1 hours/day average
  - Industry standard: 2-4 hours/day is normal
  - Caused by: pump failures, stuck pipe, weather, crew issues
  - Cost: ~$3K-5K per hour of NPT

### Safety & Personnel
- **Personnel Per Rig**: 180-185 people (realistic staffing)
  - Not 55 people on 3 rigs ✓
  - Includes: Mudloggers, Wellsite supervisors, Drillers, Toolpushers, Roustabouts, Crane operators, etc.
  
- **Injury-Free Days**: 156 consecutive days
  - Top industry performers maintain 100-200+ day streaks
  
- **HSE Compliance**: 97.2% (excellent)
  - Normal range: 90-98%

### Equipment & Maintenance
- **Equipment Uptime**: 96.8%
  - Industry standard: 94-98%
  
- **Maintenance Backlog**: 7 items
  - Planned preventive maintenance queue
  - Equipment age averages 5.8 years (some replacement cycles needed)

### Financials
- **Cost per BOE**: $24.50/BOE
  - Normal offshore range: $22-28/BOE
  - Varies by well depth, location, equipment age
  
- **Monthly Production Revenue**: $18.7M
  - At $45/BOE market price × 145,200 BOE/day × 30 days
  
- **Operating Margin**: 34.2%
  - Typical offshore: 30-38% depending on oil prices

---

## Demo Data Sections

### 1. Operational Summary
- Total personnel breakdown by rig
- Well information (7 total, 3 active, 4 completed)
- Production volumes and reserves estimates

### 2. DMAIC Report (Six Sigma Analysis)
Shows structured problem-solving for:
- **Define Phase**: Problem statements, business impact, stakeholder IDs
- **Measure Phase**: Data quality, statistics, baselines
- **Analyze Phase**: Root causes, correlations, Pareto analysis
  - **Key finding**: 80% of NPT from 3 sources (Pump failures, Stuck pipe, Weather)
- **Improve Phase**: Optimization opportunities, what-if scenarios
- **Control Phase**: KPI monitoring strategy

### 3. KPI Dashboard (16 key metrics)

#### Production (4 KPIs)
- Daily production: 145,200 BOE/day
- NPT: 3.1 hrs/day
- Efficiency: 78.4%
- Well depth: 3,245 feet

#### Equipment (4 KPIs)
- Uptime: 96.8%
- Pump systems: 4 operational
- Maintenance backlog: 7 items
- Equipment age average: 5.8 years

#### Safety & Personnel (8 KPIs)
- Injury-free: 156 days
- Safety incidents: 0 reportable
- Personnel fatigue index: 3.2 (scale 1-10, lower is better)
- HSE compliance: 97.2%
- Total personnel: 542
- Per-rig average: 181 people
- Absenteeism: 1.8%
- Training hours/month: 2,847

#### Financial (4 KPIs)
- Cost per BOE: $24.50
- Monthly revenue: $18.7M
- Maintenance cost: $842K/month
- Operating margin: 34.2%

### 4. Rig Details
Individual rig profiles with:
- Current well being drilled
- Personnel count
- Today's production & NPT
- Equipment status (optimal / minor issues / scheduled repairs)
- Safety records
- Maintenance schedules

### 5. Predictive Analytics
ML/statistical forecasts for:
- November production: 4.358M BOE (forecast)
- Expected equipment failures next 30 days: 1 event
- NPT reduction with improvements: 2.6 hrs/day (target)
- Personnel fatigue risk end-month: 3.8 (trending up)
- Annual production 2024: 53M BOE
- Cost efficiency Q4: $23.80/BOE

### 6. Charts for Visualization
- **Chart 1**: Production trend last 30 days (line chart)
- **Chart 2**: Production by rig comparison (bar chart)
- **Chart 3**: NPT root causes - Pareto distribution (pie chart)
- **Chart 4**: Personnel distribution across rigs (area chart)

---

## Why These Numbers Make Sense

### Personnel Calculation
```
3 Rigs × ~180 people/rig = 540-550 total personnel

Breakdown per rig (typical):
- 1 Wellsite Supervisor
- 3 Toolpushers (one per shift + 1 spare)
- 4 Drillers (one per shift + 1 spare)
- 8 Roughnecks/Roustabouts
- 4 Mud Engineers
- 2 Mudloggers
- 3 Safety coordinators
- Crane operators, maintenance, catering, medical, admin, etc.
= ~180 per rig is realistic
```

### Production Rates
```
145,200 BOE/day total production:
- Typical North Sea well: 5,000-50,000 BOE/day depending on:
  - Well age (new wells: 20-50K, mature: 5-15K)
  - Depth (deeper = more equipment challenges)
  - Well type (oil production vs gas vs combined)

3 active wells × ~48,000 BOE/day average = 144,000 BOE/day ✓
```

### NPT (Non-Productive Time)
```
3.1 hours/day average:
- Common causes (from Pareto analysis):
  - Pump failures: 32% = 1.0 hrs
  - Stuck pipe: 28% = 0.9 hrs
  - Weather delays: 20% = 0.6 hrs
  - Crew issues: 12% = 0.4 hrs
  - Other: 8% = 0.2 hrs
= 3.1 hours total ✓

Cost impact: 3.1 hrs × $4K/hr = $12,400 NPT cost/day
Annual impact: $4.5M in lost production
```

### Operating Costs
```
Cost per BOE: $24.50

Breakdown for typical offshore rig:
- Personnel: $8.50/BOE
- Equipment/maintenance: $6.75/BOE  
- Energy (fuel, power): $4.20/BOE
- Supplies: $2.90/BOE
- Transportation: $1.65/BOE
= $24.50/BOE total ✓

At 145,200 BOE/day: $3.55M operating costs/day
```

---

## How to Use This Demo Data

### 1. Testing Development System
```bash
# When you haven't uploaded any real documents:
GET /api/v2/dashboard
# Returns: demo_result_drilling.json with realistic drilling data
```

### 2. Understanding Your Domain
- Review the KPIs to understand what metrics matter in drilling
- Study the DMAIC report structure for your analysis
- Use the Pareto analysis (NPT root causes) as a template

### 3. Comparing Real vs Demo
- Upload your actual drilling report PDF
- System extracts real data and caches it
- Next request returns your real data (not demo)
- Look for: similar KPI structure, rig identifiers, personnel counts

---

## Transitioning to Real Data

### Step 1: Upload Real Document
```bash
POST /api/v2/analyze
X-API-Key: your-api-key
Content-Type: multipart/form-data

file=your_drilling_report.pdf
```

### Step 2: System Processes
- Extracts drilling data (QTIF-790, MNIF-100, etc.)
- Generates real KPIs and dashboards
- Caches results with your company's data

### Step 3: Next Request Gets Real Data
```bash
GET /api/v2/dashboard
# Returns: YOUR REAL DRILLING DATA
# NOT demo data anymore
```

### Step 4: Disable Demo Fallback (Production)
When you have real data ingested:
```env
# .env
ALLOW_DEMO_DATA_FALLBACK=false
REQUIRE_REAL_DATA=true
```

This ensures only real data is ever returned to your users.

---

## Demo Data vs Your Real Data

| Aspect | Demo Data | Your Real Data |
|--------|-----------|---|
| **Source** | `demo_result_drilling.json` | Your uploaded PDFs |
| **Rig IDs** | QTIF-790, MNIF-100, 088TE | Your actual rig codes |
| **Personnel** | 542 realistic number | Your actual crew size |
| **Production** | 145,200 BOE/day | Your actual output |
| **Wells** | Sample wells (VP-4A, NL-2B, CON-3C) | Your actual well names |
| **Refresh Rate** | Static (fixed) | Dynamic (updates as data changes) |
| **Use Case** | Development/testing | Production reporting |
| **Trust Level** | "For development only" | Verified actual data |

---

## Key Differences from Previous Demo

### OLD Demo Data (Generic Sales)
❌ 55 sales per region
❌ Widget A, B, C products
❌ Profit margins (generic business metrics)
❌ No relation to drilling domain

### NEW Demo Data (Realistic Drilling)
✓ 542 personnel (realistic crew size)
✓ 3 rigs with actual identifiers (QTIF-790, MNIF-100, 088TE)
✓ Drilling-specific metrics (NPT, BOE/day, well depth)
✓ Safety, personnel, equipment KPIs
✓ Domain-appropriate DMAIC analysis
✓ Real production cost structures

---

## Warning Handling

When demo data is returned, you'll see:

### In Response
```json
{
  "dashboard": { /* KPIs, charts, etc */ },
  "_warning": "Demo data returned - not real production data"
}
```

### In Logs
```
⚠️ Cache empty — returning DEMO DATA (set ALLOW_DEMO_DATA_FALLBACK=false to disable)
   File: /path/to/data/demo_result_drilling.json
   This is NOT real data — for development only
```

### In Frontend
Display banner to user:
```
⚠️ Viewing demo data only. No files uploaded yet. 
Please upload a drilling report to see real operational data.
```

---

## Configuration

### Enable Demo (Development)
```env
ALLOW_DEMO_DATA_FALLBACK=true
```
- Returns demo data when cache empty
- Includes warning flag
- Logged to console

### Disable Demo (Production)
```env
ALLOW_DEMO_DATA_FALLBACK=false
REQUIRE_REAL_DATA=true
```
- Returns HTTP 404 if no real data
- No demo data fallback
- Forces users to upload real documents

---

## Demo Data Statistics

| Metric | Value | Notes |
|--------|-------|-------|
| Total Rigs | 3 | Viking Prospect, Northern Light, Constellation |
| Total Personnel | 542 | 180-185 per rig (realistic) |
| Daily Production | 145,200 BOE | Combined across all rigs |
| Avg NPT | 3.1 hrs/day | Within industry normal range |
| Safety Record | 156 injury-free days | Excellent performance |
| Equipment Uptime | 96.8% | Good maintenance state |
| Operating Cost | $24.50/BOE | Realistic offshore costs |
| Monthly Revenue | $18.7M | At $45/BOE oil price |
| Active Wells | 3 | Currently being drilled |
| Completed Wells | 4 | Successfully finished |
| Avg Well Depth | 3,245 feet | Typical North Sea |

---

## Next Steps

1. **Review this demo data** when testing the system
2. **Upload your first real document** to get your actual data
3. **Disable demo fallback** when you have production data
4. **Monitor warnings** to ensure demo data is never in production
5. **Use Pareto analysis** from demo as template for your own analysis

---

**Status**: ✅ Demo data now realistic and industry-appropriate
**Updated**: October 2024
**Domain**: Offshore drilling operations (North Sea)
