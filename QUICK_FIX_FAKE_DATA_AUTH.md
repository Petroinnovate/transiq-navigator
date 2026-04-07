# Quick Guide: Fake Data & Authentication Issues

## The Two Concerns

### 1. "Why am I seeing fake drilling data (QTIF-790, MNIF-100)?"

**Root Cause**: System falls back to demo_result.json when cache is empty

**Before**: No warning, just returns fake data  
**After**: Returns data with `_warning` field

**FastAPI Response**:
```json
{
  "title": "Drilling Operations Report",
  "kpis": [...],
  "_warning": "Demo data returned - not real production data"
}
```

**Solution**: Disable demo fallback
```env
# In .env file
ALLOW_DEMO_DATA_FALLBACK=false
```

**Result**: Without real data, returns HTTP 404:
```
404 No dashboard data available. Please upload a file first.
```

---

### 2. "Why is there no authentication visible?"

**Answer**: Authentication IS there, but it's not always obvious

#### API Key Authentication (Required for `/api/v2/*`)

**Without API Key** ❌:
```bash
curl http://localhost:8000/api/v2/generate
# Response: 401 Invalid or missing API key
```

**With API Key** ✅:
```bash
curl -H "X-API-Key: your-key" http://localhost:8000/api/v2/generate
# Response: 200 OK with results
```

#### Where to Add API Key

**In `.env`**:
```env
API_KEY=my-secure-api-key
API_KEY_2=backup-key
API_KEY_3=third-key
```

**In Code**:
```python
from app.config.settings import settings

api_keys = [
    settings.API_KEY,
    settings.API_KEY_2,
    settings.API_KEY_3
]
valid_keys = [k for k in api_keys if k is not None]
# Each request must include one of these in X-API-Key header
```

---

## Quick Fixes

### Issue #1: Seeing Fake Data

#### Quick Fix (1 minute)
```env
# .env
ALLOW_DEMO_DATA_FALLBACK=false
```

#### Check Logs
```bash
# Should see:
grep "DEMO DATA" logs/app.log
# Or:
grep "warning" logs/app.log | grep -i demo
```

#### Verify Fix Works
```bash
# Should now return 404 instead of fake data
curl http://localhost:8000/api/v2/dashboard
# Response: 404 No dashboard data available
```

---

### Issue #2: No Visible Authentication

#### Quick Fix (2 minutes)

**Step 1**: Add API key to `.env`
```env
API_KEY=sk-prod-key-1234567890abcdef
```

**Step 2**: Restart server
```bash
# Kill and restart FastAPI
# Ctrl+C in terminal, then:
python -m uvicorn app.main:app --reload
```

**Step 3**: Check logs for security confirmation
```bash
# Should see:
tail -f logs/app.log | grep "🔐"
# Output: 🔐 API Key authentication enabled (1 valid keys)
```

**Step 4**: Test authentication
```bash
# Without key - should fail
curl http://localhost:8000/api/v2/generate
# Response: 401

# With key - should work
curl -H "X-API-Key: sk-prod-key-1234567890abcdef" \
     http://localhost:8000/api/v2/generate
# Response: 200 OK
```

---

## Configuration Templates

### Development (Demo Allowed)
```env
# .env
API_KEY=dev-key-simple
ALLOW_DEMO_DATA_FALLBACK=true
DEBUG=true
FRONTEND_URL=http://localhost:5173
```
- ✅ Use demo data when testing
- ✅ See errors clearly
- ✅ No auth on some endpoints

### Staging (Real Data)
```env
# .env
API_KEY=staging-key-abc123def456
ALLOW_DEMO_DATA_FALLBACK=false
DEBUG=true
FRONTEND_URL=https://staging.yourdomain.com
```
- ❌ No demo data
- ✅ Real data from uploads
- ✅ Full authentication
- ✅ See errors clearly

### Production (Strict)
```env
# .env
API_KEY=sk-prod-xxxxx
API_KEY_2=sk-prod-backup-xxxxx
API_KEY_3=sk-prod-third-xxxxx
ALLOW_DEMO_DATA_FALLBACK=false
REQUIRE_REAL_DATA=true
DEBUG=false
FRONTEND_URL=https://yourdomain.com
```
- ❌ NO demo data
- ✅ Require real uploads
- ✅ Multiple API keys
- ✅ Strict error handling
- ❌ Hide implementation details

