# 🔐 Security Implementation Guide

## 🔴 Critical Security Fix Applied

TransIQ now has **production-grade security** with API key authentication and rate limiting.

---

## What Was Fixed

### **Before (INSECURE)** ❌
```python
allow_origins=["*"]  # Anyone can call your API
# No authentication
# Unlimited requests
```

**Risks**:
- ✗ Public access to paid LLM API
- ✗ Gemini quota drainage attacks
- ✗ Unauthorized data access
- ✗ No usage tracking

---

### **After (SECURE)** ✅
```python
allow_origins=["http://localhost:5173"]  # Only your frontend
# X-API-Key header required
# 60 requests/minute rate limit
```

**Protection**:
- ✓ CORS restricted to your domain
- ✓ API key authentication on all endpoints
- ✓ Rate limiting prevents abuse
- ✓ Request logging for monitoring

---

## 🚀 Quick Start

### 1. Generate Secure API Keys

```bash
# Generate a secure random API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Example output:
# xK8Qp3mN9vR2tY6wZ4aB1cD5eF7gH0iJ8kL2mN4oP6qR8sT0
```

### 2. Update `.env` File

```bash
# Copy example and edit
cp .env.example .env
nano .env
```

**Add these critical settings**:
```bash
# Security (REQUIRED for production)
API_KEY=xK8Qp3mN9vR2tY6wZ4aB1cD5eF7gH0iJ8kL2mN4oP6qR8sT0
API_KEY_2=backup-key-here-optional
FRONTEND_URL=http://localhost:5173  # Change to https://yourdomain.com in production

# Your existing Gemini keys
GEMINI_API_KEY=your-gemini-key-here
```

### 3. Restart Backend

```bash
# Kill old process
Get-Process -Name python | Stop-Process -Force

# Start with new security
cd TransIQ-backend-master
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**You should see**:
```
🔒 CORS restricted to: ['http://localhost:5173']
🔐 API Key authentication enabled (1 valid keys)
⏱️  Rate limit: 60 requests/minute per key
```

---

## 📡 Frontend Integration

### Update Your Frontend (React/TypeScript)

```typescript
// src/api/client.ts
import axios from 'axios';

const API_KEY = import.meta.env.VITE_API_KEY; // Store in .env.local

export const apiClient = axios.create({
  baseURL: 'http://localhost:8001/api/v2',
  headers: {
    'X-API-Key': API_KEY,
  },
});

// Usage
const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await apiClient.post('/generate', formData);
  return response.data;
};
```

### Frontend `.env.local`

```bash
# TransIQ-frontend/.env.local
VITE_API_KEY=xK8Qp3mN9vR2tY6wZ4aB1cD5eF7gH0iJ8kL2mN4oP6qR8sT0
VITE_API_BASE_URL=http://localhost:8001
```

---

## 🧪 Testing

### 1. Test Without API Key (Should Fail)

```bash
curl http://localhost:8001/api/v2/health
```

**Expected Response** (401):
```json
{
  "error": "Unauthorized",
  "message": "Missing API key. Include 'X-API-Key' header in your request.",
  "hint": "Example: curl -H 'X-API-Key: your-key-here' http://..."
}
```

---

### 2. Test With Valid API Key (Should Work)

```bash
curl -H "X-API-Key: xK8Qp3mN9vR2tY6wZ4aB1cD5eF7gH0iJ8kL2mN4oP6qR8sT0" \
  http://localhost:8001/api/v2/health
```

**Expected Response** (200):
```json
{
  "status": "ok",
  "services": {
    "redis": "ok",
    "qdrant": "ok",
    "database": "ok",
    "llm": "ok"
  }
}
```

---

### 3. Test With Invalid API Key (Should Fail)

```bash
curl -H "X-API-Key: wrong-key" \
  http://localhost:8001/api/v2/health
```

**Expected Response** (401):
```json
{
  "error": "Unauthorized",
  "message": "Invalid API key"
}
```

---

### 4. Test Rate Limiting (Spam Requests)

```bash
# Send 70 requests rapidly (limit is 60/min)
for i in {1..70}; do
  curl -s -H "X-API-Key: your-key" http://localhost:8001/api/v2/health > /dev/null
  echo "Request $i"
