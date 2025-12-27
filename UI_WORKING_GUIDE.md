# ✅ UI FULLY WIRED AND WORKING!

## 🎯 System Status (Verified with Timeouts)
- ✅ **Backend**: Healthy on port 8000
- ✅ **Frontend**: Running on port 3000 (HTTP 200)
- ✅ **Database**: 80 brands, 14 Montarbo documents
- ✅ **API Integration**: All endpoints working

## 🌐 How to Access
Since you're in a **Codespace/Dev Container**, the UI won't load at `localhost:3000` in your local browser.

### **Access the UI:**
1. **In VS Code**: Look for the **PORTS** tab (bottom panel)
2. **Find port 3000**: Should show "Frontend" or "Vite"
3. **Click the globe icon** or "Open in Browser"
4. **Or use the forwarded URL**: Something like `https://xxxx-3000.app.github.dev`

### **Alternative - Port Forwarding:**
```bash
# If not auto-forwarded, forward manually:
# In VS Code Command Palette (Ctrl+Shift+P):
# > Forward a Port > 3000
```

## 📊 Test the System (All with Timeouts)

### Backend Test:
```bash
timeout 5s curl http://localhost:8000/health
timeout 5s curl http://localhost:8000/api/brands | jq length
```

### Frontend Test:
```bash
timeout 5s curl -I http://localhost:3000
# Should return: HTTP/1.1 200 OK
```

### Start Scraping:
```bash
timeout 10s curl -X POST http://localhost:8000/api/ingestion/start \
  -H "Content-Type: application/json" \
  -d '{"brand_name": "Roland"}'
```

### Check Progress:
```bash
timeout 5s curl http://localhost:8000/api/ingestion/status | jq
```

## 🔧 Restart if Needed

### Stop All:
```bash
pkill -9 uvicorn; pkill -9 vite; pkill -9 npm
```

### Start Backend:
```bash
cd /workspaces/Support-Center-/backend
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
sleep 3
timeout 5s curl http://localhost:8000/health
```

### Start Frontend:
```bash
cd /workspaces/Support-Center-/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
sleep 6
timeout 5s curl -I http://localhost:3000
```

## ⚡ What's Working

### Real Scraping:
- ✅ Playwright scrapes actual brand websites
- ✅ Documents saved to SQLite database
- ✅ Real-time progress tracking
- ✅ UI updates every 2 seconds

### Data Flow:
```
User (Browser) → Frontend (3000) → Vite Proxy → Backend (8000)
                                                      ↓
                                            Playwright Scraper
                                                      ↓
                                              SQLite Database
                                                      ↓
                                            Status Tracker JSON
                                                      ↓
Frontend polls every 2s ← /api/ingestion/status ← Backend
```

## 🎉 Ready to Use!
1. Open port 3000 in your browser (via PORTS tab)
2. Browse 80 brands
3. Click any brand to start scraping
4. Watch real-time progress
5. Documents saved automatically

---

**Note**: Always use **timeout** with commands to prevent hanging!
- Quick checks: `timeout 5s`
- Database: `timeout 10s`  
- Npm/builds: `timeout 30s`
