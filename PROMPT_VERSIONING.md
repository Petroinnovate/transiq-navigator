# Prompt Versioning System

## 🎯 Overview

TransIQ now features a **production-grade prompt versioning system** that decouples AI quality improvements from deployment cycles.

### Key Benefits

| Before | After |
|--------|-------|
| Deploy to test prompts | Change config instantly |
| Risky updates | Safe experiments with A/B testing |
| No visibility | Measurable performance metrics |
| Static AI | Continuously improving AI |

---

## 🏗️ Architecture

```
app/prompts/
├── __init__.py              # Package exports
├── loader.py                # PromptLoader with caching & A/B testing
├── logger.py                # PromptLogger for performance tracking
├── cli.py                   # CLI tool for management
└── dashboard/               # Prompt registry
    ├── 1.0.0.yaml          # Stable version
    └── 1.1.0.yaml          # Experimental version
```

---

## 📝 Prompt File Format

```yaml
version: "1.0.0"
name: "dashboard"
description: "Stable dashboard generation prompt"
created_at: "2026-03-20"
stable: true
fallback_version: null

metadata:
  target_kpi_count: 25
  target_chart_count: 8
  focus: "balanced"

template: |
  Retrieved document content ({num_chunks} section(s) analysed):
  {content}
  
  You are an expert Six Sigma Black Belt...
```

---

## 🚀 Quick Start

### 1. Using Prompt Versioning in Code

```python
from app.processors.dashboard import DashboardGenerator

# Use latest version
generator = DashboardGenerator(prompt_version="latest")

# Use stable version
generator = DashboardGenerator(prompt_version="stable")

# Use specific version
generator = DashboardGenerator(prompt_version="1.0.0")

# Enable A/B testing
generator = DashboardGenerator(use_ab_test=True)

# Generate dashboard
dashboard_data = generator.generate_dashboard(
    text_chunks=chunks,
    file_name="report.pdf",
    doc_id="doc_123",
    user_id="user_456"
)
```

### 2. Using CLI Tools

**List all prompts and versions:**
```bash
python -m app.prompts.cli list
```

**Show prompt details:**
```bash
python -m app.prompts.cli show dashboard --version 1.0.0
```

**View performance stats:**
```bash
# Last 24 hours
python -m app.prompts.cli stats dashboard --hours 24

# Specific version
python -m app.prompts.cli stats dashboard --version 1.1.0 --hours 48
```

**Register A/B test:**
```bash
# Equal distribution (50/50)
python -m app.prompts.cli ab-test dashboard --versions 1.0.0,1.1.0

# Custom weights (70/30)
python -m app.prompts.cli ab-test dashboard --versions 1.0.0,1.1.0 --weights 0.7,0.3
```

---

## 📊 Performance Tracking

Every prompt execution is automatically logged with:

- **Execution metrics**: Latency (ms), token usage, cost
- **Result metrics**: KPI count, chart count, success/failure
- **Context**: Document ID, user ID, prompt version used
- **Metadata**: Custom metrics (file name, content length, etc.)

### Database Schema

```sql
CREATE TABLE prompt_executions (
    id VARCHAR(36) PRIMARY KEY,
    prompt_name VARCHAR(100) NOT NULL,
    prompt_version VARCHAR(50) NOT NULL,
    doc_id VARCHAR(36),
    user_id VARCHAR(36),
    latency_ms INTEGER NOT NULL,
    tokens_used INTEGER,
    cost INTEGER,  -- Cost in cents
    kpi_count INTEGER,
    chart_count INTEGER,
    success INTEGER DEFAULT 1,  -- 1=success, 0=failure
    error_message VARCHAR(500),
    exec_metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_prompt_perf (prompt_name, prompt_version, created_at),
    INDEX idx_prompt_user (prompt_name, user_id)
);
```

---

## 🧪 A/B Testing

### Register Test in Code

```python
from app.prompts import get_loader

loader = get_loader()

# 50/50 split
loader.register_ab_test("dashboard", ["1.0.0", "1.1.0"])

# Custom weights (70% v1.0.0, 30% v1.1.0)
loader.register_ab_test("dashboard", ["1.0.0", "1.1.0"], weights=[0.7, 0.3])
```

### Use A/B Testing

```python
# A/B test will automatically select version
generator = DashboardGenerator(use_ab_test=True)
dashboard = generator.generate_dashboard(chunks, file_name)
```

### Analyze Results

```bash
# Compare performance
python -m app.prompts.cli stats dashboard --version 1.0.0 --hours 24
python -m app.prompts.cli stats dashboard --version 1.1.0 --hours 24
```

---

## 📦 Available Prompt Versions

### dashboard v1.0.0 (Stable)
- **Status**: ✅ Stable
- **Focus**: Balanced KPI extraction
- **Target KPIs**: 25
- **Target Charts**: 8
- **Categories**: Financial, Safety, Operations, Efficiency, Reliability, Supporting
- **Use Case**: General-purpose dashboard generation

### dashboard v1.1.0 (Experimental)
- **Status**: 🚧 Experimental
- **Focus**: Financial and Risk Analysis
- **Target KPIs**: 35 (40% financial, 20% safety/risk)
- **Target Charts**: 10
- **Enhanced**: Deeper financial metrics, risk scoring, compliance tracking
- **Fallback**: v1.0.0
- **Use Case**: Financial reporting, risk assessment, compliance audits

