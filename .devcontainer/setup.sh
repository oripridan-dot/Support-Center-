#!/bin/bash
# One-time setup script for the dev container

echo "Setting up Halilit Support Center development environment..."

# Install Python dependencies
cd /workspaces/Support-Center-/backend
pip install -q -r requirements.txt

# Install Node dependencies  
cd /workspaces/Support-Center-/frontend
npm install --silent

echo "✓ Development environment setup complete"
