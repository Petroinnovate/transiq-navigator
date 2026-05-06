# Testing Guide: Upload File and View Dashboard

## Step-by-Step Testing Instructions

### 1. Start the Servers

#### Backend (if not running):
```bash
cd "C:\github-copiolot\1 A TransIQ\TransIQ-backend-master\TransIQ-backend-master"
python -m uvicorn main:app --host localhost --port 8001 --reload
```
Or double-click: `start_backend.bat`

#### Frontend (if not running):
```bash
cd "C:\github-copiolot\1 A TransIQ\TransIQ-frontend-main\TransIQ-frontend-main"
npm run dev
```
Or double-click: `start_frontend.bat`

### 2. Access the Application

1. Open your browser
2. Navigate to: **http://localhost:5173**
3. You should see the TransIQ homepage

### 3. Upload a File

1. Click on **"Upload Data"** button or navigate to `/upload`
2. You'll see the upload page with:
   - Drag & drop area
   - "Choose Files" button
   - Supported formats: `.xlsx`, `.xls`, `.pdf`, `.csv`

3. **Upload a file:**
   - Click "Choose Files" button
   - Select an Excel file (.xlsx or .xls) or PDF file
   - The file will appear in the file list below

4. **Generate Dashboard:**
   - Click the **"Generate Dashboard"** button
   - You'll see a loading indicator ("Processing...")
   - Wait for the AI to process your file (this may take 30-60 seconds)

### 4. View the Dashboard

After processing completes:

1. You'll be automatically redirected to `/dashboard`
2. You should see:
   - **Dashboard Title and Description**
   - **KPI Cards** (4 cards showing key metrics)
   - **Six Sigma Analysis Section** (if data supports it):
     - Sigma Level
     - Defect Rate
     - Process Capability
     - DMAIC Methodology (Define, Measure, Analyze, Improve, Control)
     - Root Causes
   - **Charts** (various types: Bar, Line, Pie, Area, etc.)
   - **Insights Section**:
     - Executive Summary
     - Key Trends
     - Alerts & Actions
     - Strategic Recommendations
   - **Optimization Suggestions** (if available)
   - **Data Tables** (detailed data views)

### 5. What to Check

✅ **Verify these elements appear:**
- [ ] Dashboard title and description
- [ ] At least 4 KPI cards with values
- [ ] Six Sigma section (if applicable)
- [ ] Multiple charts (at least 5 as per backend prompt)
- [ ] Insights section with summary
- [ ] Tables with data (if applicable)

### 6. Troubleshooting

**If upload fails:**
- Check browser console (F12) for errors
- Verify backend is running at http://localhost:8001
- Check network tab for API call status
- Ensure file is valid Excel/PDF format

**If dashboard doesn't appear:**
- Check browser console for errors
- Verify API response in Network tab
- Check if backend returned valid JSON structure
- Look for CORS errors in console

**If charts don't render:**
- Check browser console for chart library errors
- Verify data structure matches expected format
- Check if chart data arrays are populated

### 7. Test Files

You can create a simple test Excel file with:
- Column headers
- Some numeric data
- Multiple rows

Example structure:
```
Name    | Value | Category
--------|-------|----------
Item 1  | 100   | A
Item 2  | 200   | B
Item 3  | 150   | A
```

### 8. Expected API Response Structure

The backend should return:
```json
{
  "dashboard": {
    "title": "Dashboard Title",
    "description": "Description",
    "sixSigma": { ... },
    "kpis": [ ... ],
    "charts": [ ... ],
    "tables": [ ... ],
    "insights": { ... },
    "optimizationSuggestions": [ ... ]
  }
}
```

### 9. Browser Developer Tools

Press **F12** to open developer tools:
- **Console tab**: Check for JavaScript errors
- **Network tab**: Monitor API calls to `/generate`
- **Response tab**: View the API response structure

### 10. Success Indicators

✅ Upload successful if you see:
- Toast notification: "Upload successful!"
- Automatic redirect to `/dashboard`
- Dashboard content appears

❌ Upload failed if you see:
- Toast notification: "Upload failed"
- Error message in console
- No redirect or empty dashboard

