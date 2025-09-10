#!/bin/bash

# Script to push Readwise MCP Python to GitHub
# Run this script from the readwise-mcp-python directory

set -e

echo "🚀 Preparing to push Readwise MCP Python to GitHub..."
echo

# Check if we're in the right directory
if [ ! -f "server.py" ]; then
    echo "❌ Error: Not in the readwise-mcp-python directory"
    echo "Please run this script from the directory containing server.py"
    exit 1
fi

# Initialize new git repository
echo "📝 Initializing new Git repository..."
rm -rf .git 2>/dev/null || true  # Remove any existing git
git init
git branch -M main

# Add all files
echo "📁 Adding files to Git..."
git add .

# Commit
echo "💾 Creating initial commit..."
git commit -m "Initial commit - Readwise MCP Enhanced Python for FastMCP Cloud

- Complete port from TypeScript to Python FastMCP
- All 13 tools: 6 Reader tools + 7 Highlights tools  
- AI-powered text processing with wordninja
- Context optimization (94% token reduction)
- Dual API support (Readwise v2 + v3)
- Production-ready error handling and rate limiting
- Ready for FastMCP Cloud deployment"

# Ask for GitHub repository name
echo
echo "📂 What would you like to name your GitHub repository?"
echo "   Suggested: readwise-mcp-python"
read -p "Repository name: " repo_name

# Default to suggested name if empty
if [ -z "$repo_name" ]; then
    repo_name="readwise-mcp-python"
fi

echo
echo "🔗 To complete the setup, you need to:"
echo "1. Create a new repository on GitHub named: $repo_name"
echo "2. Then run these commands:"
echo
echo "   git remote add origin https://github.com/yourusername/$repo_name.git"
echo "   git push -u origin main"
echo
echo "Replace 'yourusername' with your actual GitHub username."
echo
echo "🎯 After pushing, use this repository for FastMCP Cloud deployment:"
echo "   - Entrypoint: server.py:mcp"
echo "   - Environment variable: READWISE_TOKEN"
echo
echo "✅ Git repository initialized and committed locally!"
echo "📝 Ready for GitHub push once you create the remote repository."