# 🎵 Support Center - Application Ready

## ✅ Services Running

### Frontend (Next.js React)
- **URL**: http://localhost:3000
- **Status**: ✅ Running
- **Port**: 3000
- **Features**: Chat interface, brand dashboard, system status monitoring

### Backend API (FastAPI)
- **URL**: http://0.0.0.0:8000
- **Status**: ✅ Running
- **Port**: 8000
- **Features**: RAG API, brand management, document ingestion, WebSocket status updates

### Continuous Background Ingestion Service
- **Status**: ✅ Running
- **Purpose**: Automatically builds complete product catalog documentation
- **Cycle Duration**: 24 hours
- **PID**: Check with `pgrep -f continuous_ingestion`

## 📋 Ingestion Queue (8 Brands)

The following brands are being ingested in priority order:

1. **Montarbo** - Music equipment
2. **RCF** - Pro audio systems
3. **Allen & Heath** - Mixing consoles
4. **Rode** - Microphones & audio
5. **Roland** - Music instruments & synthesizers
6. **Boss** - Effects & instruments
7. **Mackie** - Audio equipment
8. **PreSonus** - Digital audio workstations

Each cycle completes in ~24 hours, continuously building the RAG knowledge base.

## 📊 Monitoring

### View Ingestion Progress
```bash
./scripts/monitor_ingestion.sh
```

### View Logs
- **Frontend**: `/tmp/next_dev.log`
- **Ingestion**: `/tmp/continuous_ingestion_output.log`
- **Ingestion Status**: `/tmp/ingestion_status.json`

## 🔧 Managing Services

### Stop All Services
```bash
pkill -f "uvicorn|next dev|continuous_ingestion"
```

### Start Services Manually
```bash
# Backend
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev

# Ingestion Service
cd backend && python scripts/continuous_ingestion.py
```

### Monitor Service Status
```bash
echo "Frontend: $(lsof -i :3000 >/dev/null && echo '✅' || echo '❌')"
echo "Backend: $(lsof -i :8000 >/dev/null && echo '✅' || echo '❌')"
echo "Ingestion: $(pgrep -f continuous_ingestion >/dev/null && echo '✅' || echo '❌')"
```

## 🌐 Access the Application

1. **Open http://localhost:3000 in your browser**
2. Browse product brands and their documentation
3. Ask the AI chat for technical support and specifications
4. Monitor ingestion progress in System Status

## 📝 Notes

- The ingestion service runs in the background continuously
- No manual interaction required for daily catalog updates
- The RAG knowledge base grows with each ingestion cycle
- Frontend browser preview has been disabled (use your browser directly)

---

**Started**: 2025-12-24 07:13:00 UTC
**Last Updated**: 2025-12-24 07:14:00 UTC