done
```

**Expected**: First 60 succeed, then:
```json
{
  "error": "Rate Limit Exceeded",
  "message": "Maximum 60 requests per minute exceeded. Please slow down."
}
```

---

## 🛡️ Security Features

### 1. **CORS Restriction**
- **Development**: Allows `localhost:5173`, `localhost:3000`
- **Production**: Only your `FRONTEND_URL`
- **Prevents**: Cross-origin attacks from malicious websites

---

### 2. **API Key Authentication**
- **Header**: `X-API-Key: your-secret-key`
- **Validates**: Against `API_KEY`, `API_KEY_2`, `API_KEY_3` in `.env`
- **Protects**: All `/api/*` endpoints
- **Excludes**: `/docs`, `/health`, `/` (public endpoints)

---

### 3. **Rate Limiting**
- **Limit**: 60 requests/minute per API key (configurable)
- **Scope**: Per API key (not per IP)
- **Response**: HTTP 429 when exceeded
- **Prevents**: Abuse, quota drainage, DDoS

---

### 4. **Request Logging**
- **Logs**: All unauthorized attempts with IP address
- **Format**: `Unauthorized access attempt from 123.45.67.89 - Invalid API key: xK8Qp3m...`
- **Use**: Security monitoring, attack detection

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | **YES** | None | Primary API key (32+ chars recommended) |
| `API_KEY_2` | No | None | Backup API key |
| `API_KEY_3` | No | None | Additional API key |
| `FRONTEND_URL` | **YES** | `http://localhost:5173` | CORS allowed origin |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | Max requests per minute per key |
| `DEBUG` | No | `False` | If `True`, allows multiple localhost origins |

---

## 📊 Monitoring

### View Logs (Unauthorized Attempts)

```bash
# Real-time log monitoring
docker-compose logs -f api | grep "Unauthorized"

# Or if running locally
tail -f logs/app.log | grep "Unauthorized"
```

**Example Output**:
```
2026-03-25 10:15:23 - WARNING - Unauthorized access attempt from 192.168.1.100 - No API key provided
2026-03-25 10:16:45 - WARNING - Unauthorized access attempt from 192.168.1.100 - Invalid API key: badkey12...
2026-03-25 10:18:30 - WARNING - Rate limit exceeded for API key: xK8Qp3m... from 192.168.1.50
```

---

### Check Current Security Status

```bash
curl http://localhost:8001/
```

**Response**:
```json
{
  "name": "TransIQ Backend",
  "version": "2.0.0",
  "security": {
    "authentication": "API Key (X-API-Key header)",
    "rate_limit": "60 requests/minute",
    "cors": "Restricted"
  }
}
```

---

## 🚨 Production Deployment Checklist

### Before Going Live:

- [ ] **Generate strong API keys** (32+ characters)
- [ ] **Update FRONTEND_URL** to production domain (https://yourdomain.com)
- [ ] **Set DEBUG=false** in `.env`
- [ ] **Never commit `.env`** to git (check `.gitignore`)
- [ ] **Rotate API keys** every 90 days
- [ ] **Monitor logs** for unauthorized attempts
- [ ] **Enable HTTPS** (use Nginx reverse proxy)
- [ ] **Test CORS** from production domain
- [ ] **Test rate limiting** under load
- [ ] **Document API keys** in secure password manager

---

## 🔄 Key Rotation (Every 90 Days)

### Step 1: Generate New Key
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 2: Add as `API_KEY_2`
```bash
# .env
API_KEY=old-key-here
API_KEY_2=new-key-here  # ← Add new key
```

### Step 3: Update Frontend
- Deploy frontend with new key in `VITE_API_KEY`

### Step 4: Remove Old Key (After 7 Days)
```bash
# .env
API_KEY=new-key-here
# API_KEY_2=old-key-removed  # ← Comment out
```

**Grace Period**: Keep old key active for 7 days to allow frontend updates to propagate.

---

## 🛠️ Troubleshooting

### Problem: "No API keys configured - authentication disabled"

**Cause**: `API_KEY` not set in `.env`

**Solution**:
```bash
# Generate key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
echo "API_KEY=your-generated-key" >> .env

# Restart backend
```

---

### Problem: Frontend gets 401 errors

**Cause**: Missing or wrong API key in frontend

**Check**:
```javascript
// Verify API key is set
console.log(import.meta.env.VITE_API_KEY);
```

**Fix**:
```bash
# Frontend .env.local
VITE_API_KEY=xK8Qp3mN9vR2tY6wZ4aB1cD5eF7gH0iJ8kL2mN4oP6qR8sT0
```

---

### Problem: CORS errors in browser

**Cause**: Frontend URL not in `FRONTEND_URL`

**Check Browser Console**:
```
Access to XMLHttpRequest at 'http://localhost:8001/api/v2/generate' 
from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Fix**:
```bash
# .env
FRONTEND_URL=http://localhost:3000  # Match your frontend port
```

---

### Problem: Rate limit too strict

**Symptoms**: Legitimate users getting 429 errors

**Solution**:
```bash
# .env
RATE_LIMIT_PER_MINUTE=120  # Increase to 120 requests/minute
```

---

## 📈 Next Steps (Phase 2: JWT Authentication)

**Current**: API keys (good for internal/MVP)  
**Next**: JWT tokens (needed for multi-user SaaS)

### When to Upgrade:

1. **You need user accounts** (sign up, login)
2. **Data isolation** (users can't see each other's data)
3. **Usage tracking** per user (billing, quotas)
4. **Role-based access** (admin, user, guest)

### Future Implementation:
- JWT token authentication
- User registration/login
- Per-user document isolation
- Usage quotas and billing
- OAuth2 for enterprise SSO

**Current API key security is sufficient for:**
- ✅ MVPs and prototypes
- ✅ Internal tools
- ✅ Single-tenant deployments
- ✅ API-to-API integrations

---

## ✅ Summary

✅ **CORS fixed** - Only your domain allowed  
✅ **API key authentication** - All endpoints protected  
✅ **Rate limiting** - 60 req/min per key  
✅ **Request logging** - Unauthorized attempts tracked  
✅ **Easy integration** - Simple `X-API-Key` header  
✅ **Multiple keys** - API_KEY, API_KEY_2, API_KEY_3  
✅ **Production-ready** - No more open access  

**Your API is now secure!** 🔒
