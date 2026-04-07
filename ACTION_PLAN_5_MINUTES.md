# Action Plan: Fix Fake Data & Authentication Issues

## What You Asked

> "I see fake drilling data (QTIF-790, MNIF-100). Report data is fake. KPI's are fake. There is no authentication. Why?"

## What I Found

✅ **Authentication IS implemented** (API Key + JWT)  
⚠️ **Demo fallback IS enabled by default** (returns fake data when cache empty)  
❌ **No configuration to control it** (have NOW fixed this)

---

## What I Fixed (Today)

### 1. Code Changes
- Added configuration: `ALLOW_DEMO_DATA_FALLBACK` (true/false)
- Added configuration: `REQUIRE_REAL_DATA` (true/false)
- Modified demo fallback to respect config
- Added `_warning` field to demo responses
- Enhanced logging for transparency

### 2. Documentation
- `SECURITY_AND_AUTHENTICATION.md` - Complete security guide
- `QUICK_FIX_FAKE_DATA_AUTH.md` - Quick reference
- `ANSWER_FAKE_DATA_NO_AUTH.md` - Direct answers
- `.env.example` - Updated with new settings

---

## Your 5-Minute Action Plan

### Step 1: Generate API Keys
```bash
python -c "import secrets; print('API_KEY=sk-' + secrets.token_hex(32))"
```

Copy the output. Example output:
```
API_KEY=sk-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### Step 2: Update `.env` File

Open `.env` and add/update:
```env
# Authentication
API_KEY=sk-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

# CRITICAL: Disable demo data fallback
ALLOW_DEMO_DATA_FALLBACK=false

# Optional: Strict mode (require real data)
REQUIRE_REAL_DATA=true

# Production settings
DEBUG=false
```

### Step 3: Restart Server
```bash
# Stop current server (Ctrl+C)

# Restart:
python -m uvicorn app.main:app --reload
```

### Step 4: Verify It Works
```bash
# Check logs for security confirmation:
# Should see: 🔐 API Key authentication enabled

# Test without auth (should FAIL with 401):
curl http://localhost:8000/api/v2/generate

# Test with auth (should WORK with 200):
curl -H "X-API-Key: sk-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
     http://localhost:8000/api/v2/generate
