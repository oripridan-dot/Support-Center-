#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}   Halilit Support Center - Local AI Launcher ${NC}"
echo -e "${BLUE}==============================================${NC}"

# 1. Check Environment
OS_NAME=$(uname)
if [[ "$OS_NAME" != "Darwin" ]]; then
    echo -e "${RED}Error: This script is designed for macOS (M1/M2/M3).${NC}"
    echo "You seem to be running on Linux/Windows."
    exit 1
fi

# 2. Check Prerequisites
echo -e "\n${GREEN}[1/4] Checking System Requirements...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed.${NC}"
    echo "Please install Docker Desktop for Mac: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker Desktop is not running.${NC}"
    echo "Please start Docker Desktop from your Applications folder and try again."
    exit 1
fi

if ! command -v ollama &> /dev/null; then
    echo -e "${RED}❌ Ollama is not installed.${NC}"
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed.${NC}"
    echo "Please install Node.js: https://nodejs.org/"
    exit 1
fi

# 3. Setup AI Models
echo -e "\n${GREEN}[2/4] Checking AI Models...${NC}"
if ! ollama list | grep -q "llama3.2:3b"; then
    echo "Downloading Llama 3.2 (3B)..."
    ollama pull llama3.2:3b
fi
if ! ollama list | grep -q "nomic-embed-text"; then
    echo "Downloading Embedding Model..."
    ollama pull nomic-embed-text
fi

# 4. Start Vector Database
echo -e "\n${GREEN}[3/4] Starting Vector Database (Qdrant)...${NC}"
if [ ! "$(docker ps -q -f name=halilit-qdrant)" ]; then
    if [ "$(docker ps -aq -f name=halilit-qdrant)" ]; then
        docker start halilit-qdrant
    else
        docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage --name halilit-qdrant qdrant/qdrant
    fi
fi
echo "✅ Qdrant is running."

# 5. Launch Services
echo -e "\n${GREEN}[4/4] Launching App...${NC}"
PROJECT_ROOT=$(pwd)

osascript <<EOF
tell application "Terminal"
    activate
    -- Window 1: Backend
    do script "echo 'Starting Backend...'; cd \"$PROJECT_ROOT/backend\"; python3 -m venv venv; source venv/bin/activate; pip install -r requirements.txt; ./venv/bin/python -m uvicorn app.main:app --reload"
    
    -- Window 2: Frontend
    tell application "System Events" to keystroke "n" using command down
    do script "echo 'Starting Frontend...'; cd \"$PROJECT_ROOT/frontend\"; npm install; npm run electron:dev" in front window
end tell
EOF

echo -e "${BLUE}🚀 System Launching! Check your Terminal windows.${NC}"
echo -e "1. One window is running the Backend (FastAPI)"
echo -e "2. One window is running the Frontend (Electron)"
echo -e "The App should open automatically once ready."
