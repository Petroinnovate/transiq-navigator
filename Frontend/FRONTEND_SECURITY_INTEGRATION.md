# Frontend Security Integration Guide

## Overview

The TransIQ Backend now requires API key authentication. You need to update your frontend to send the `X-API-Key` header with every request.

---

## 1. Update Environment Variables

### Create `.env.local` (or `.env`)

```bash
# TransIQ-frontend/.env.local
VITE_API_KEY=ZSOLc_hD6aI6yK2BhP7SAItq9_ihNY9pUEhMAiEZLgs
VITE_API_BASE_URL=http://localhost:8001
```

**⚠️ IMPORTANT**: 
- Add `.env.local` to `.gitignore`
- Never commit API keys to version control
- Use different keys for development and production

---

## 2. Update API Client

### Option A: Axios (Recommended)

```typescript
// src/api/client.ts
import axios from 'axios';

const API_KEY = import.meta.env.VITE_API_KEY;
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

if (!API_KEY) {
  console.error('⚠️ VITE_API_KEY is not set in environment variables');
}

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'X-API-Key': API_KEY,
  },
});

// Optionally add response interceptor for better error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('🔒 Authentication failed: Invalid API key');
      // Optionally redirect to error page
    } else if (error.response?.status === 429) {
      console.warn('⏱️ Rate limit exceeded: Please slow down');
    }
    return Promise.reject(error);
  }
);

// Usage example
export const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await apiClient.post('/api/v2/generate', formData);
  return response.data;
};

export const searchDocuments = async (query: string, topK: number = 10) => {
  const response = await apiClient.post('/api/v2/search', {
    query,
    top_k: topK,
  });
  return response.data;
};
```

---

### Option B: Fetch API

```typescript
// src/api/client.ts
const API_KEY = import.meta.env.VITE_API_KEY;
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'X-API-Key': API_KEY,
      ...options.headers,
    },
  });

  if (response.status === 401) {
    throw new Error('Authentication failed: Invalid API key');
  }
  
  if (response.status === 429) {
    throw new Error('Rate limit exceeded: Please slow down');
  }

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Usage example
export const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  return fetchWithAuth('/api/v2/generate', {
    method: 'POST',
    body: formData,
  });
};
```

---

## 3. Update WebSocket Connection

### WebSocket with Authentication

```typescript
// src/api/websocket.ts
const API_KEY = import.meta.env.VITE_API_KEY;

export function connectWebSocket(docId: string) {
  // Include API key in query string (WebSocket doesn't support custom headers)
  const ws = new WebSocket(
    `ws://localhost:8001/ws/document/${docId}?api_key=${API_KEY}`
  );

  ws.onopen = () => {
    console.log('✅ WebSocket connected');
  };

  ws.onerror = (error) => {
    console.error('❌ WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('🔌 WebSocket disconnected');
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('📩 Progress update:', data);
    // Handle progress updates
  };

  return ws;
}
```

**Note**: Your backend WebSocket handler needs to be updated to accept `api_key` query parameter. Let me know if you need backend changes for this.

---

## 4. Production Deployment

### Environment Variables in Production

#### Vercel
```bash
# Add in Vercel dashboard: Settings → Environment Variables
VITE_API_KEY=production-api-key-here
VITE_API_BASE_URL=https://api.yourdomain.com
```

#### Netlify
```bash
# Add in Netlify dashboard: Site settings → Environment variables
VITE_API_KEY=production-api-key-here
VITE_API_BASE_URL=https://api.yourdomain.com
```

#### Docker
```dockerfile
# docker-compose.yml
services:
  frontend:
    build: .
    environment:
      - VITE_API_KEY=${VITE_API_KEY}
      - VITE_API_BASE_URL=http://api:8001
```

---

## 5. Testing

### Test API Key Authentication

```typescript
// src/tests/auth.test.ts
import { apiClient } from '@/api/client';