```

---

## What Each Setting Does

### ALLOW_DEMO_DATA_FALLBACK

**Default**: `true` (development mode)

| Value | Behavior |
|-------|----------|
| `true` | Cache empty → return demo_result.json (with `_warning` field) |
| `false` | Cache empty → return HTTP 404 error |

**Recommendation**:
- Development: `true` (allows testing without uploading)
- Production: `false` (prevent fake data)

### REQUIRE_REAL_DATA

**Default**: `false` (warning mode)

| Value | Behavior |
|-------|----------|
| `false` | Allow demo data when cache empty (with warning) |
| `true` | Reject requests without real data (strict mode) |

**Recommendation**:
- Development: `false` (flexible testing)
- Production: `true` (strict compliance)

### API_KEY

**Default**: None (no authentication)

| Value | Behavior |
|-------|----------|
| Not set | Authentication disabled (INSECURE) |
| `sk-xxxxx` | All `/api/v2/*` requests require this key |

**Recommendation**:
- Always set in `.env`
- Use strong random value (32+ chars)
- Update regularly

---

## Before & After Comparison

### Before (Current State)
```
User → Request without API key
        ↓
Server → No authentication check
         ↓
         Cache empty? Yes
         ↓
         Return demo_result.json
         ↓
Response → FAKE drilling data (QTIF-790, MNIF-100)
           NO WARNING about fake data
           USER DOESN'T KNOW IT'S FAKE
```

### After (With Your Changes)
```
User → Request WITH X-API-Key header
        ↓
Server → Validate API key ✓
         ↓
         Cache empty? Yes
         ↓
         ALLOW_DEMO_DATA_FALLBACK=false?
         ↓ YES
         Return HTTP 404 "No data available"
         ↓
Response → ERROR: No dashboard data available

OR (if demo allowed)

         ALLOW_DEMO_DATA_FALLBACK=true?
         ↓ YES
         Return demo data WITH _warning field
         ↓
Response → FAKE data (marked with warning)
           FRONTEND SHOWS WARNING TO USER
```

---

## How It Works After Setup

### Authentication
Every request to `/api/v2/*` must include:
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v2/generate
```

Without it:
```json
{
  "detail": "Invalid or missing API key"
}
```

### Demo Data Control

**Upload real document**:
```bash
curl -X POST http://localhost:8000/api/v2/analyze \
  -H "X-API-Key: your-api-key" \
  -F "file=@my_report.pdf"
```
→ Real data is cached, returned with confidence

**No document, demo enabled**:
```bash
curl http://localhost:8000/api/v2/dashboard \
  -H "X-API-Key: your-api-key"
```
→ Returns demo_result.json with `_warning` field:
```json
{
  "title": "...",
  "kpis": [...],
  "_warning": "Demo data returned - not real production data"
}
```

**No document, demo disabled**:
```bash
curl http://localhost:8000/api/v2/dashboard \
  -H "X-API-Key: your-api-key"
```
→ Returns HTTP 404:
```json
{
  "detail": "No dashboard data available. Please upload a file first."
}
```

---

## Configuration Templates

### Development Setup
```env
DEBUG=true
API_KEY=dev-simple-key
ALLOW_DEMO_DATA_FALLBACK=true
REQUIRE_REAL_DATA=false
FRONTEND_URL=http://localhost:5173
```

### Staging Setup
```env
DEBUG=false
API_KEY=sk-staging-key-secure-random-value
API_KEY_2=sk-staging-backup-key
ALLOW_DEMO_DATA_FALLBACK=false
REQUIRE_REAL_DATA=true
FRONTEND_URL=https://staging.yourdomain.com
```

### Production Setup
```env
DEBUG=false
API_KEY=sk-prod-key-very-secure-random-value
API_KEY_2=sk-prod-backup-very-secure-random
API_KEY_3=sk-prod-third-very-secure-random
RATE_LIMIT_PER_MINUTE=100
ALLOW_DEMO_DATA_FALLBACK=false
REQUIRE_REAL_DATA=true
FRONTEND_URL=https://yourdomain.com
```

---

## Testing Your Setup

### Test 1: Authentication Works
```bash
# Without key - should FAIL
$ curl http://localhost:8000/api/v2/generate
{"detail": "Invalid or missing API key"}  ✓

# With key - should WORK
$ curl -H "X-API-Key: sk-..." http://localhost:8000/api/v2/generate
{...successful response...}  ✓
```

### Test 2: Demo Data Disabled
```bash
# Configure in .env:
ALLOW_DEMO_DATA_FALLBACK=false

# Request with no real data - should FAIL with 404
$ curl -H "X-API-Key: sk-..." http://localhost:8000/api/v2/dashboard
{"detail": "No dashboard data available"}  ✓
```

### Test 3: Real Data Works
```bash
# Upload a real document
$ curl -X POST http://localhost:8000/api/v2/analyze \
  -H "X-API-Key: sk-..." \
  -F "file=@report.pdf"
{...real data with results...}  ✓
```

---

## FAQ During Setup

**Q: Can I use a simple API key like "dev123"?**  
A: For dev yes. For production, use 32+ random chars: `secrets.token_hex(32)`

**Q: Will authentication break my frontend?**  
A: If your frontend doesn't send X-API-Key header, yes. You'll need to update it.

**Q: What if I want to keep demo data in production?**  
A: Set `ALLOW_DEMO_DATA_FALLBACK=true`, but add warning check in your UI.

**Q: Can I have different keys for different users?**  
A: Currently supports 3 API keys. For per-user keys, needs JWT implementation.

**Q: How often to rotate API keys?**  
A: Every 90 days, or immediately if compromised.

**Q: What if I forget my API key?**  
A: Regenerate it: `python -c "import secrets; print(secrets.token_hex(32))"` and update .env

---

## Monitoring After Setup

### Check Logs
```bash
# Watch for security events
tail -f logs/app.log | grep -i "auth\|api key\|demo"

# Should see:
# ✓ "🔐 API Key authentication enabled"
# × "⚠️ Cache empty — returning DEMO DATA" (if demo enabled)
```

### Verify Authentication
```bash
# Count successful auth:
grep "API key.*valid" logs/app.log | wc -l

# Count failed auth:
grep "Invalid API key" logs/app.log | wc -l

# Should see more successful than failed
```

### Track Demo Data Usage
```bash
# If demo is ever served in production, find it:
grep "DEMO DATA" logs/app.log
# Result: empty if ALLOW_DEMO_DATA_FALLBACK=false ✓
```

---

## Complete Checklist

### Immediate (Now - 5 minutes)
- [ ] Generate API key
- [ ] Update API_KEY in .env
- [ ] Set ALLOW_DEMO_DATA_FALLBACK=false
- [ ] Restart server
- [ ] Test with curl

### Today
- [ ] Verify logs show authentication working
- [ ] Check that demo data returns warning (if enabled)
- [ ] Update frontend to send X-API-Key header
- [ ] Test end-to-end with frontend

### This Week
- [ ] Generate backup API_KEY_2 and API_KEY_3
- [ ] Review SECURITY_AND_AUTHENTICATION.md fully
- [ ] Plan API key rotation schedule
- [ ] Update deployment documentation

### Before Production
- [ ] Set all 3 API key slots with different values
- [ ] Enable REQUIRE_REAL_DATA=true
- [ ] Disable demo fallback completely
- [ ] Enable HTTPS only
- [ ] Set DEBUG=false
- [ ] Configure rate limiting
- [ ] Set up monitoring/alerting
- [ ] Document your security setup

---

## Next Steps

1. **Right Now** (5 min):
   - Generate API key
   - Update .env
   - Restart server
   - Test with curl

2. **Later Today** (30 min):
   - Update frontend to send API key
   - Test end-to-end
   - Review documentation

3. **This Week** (2 hours):
   - Implement key rotation
   - Set up monitoring
   - Test failure scenarios

---

## Support Documents

- **Complete Guide**: `SECURITY_AND_AUTHENTICATION.md`
- **Quick Reference**: `QUICK_FIX_FAKE_DATA_AUTH.md`
- **Direct Answer**: `ANSWER_FAKE_DATA_NO_AUTH.md`
- **Config Template**: `.env.example`

---

## Summary

**Issue**: Fake data + no auth  
**Cause**: Demo fallback enabled, API_KEY not set  
**Fix**: Set API_KEY + set ALLOW_DEMO_DATA_FALLBACK=false  
**Time**: 5 minutes  
**Impact**: Secure, no more fake data visible  

**Status**: ✅ Ready to implement
