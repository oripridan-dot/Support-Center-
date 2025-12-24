# Halilit Brands - Automatic Ingestion

This directory contains scripts for automatically ingesting all Halilit partner brands.

## Overview

**80 Halilit Brands** are configured for automatic ingestion, including:

### Priority Brands (Ingested First)
- Adam Audio ✓ (Already ingested)
- KRK Systems
- Roland
- Boss
- Nord
- Mackie
- Allen & Heath
- PreSonus
- Universal Audio
- Warm Audio
- Avid
- Steinberg
- Eve Audio

### All Other Partners
The system will automatically ingest:
- Pearl, Akai Professional, ESP, Hiwatt, Heritage Audio, Ashdown Engineering
- Ultimate Support, Sonarworks, Headrush FX, Maton Guitars, Oberheim
- ASM, V-MODA, Jasmine Guitars, EAW, Keith McMillen, Lynx, Maybach
- Cordoba Guitars, Bohemian, Foxgear, Maestro, Remo, Guild, Breedlove
- M-Audio, Xotic, Medeli, Paiste, Washburn, Oscar Schmidt, Montarbo
- Xvive, Tombo, Antigua, On Stage, Turkish, Santos Martinez, Rapier 33
- Adams, Bespeco, Topp Pro, Fusion, Rhythm Tech, Dynaudio, Gon Bops
- Fzone, Studio Logic, Perri's Leathers, Expressive E, Show, Vintage
- Innovative Percussion, Drumdots, MJC Ironworks, Lag Guitars
- Austrian Audio, Amphion, Magma, Rogers, Solar Guitars, Eden
- Regal Tip, Dixon, Marimba One, Encore

## Automatic Startup

The ingestion runs automatically when you start the codespace:

```bash
# Managed by .devcontainer/startup.sh
# Logs: /tmp/halilit_ingestion.log
# PID: /tmp/halilit_ingestion.pid
```

## Manual Ingestion

To run ingestion manually:

```bash
cd /workspaces/Support-Center-/backend
python3 scripts/ingest_halilit_brands.py
```

## Monitor Progress

```bash
# Watch live progress
tail -f /tmp/halilit_ingestion.log

# Check if running
cat /tmp/halilit_ingestion.pid

# View completion status
grep "COMPLETE" /tmp/halilit_ingestion.log
```

## Configuration

Edit `scripts/ingest_halilit_brands.py` to:
- Change priority brands list
- Adjust max products per brand
- Enable/disable PDFs or images
- Modify timeout settings

## Notes

- **Yamaha, Sennheiser, Behringer** are NOT Halilit brands and excluded
- Ingestion runs in background (~30-60 minutes for all brands)
- Priority brands get more products scraped (50 vs 20)
- 2-second delay between brands to avoid overwhelming servers
