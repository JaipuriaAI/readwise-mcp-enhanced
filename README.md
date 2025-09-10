# Readwise MCP Enhanced - Python FastMCP

Enhanced MCP server unifying Readwise Reader + Highlights with AI-powered text processing and context optimization. Built with Python FastMCP framework for cloud deployment.

## Features

### 📚 **Enhanced Reader Management (6 tools)**
- **Smart Content Extraction**: Pagination, keyword filtering, length limits
- **AI-Powered Text Processing**: Automatic word segmentation fixes merged words
- **Performance Controls**: Built-in warnings and guidance for expensive operations
- **Flexible Filtering**: By location, category, tags, dates, and custom criteria

### 🎯 **Complete Highlights Ecosystem (7 tools)**  
- **Daily Reviews**: Spaced repetition learning system
- **Advanced Search**: Field-specific queries with relevance scoring
- **Book Management**: Full metadata with highlight counts and filtering
- **Export & Backup**: Bulk highlight analysis and incremental sync
- **Manual Creation**: Add highlights with full metadata support

### ⚡ **Production Excellence**
- **Context Optimized**: 94% reduction in token usage (25,600 → 1,600 tokens)
- **Dual API Architecture**: Seamless v2 (highlights) + v3 (Reader) integration
- **Unlimited Results**: No artificial limits, just efficient data per item
- **MCP Protocol Compliant**: Proper logging, error handling, and rate limiting

## Available Tools (13 Total)

### Reader Tools (6)
1. `readwise_save_document` - Save documents with full metadata control
2. `readwise_list_documents` - Enhanced with smart content controls
3. `readwise_update_document` - Update document metadata
4. `readwise_delete_document` - Remove documents from library
5. `readwise_list_tags` - Get all document tags
6. `readwise_topic_search` - AI-powered text processing and search

### Highlights Tools (7)
1. `readwise_list_highlights` - List highlights with advanced filtering
2. `readwise_get_daily_review` - Get spaced repetition highlights
3. `readwise_search_highlights` - Advanced search with field-specific queries
4. `readwise_list_books` - Get books with highlight metadata
5. `readwise_get_book_highlights` - Get all highlights from specific book
6. `readwise_export_highlights` - Bulk export for analysis and backup
7. `readwise_create_highlight` - Manually add highlights with metadata

## Local Development

### Requirements
- Python 3.8+
- FastMCP library
- Readwise account and API token

### Setup
1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your READWISE_TOKEN
   ```

4. Run locally:
   ```bash
   python server.py
   ```

## Deployment to FastMCP Cloud

### Prerequisites
- GitHub account
- GitHub repository containing this FastMCP server
- Readwise API token

### Steps

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Readwise MCP Python server"
   git branch -M main
   git remote add origin https://github.com/yourusername/readwise-mcp-python.git
   git push -u origin main
   ```

2. **Deploy to FastMCP Cloud**
   - Go to [fastmcp.cloud](https://fastmcp.cloud)
   - Sign in with GitHub
   - Create new project
   - Select your GitHub repository
   - Configure project settings:
     - **Project name**: `readwise-mcp-enhanced`
     - **Entrypoint**: `server.py:mcp` 
     - **Environment variables**: Add `READWISE_TOKEN` with your token value

3. **Access your deployed MCP**
   - FastMCP Cloud will provide a unique URL
   - Use this URL in your MCP clients (Claude Desktop, Continue, etc.)

### Configuration Example

For Claude Desktop, add to your configuration:

```json
{
  "mcpServers": {
    "readwise-mcp-enhanced": {
      "command": "npx",
      "args": ["-y", "fastmcp", "https://your-unique-fastmcp-url.com"],
      "env": {}
    }
  }
}
```

## Context Optimization

**94% Token Reduction** while maintaining full functionality:

| Tool | Before | After | Savings |
|------|--------|-------|---------|
| List Highlights (32 items) | ~25,600 tokens | ~1,600 tokens | 94% |
| Daily Review (5 items) | ~5,000 tokens | ~400 tokens | 92% |
| List Books (10 items) | ~8,000 tokens | ~600 tokens | 93% |

**Optimized Fields:**
- **Highlights**: `id`, `text`, `note`, `book_id` only
- **Books**: `id`, `title`, `author`, `category`, `num_highlights` only
- **Search**: `text`, `book`, `author`, `score` only

## AI-Powered Features

### **Intelligent Word Segmentation**
Automatically fixes common text extraction issues:
- `whatyou` → `what you`
- `fromdissatisfaction` → `from dissatisfaction`  
- `timeago` → `time ago`

### **Smart Content Processing**
- **Sentence-based chunking** for YouTube transcripts
- **Distributed keyword filtering** throughout content
- **Context-aware text extraction** with proper spacing

### **Advanced Search Algorithm**
- **Multi-field search** with relevance scoring
- **Export-based comprehensive search** equivalent to official MCP
- **Field-specific filtering** (title, author, text, notes, tags)

## Rate Limits

- **Reader API**: 20 requests/minute (default), 50/minute (CREATE/UPDATE)
- **Highlights API**: Standard Readwise limits with automatic retry-after handling
- **Smart Handling**: 429 responses include "Retry-After" header processing

## License

MIT

## Acknowledgments

This Python FastMCP server is a port of the enhanced TypeScript version, combining:
- **Enhanced Reader functionality** with smart content controls
- **Complete highlights integration** equivalent to official MCP
- **AI-powered text processing** with word segmentation
- **Context optimization** for production efficiency
- **Unified architecture** combining dual APIs seamlessly