---

## Verification Checklist

### Is Authentication Working?

- [ ] Check `.env` has `API_KEY` set (not empty)
- [ ] Check logs show: `🔐 API Key authentication enabled`
- [ ] Test without key returns 401
- [ ] Test with key returns 200

### Is Demo Data Disabled?

- [ ] Check `.env` has `ALLOW_DEMO_DATA_FALLBACK=false`
- [ ] Check logs show: `❌ Cache empty and demo data disabled`
- [ ] Test without real data returns 404
- [ ] Test with real data returns 200

### Is System Secure?

- [ ] `DEBUG=false` (production mode)
- [ ] `API_KEY` is strong (min 32 chars recommended)
- [ ] `FRONTEND_URL` is set to actual domain
- [ ] `ALLOW_DEMO_DATA_FALLBACK=false` (production)
- [ ] Database has proper authentication
- [ ] Redis has password set
- [ ] HTTPS is enabled

---

## Common Questions

**Q: Is my data currently visible without authentication?**  
A: Only if you haven't set an API_KEY. Set one now: `API_KEY=your-secure-key`

**Q: Can someone access my fake drilling data without permission?**  
A: Currently yes, if auth isn't set. Fix: Set API_KEY and test with header.

**Q: How do I generate a secure API key?**  
A: `python -c "import secrets; print('sk-' + secrets.token_hex(32))"`

**Q: Will enabling authentication break my frontend?**  
A: Maybe. Frontend must add `X-API-Key` header to all `/api/v2/*` requests.

**Q: What if I have multiple environments (dev, staging, prod)?**  
A: Use separate `.env` files:
```bash
.env             # Current (dev)
.env.staging     # Staging config
.env.production  # Production config
```

**Q: How often should I rotate API keys?**  
A: Every 90 days, or immediately if compromised.

**Q: What's the difference between fake data and real data?**  
A: Fake = from demo_result.json (canned example)  
Real = from documents users upload

---

## Logs to Watch

### Good Signs ✅
```
🔐 API Key authentication enabled (3 valid keys)
⏱️  Rate limit: 60 requests/minute per key
[INFO] Cache empty — returning DEMO DATA (set ALLOW_DEMO_DATA_FALLBACK=false to disable)
```

### Warning Signs ⚠️
```
⚠️  No API keys configured - authentication disabled (INSECURE!)
⚠️  Cache empty — returning DEMO DATA
[ERROR] Rate limit exceeded for API key
[ERROR] Invalid or missing API key
```

### Dangerous Signs 🚨
```
⚠️  No API keys configured - authentication disabled (INSECURE!)
DEBUG=true in production mode
FRONTEND_URL = "*" (allows any origin)
ALLOW_DEMO_DATA_FALLBACK=true in production
```

---

## Next Steps

1. **Immediate** (Do now):
   - [ ] Add `API_KEY` to `.env`
   - [ ] Set `ALLOW_DEMO_DATA_FALLBACK=false`
   - [ ] Restart server
   - [ ] Test with curl

2. **Short-term** (This week):
   - [ ] Update frontend to send X-API-Key header
   - [ ] Test in staging with real auth
   - [ ] Review all security settings

3. **Long-term** (Before production):
   - [ ] Generate strong API keys
   - [ ] Enable HTTPS only
   - [ ] Configure database auth
   - [ ] Set up monitoring/alerting
   - [ ] Test failover scenarios

---

## Files to Review

- `.env.example` - Template with all settings
- `app/config/settings.py` - Where settings are loaded
- `app/middleware/auth.py` - Where API Key validation happens
- `app/main.py` - Where CORS is configured
- `llm.py` - Where demo data fallback happens
- `SECURITY_AND_AUTHENTICATION.md` - Complete security guide

---

**Status**: ✅ Authentication is implemented  
**Issue**: ⚠️ Demo data fallback (now configurable)  
**Action**: Set `API_KEY` and `ALLOW_DEMO_DATA_FALLBACK=false` in `.env`