// Test 1: Valid API key (should work)
apiClient.get('/health')
  .then(() => console.log('✅ API key is valid'))
  .catch(() => console.error('❌ API key is invalid'));

// Test 2: Without API key (should fail)
fetch('http://localhost:8001/api/v2/health')
  .then(res => {
    if (res.status === 401) {
      console.log('✅ Authentication is working (401 without key)');
    }
  });
```

---

## 6. Error Handling UI

### Show User-Friendly Errors

```tsx
// src/components/ErrorAlert.tsx
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';

export function ApiErrorAlert({ error }: { error: any }) {
  if (error.response?.status === 401) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Authentication Error</AlertTitle>
        <AlertDescription>
          Invalid API key. Please contact support.
        </AlertDescription>
      </Alert>
    );
  }

  if (error.response?.status === 429) {
    return (
      <Alert variant="warning">
        <AlertTitle>Rate Limit Exceeded</AlertTitle>
        <AlertDescription>
          You're making too many requests. Please wait a moment.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert variant="destructive">
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>
        {error.message || 'An unexpected error occurred'}
      </AlertDescription>
    </Alert>
  );
}
```

---

## 7. Common Issues

### Issue: "VITE_API_KEY is not defined"

**Solution**:
1. Create `.env.local` file in frontend root
2. Add `VITE_API_KEY=your-key-here`
3. Restart dev server (`npm run dev`)

---

### Issue: "401 Unauthorized" errors

**Solution**:
- Verify API key matches backend `.env` file
- Check that `X-API-Key` header is being sent:
  ```javascript
  // In browser console
  console.log(import.meta.env.VITE_API_KEY);
  ```

---

### Issue: "CORS errors" in console

**Solution**:
- Backend `FRONTEND_URL` must match your frontend URL
- Backend `.env`:
  ```bash
  FRONTEND_URL=http://localhost:5173
  ```

---

## 8. Complete Example

### Full React Component with Authentication

```tsx
// src/pages/Upload.tsx
import { useState } from 'react';
import { apiClient } from '@/api/client';
import { ApiErrorAlert } from '@/components/ErrorAlert';

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<any>(null);
  const [result, setResult] = useState<any>(null);

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post('/api/v2/generate', formData);
      setResult(response.data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Upload Document</h1>
      
      {error && <ApiErrorAlert error={error} />}
      
      <input 
        type="file" 
        onChange={(e) => setFile(e.files?.[0] || null)} 
      />
      
      <button onClick={handleUpload} disabled={loading || !file}>
        {loading ? 'Uploading...' : 'Upload'}
      </button>
      
      {result && (
        <div>
          <p>Document ID: {result.doc_id}</p>
          <p>Task ID: {result.task_id}</p>
        </div>
      )}
    </div>
  );
}
```

---

## 9. Security Best Practices

### ✅ DO:
- Store API key in `.env.local` (not committed to git)
- Use different keys for dev/staging/production
- Regenerate keys if compromised
- Handle 401/429 errors gracefully in UI
- Log authentication errors to monitoring service

### ❌ DON'T:
- Hardcode API keys in source code
- Commit `.env` files to git
- Share API keys in Slack/email
- Use production keys in development
- Ignore authentication errors

---

## 10. Next Steps

After implementing this:

1. **Test locally**: Verify all requests include `X-API-Key` header
2. **Check browser console**: No CORS errors
3. **Test rate limiting**: Upload multiple files rapidly (should get 429 after 60 requests/minute)
4. **Deploy**: Update production environment variables
5. **Monitor**: Check backend logs for authentication errors

---

## Need Help?

- Backend not starting? Check [SECURITY.md](../TransIQ-backend-master/SECURITY.md)
- CORS errors? Verify `FRONTEND_URL` in backend `.env`
- 401 errors? Test API key with curl:
  ```bash
  curl -H "X-API-Key: your-key" http://localhost:8001/api/v2/health
  ```

**Questions?** Open an issue or contact the backend team.