---

## 🔄 Creating New Prompt Versions

### Step 1: Create YAML File

```bash
cd app/prompts/dashboard
cp 1.0.0.yaml 1.2.0.yaml
```

### Step 2: Edit Metadata

```yaml
version: "1.2.0"
name: "dashboard"
description: "Your new optimized prompt"
created_at: "2026-03-25"
stable: false  # Set to true after testing
fallback_version: "1.0.0"  # Fallback to stable version

metadata:
  target_kpi_count: 30
  target_chart_count: 9
  focus: "custom_focus"
```

### Step 3: Update Template

Modify the `template: |` section with your improvements.

### Step 4: Test New Version

```python
generator = DashboardGenerator(prompt_version="1.2.0")
dashboard = generator.generate_dashboard(chunks, file_name)
```

### Step 5: Monitor Performance

```bash
python -m app.prompts.cli stats dashboard --version 1.2.0 --hours 24
```

### Step 6: Promote to Stable

Once tested and validated:
1. Edit `1.2.0.yaml`
2. Change `stable: true`
3. Remove `fallback_version` (or set to null)

---

## 🎨 Customization

### Custom Prompt Categories

Create new prompt directories:

```
app/prompts/
├── dashboard/
│   ├── 1.0.0.yaml
│   └── 1.1.0.yaml
├── summary/           # New prompt type
│   └── 1.0.0.yaml
└── extraction/        # New prompt type
    └── 1.0.0.yaml
```

### Load Custom Prompts

```python
from app.prompts import load_prompt

# Load summary prompt
summary_prompt = load_prompt(
    prompt_name="summary",
    version="1.0.0",
    content=document_text
)

# Use with LLM
response = llm.generate(summary_prompt)
```

---

## 🔍 Debugging

### View Prompt Execution Logs

```python
from app.prompts import get_prompt_logger

logger = get_prompt_logger()
stats = logger.get_performance_stats("dashboard", hours=24)
print(stats)
```

### Check Loaded Prompt

```python
from app.prompts import get_loader

loader = get_loader()
prompt_version = loader.load_prompt("dashboard", "1.0.0")

print(f"Version: {prompt_version.version}")
print(f"Stable: {prompt_version.stable}")
print(f"Template length: {len(prompt_version.template)}")
```

### Clear Cache

```python
from app.prompts import get_loader

loader = get_loader()
loader.clear_cache()
```

---

## 📈 Performance Metrics

### Latency Analysis

```bash
python -m app.prompts.cli stats dashboard --hours 24
```

Output:
```
📈 Summary:
   Total executions: 150
   Success rate: 98.7%

⏱️  Latency:
   Average: 12400 ms
   Median (P50): 11800 ms
   P95: 15200 ms
   Min: 8500 ms
   Max: 18900 ms

📊 KPI Extraction:
   Average count: 28.5
   Min count: 18
   Max count: 42
```

---

## 🚨 Error Handling

### Fallback Mechanism

If a prompt version fails, the system automatically falls back to the specified `fallback_version`:

```python
from app.prompts import get_loader

loader = get_loader()

# Will use fallback if 1.1.0 fails
prompt_version = loader.load_with_fallback("dashboard", "1.1.0")
```

### Manual Fallback

```python
try:
    prompt = load_prompt("dashboard", "1.2.0", content=text)
except Exception:
    # Fallback to stable version
    prompt = load_prompt("dashboard", "stable", content=text)
```

---

## 🔐 Best Practices

1. **Always test new versions** in development before production
2. **Use A/B testing** to compare performance metrics
3. **Set stable=false** for experimental versions
4. **Monitor performance** regularly with CLI tools
5. **Version incrementally** (1.0.0 → 1.1.0 → 1.2.0)
6. **Document changes** in the description field
7. **Keep fallback versions** specified for experimental prompts
8. **Track metadata** (target KPI counts, focus areas)

---

## 🛠️ Integration with Existing Code

The system is **backward compatible**. Existing code will continue to work, using the latest stable version by default:

```python
# Old code (still works)
generator = DashboardGenerator()

# New code (explicit versioning)
generator = DashboardGenerator(prompt_version="1.0.0")
```

---

## 📚 Resources

- **Prompt Registry**: `app/prompts/dashboard/`
- **CLI Tool**: `python -m app.prompts.cli`
- **Loader**: `from app.prompts import load_prompt`
- **Logger**: `from app.prompts import log_prompt_execution`
- **Performance Stats**: `python -m app.prompts.cli stats dashboard`

---

## 🎯 Next Steps

1. **Create your first experimental version** (e.g., v1.2.0)
2. **Run A/B tests** to compare with stable version
3. **Monitor performance metrics** over 24-48 hours
4. **Promote best-performing version** to stable
5. **Iterate and improve** continuously

---

## 💡 Pro Tips

- Use **metadata fields** to document optimization goals
- Track **confidence scores** (how certain is the KPI value)
- Monitor **KPI count trends** (are prompts getting better?)
- Compare **latency** across versions to optimize performance
- Use **weights** in A/B tests to gradually roll out new versions (90/10 → 70/30 → 50/50)

---

**Built with ❤️ for TransIQ - Decoupling AI quality from deployment cycles**
