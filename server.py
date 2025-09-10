#!/usr/bin/env python3
"""
Readwise MCP Enhanced - Python FastMCP Server
A comprehensive MCP server combining Readwise Reader + Highlights functionality
Ported from TypeScript to Python for FastMCP Cloud deployment
"""

import os
import re
import time
from typing import List, Dict, Any, Optional, Union
import wordninja
from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
from readwise_client import ReadwiseClient
try:
    from mcp.types import ToolAnnotations
except ImportError:
    # Fallback if annotations not available
    ToolAnnotations = None

# Initialize FastMCP server
mcp = FastMCP("Readwise MCP Enhanced")

# Add rate limiting middleware based on Readwise API documentation
try:
    from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
    # Readwise API limits: 240 requests/minute (4/second) general, 20/minute for LIST endpoints
    # Using conservative 3/second with burst capacity to handle LIST endpoints safely
    mcp.add_middleware(RateLimitingMiddleware(
        max_requests_per_second=3.0,
        burst_capacity=10  # Allow some burst for non-LIST operations
    ))
except ImportError:
    # Graceful fallback if middleware not available
    pass

# Initialize Readwise client (will be initialized when first needed)
readwise_token = os.getenv('READWISE_TOKEN')
client = None

# Simple cache for expensive operations (helps reduce API calls)
_cache = {}
_cache_timestamps = {}
CACHE_TTL = 300  # 5 minutes

def is_cache_valid(key: str) -> bool:
    """Check if cached data is still valid"""
    if key not in _cache or key not in _cache_timestamps:
        return False
    return (time.time() - _cache_timestamps[key]) < CACHE_TTL

def get_cached(key: str):
    """Get cached data if valid"""
    if is_cache_valid(key):
        return _cache[key]
    return None

def set_cache(key: str, data):
    """Cache data with timestamp"""
    _cache[key] = data
    _cache_timestamps[key] = time.time()

def get_client():
    global client
    if client is None:
        if not readwise_token:
            raise ValueError("READWISE_TOKEN environment variable is required")
        client = ReadwiseClient(readwise_token)
    return client

# Pydantic models for request validation
class SaveDocumentRequest(BaseModel):
    url: str = Field(..., description="URL of the document to save")
    html: Optional[str] = Field(None, description="HTML content of the document (optional)")
    tags: Optional[List[str]] = Field(None, description="Tags to add to the document")
    location: str = Field("new", description="Location to save the document")
    category: Optional[str] = Field(None, description="Category of the document")

class ListDocumentsRequest(BaseModel):
    id: Optional[str] = Field(None, description="Filter by specific document ID")
    updatedAfter: Optional[str] = Field(None, description="Filter documents updated after this date (ISO 8601)")
    addedAfter: Optional[str] = Field(None, description="Filter documents added after this date (ISO 8601)")
    location: Optional[str] = Field(None, description="Filter by document location")
    category: Optional[str] = Field(None, description="Filter by document category")
    tag: Optional[str] = Field(None, description="Filter by tag name")
    pageCursor: Optional[str] = Field(None, description="Page cursor for pagination")
    withHtmlContent: Optional[bool] = Field(False, description="Include HTML content (performance warning)")
    withFullContent: Optional[bool] = Field(False, description="Include full text content (performance warning)")
    contentMaxLength: Optional[int] = Field(50000, description="Maximum content length per document")
    contentStartOffset: Optional[int] = Field(0, description="Character offset to start content extraction")
    contentFilterKeywords: Optional[List[str]] = Field(None, description="Filter content by keywords")
    limit: Optional[int] = Field(None, description="Maximum number of documents to return")

class UpdateDocumentRequest(BaseModel):
    id: str = Field(..., description="Document ID to update")
    title: Optional[str] = Field(None, description="New title")
    author: Optional[str] = Field(None, description="New author")
    summary: Optional[str] = Field(None, description="New summary")
    published_date: Optional[str] = Field(None, description="New published date")
    image_url: Optional[str] = Field(None, description="New image URL")
    location: Optional[str] = Field(None, description="New location")
    category: Optional[str] = Field(None, description="New category")

class DeleteDocumentRequest(BaseModel):
    id: str = Field(..., description="Document ID to delete")

class TopicSearchRequest(BaseModel):
    searchTerms: List[str] = Field(..., description="Search terms to look for")

class ListHighlightsRequest(BaseModel):
    page_size: Optional[int] = Field(100, description="Number of highlights per page")
    page: Optional[int] = Field(None, description="Page number")
    book_id: Optional[int] = Field(None, description="Filter by book ID")
    updated__lt: Optional[str] = Field(None, description="Updated before this date")
    updated__gt: Optional[str] = Field(None, description="Updated after this date")
    highlighted_at__lt: Optional[str] = Field(None, description="Highlighted before this date")
    highlighted_at__gt: Optional[str] = Field(None, description="Highlighted after this date")

class CreateHighlightRequest(BaseModel):
    highlights: List[Dict[str, Any]] = Field(..., description="List of highlights to create")

class ExportHighlightsRequest(BaseModel):
    updatedAfter: Optional[str] = Field(None, description="Export highlights updated after this date")
    ids: Optional[str] = Field(None, description="Comma-separated list of highlight IDs")
    includeDeleted: Optional[bool] = Field(False, description="Include deleted highlights")
    pageCursor: Optional[str] = Field(None, description="Page cursor for pagination")

class ListBooksRequest(BaseModel):
    page_size: Optional[int] = Field(100, description="Number of books per page")
    page: Optional[int] = Field(None, description="Page number")
    category: Optional[str] = Field(None, description="Filter by category")
    source: Optional[str] = Field(None, description="Filter by source")
    updated__lt: Optional[str] = Field(None, description="Updated before this date")
    updated__gt: Optional[str] = Field(None, description="Updated after this date")
    last_highlight_at__lt: Optional[str] = Field(None, description="Last highlight before this date")
    last_highlight_at__gt: Optional[str] = Field(None, description="Last highlight after this date")

class GetBookHighlightsRequest(BaseModel):
    # Allow searching by book ID OR by book title/author (more natural workflow)
    bookId: Optional[int] = Field(None, description="Book ID to get highlights from")
    title: Optional[str] = Field(None, description="Book title to search for")
    author: Optional[str] = Field(None, description="Book author to search for") 
    # At least one field must be provided
    
    def model_post_init(self, __context) -> None:
        if not any([self.bookId, self.title, self.author]):
            raise ValueError("Must provide either bookId OR title/author to search for book")

class SearchHighlightsRequest(BaseModel):
    textQuery: Optional[str] = Field(None, description="Main search query")
    fieldQueries: Optional[List[Dict[str, str]]] = Field(None, description="Field-specific queries")
    bookId: Optional[int] = Field(None, description="Filter by book ID")
    limit: Optional[int] = Field(None, description="Maximum number of results")

# Utility functions
def process_with_wordninja(text: str) -> str:
    """Process text with wordninja for better word segmentation"""
    try:
        # Split text into words and rejoin with proper spacing
        words = wordninja.split(text)
        return ' '.join(words)
    except Exception:
        return text

def extract_keywords_from_content(content: str, keywords: List[str]) -> str:
    """Extract sections containing keywords from content"""
    if not keywords:
        return content
    
    sentences = re.split(r'[.!?]+', content)
    matching_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if any(keyword.lower() in sentence.lower() for keyword in keywords):
            matching_sentences.append(sentence)
    
    return '. '.join(matching_sentences)

# ========== READER TOOLS (6) ==========

@mcp.tool(
    name="readwise_save_document",
    description="Save a document (URL or HTML content) to Readwise Reader",
    annotations=ToolAnnotations(
        title="Save Document to Reader", 
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False
    ) if ToolAnnotations else None,
    tags=["reader", "document", "save"]
)
def readwise_save_document(request: SaveDocumentRequest) -> Dict[str, Any]:
    """Save a document (URL or HTML content) to Readwise Reader"""
    try:
        response = get_client().create_document(
            url=request.url,
            html=request.html,
            tags=request.tags,
            location=request.location,
            category=request.category
        )
        return {
            "success": True,
            "data": response.data,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool(
    name="readwise_list_documents",
    description="List documents from Readwise Reader with optional filtering and smart content controls. Use conservative limits to avoid rate limits.",
    annotations=ToolAnnotations(
        title="List Reader Documents",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True
    ) if ToolAnnotations else None,
    tags=["reader", "document", "list", "search"]
)
async def readwise_list_documents(request: ListDocumentsRequest, ctx: Context = None) -> Dict[str, Any]:
    """List documents from Readwise Reader with optional filtering and smart content controls"""
    try:
        if ctx:
            await ctx.info("Retrieving documents from Readwise Reader...")
            
        # Convert request to dictionary for the client
        params = {}
        for field, value in request.model_dump().items():
            if value is not None:
                params[field] = value
        
        response = get_client().list_documents(**params)
        
        # Post-process content if needed
        if request.withFullContent and response.data.get('results'):
            for doc in response.data['results']:
                if doc.get('html_content'):
                    # Process with wordninja for better text segmentation
                    processed_content = process_with_wordninja(doc['html_content'])
                    
                    # Apply keyword filtering if specified
                    if request.contentFilterKeywords:
                        processed_content = extract_keywords_from_content(
                            processed_content, 
                            request.contentFilterKeywords
                        )
                    
                    # Apply length limits
                    if request.contentMaxLength:
                        start_offset = request.contentStartOffset or 0
                        end_offset = start_offset + request.contentMaxLength
                        processed_content = processed_content[start_offset:end_offset]
                    
                    doc['html_content'] = processed_content
        
        return {
            "success": True,
            "data": response.data,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def readwise_update_document(request: UpdateDocumentRequest) -> Dict[str, Any]:
    """Update a document in Readwise Reader"""
    try:
        doc_id = request.id
        update_data = {k: v for k, v in request.model_dump().items() if k != 'id' and v is not None}
        
        response = get_client().update_document(doc_id, **update_data)
        return {
            "success": True,
            "data": response.data,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool(
    name="readwise_delete_document", 
    description="Delete a document from Readwise Reader. This action cannot be undone!",
    annotations=ToolAnnotations(
        title="Delete Reader Document",
        readOnlyHint=False,
        destructiveHint=True,  # Mark as destructive - cannot be undone
        idempotentHint=True
    ) if ToolAnnotations else None,
    tags=["reader", "document", "delete", "destructive"]
)
def readwise_delete_document(request: DeleteDocumentRequest) -> Dict[str, Any]:
    """Delete a document from Readwise Reader"""
    try:
        response = get_client().delete_document(request.id)
        return {
            "success": True,
            "data": {"deleted": True, "id": request.id},
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool(
    name="readwise_list_tags",
    description="Get all document tags from Readwise Reader (cached for 5 minutes to reduce API calls)",
    annotations=ToolAnnotations(
        title="List Document Tags",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True
    ) if ToolAnnotations else None,
    tags=["reader", "tags", "metadata", "cached"]
)
def readwise_list_tags() -> Dict[str, Any]:
    """Get all document tags from Readwise Reader (cached for 5 minutes to reduce API calls)"""
    try:
        # Check cache first to avoid unnecessary API calls
        cached_tags = get_cached("tags_list")
        if cached_tags is not None:
            return cached_tags
            
        response = get_client().list_tags()
        result = {
            "success": True,
            "data": response.data,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
        
        # Cache the result to reduce future API calls
        set_cache("tags_list", result)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def readwise_topic_search(request: TopicSearchRequest) -> Dict[str, Any]:
    """Enhanced topic search across documents with AI-powered text processing"""
    try:
        # Process search terms with wordninja for better matching
        processed_terms = []
        for term in request.searchTerms:
            processed_term = process_with_wordninja(term)
            processed_terms.append(processed_term)
            # Also add original term
            if processed_term != term:
                processed_terms.append(term)
        
        response = get_client().search_documents_by_topic(processed_terms)
        return {
            "success": True,
            "data": response.data,
            "searchTermsUsed": processed_terms,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========== HIGHLIGHTS TOOLS (7) ==========

@mcp.tool(
    name="readwise_list_highlights", 
    description="List highlights with advanced filtering options. Use conservative limits to avoid hitting rate limits.",
    annotations=ToolAnnotations(
        title="List Highlights",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True
    ) if ToolAnnotations else None,
    tags=["highlights", "list", "search", "reading"]
)
def readwise_list_highlights(request: ListHighlightsRequest) -> Dict[str, Any]:
    """List highlights with advanced filtering options"""
    try:
        params = {k: v for k, v in request.model_dump().items() if v is not None}
        response = get_client().list_highlights(**params)
        
        # Context-optimized response - only essential fields
        if response.data.get('results'):
            optimized_results = []
            for highlight in response.data['results']:
                optimized_highlight = {
                    'id': highlight.get('id'),
                    'text': highlight.get('text'),
                    'note': highlight.get('note'),
                    'book_id': highlight.get('book_id')
                }
                optimized_results.append(optimized_highlight)
            response.data['results'] = optimized_results
        
        return {
            "success": True,
            "data": response.data,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def readwise_get_daily_review() -> Dict[str, Any]:
    """Get daily review highlights for spaced repetition learning"""
    try:
        response = get_client().get_daily_review()
        return {
            "success": True,
            "data": response.data,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def readwise_search_highlights(request: SearchHighlightsRequest) -> Dict[str, Any]:
    """Advanced search across highlights with field-specific queries and relevance scoring"""
    try:
        # Convert camelCase to snake_case for the API
        params = {}
        if request.textQuery is not None:
            params['text_query'] = request.textQuery
        if request.fieldQueries is not None:
            params['field_queries'] = request.fieldQueries
        if request.bookId is not None:
            params['book_id'] = request.bookId
        if request.limit is not None:
            params['limit'] = request.limit
        
        response = get_client().search_highlights(**params)
        
        # Context-optimized response
        optimized_results = []
        for result in response.data:
            optimized_result = {
                'text': result['highlight'].get('text'),
                'book': result['book'].get('title'),
                'author': result['book'].get('author'),
                'score': result.get('score')
            }
            optimized_results.append(optimized_result)
        
        return {
            "success": True,
            "data": optimized_results,
            "totalResults": len(response.data),
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def readwise_list_books(request: ListBooksRequest) -> Dict[str, Any]:
    """Get books with highlight metadata and filtering"""
    try:
        params = {k: v for k, v in request.model_dump().items() if v is not None}
        response = get_client().list_books(**params)
        
        # Context-optimized response - only essential fields
        if response.data.get('results'):
            optimized_results = []
            for book in response.data['results']:
                optimized_book = {
                    'id': book.get('id'),
                    'title': book.get('title'),
                    'author': book.get('author'),
                    'category': book.get('category'),
                    'num_highlights': book.get('num_highlights')
                }
                optimized_results.append(optimized_book)
            response.data['results'] = optimized_results
        
        return {
            "success": True,
            "data": response.data,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool(
    name="readwise_get_book_highlights",
    description="Get all highlights from a specific book. Can search by book ID directly or by title/author to find the book first.",
    annotations=ToolAnnotations(
        title="Get Book Highlights",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True
    ) if ToolAnnotations else None,
    tags=["highlights", "book", "search", "reading"]
)
async def readwise_get_book_highlights(request: GetBookHighlightsRequest, ctx: Context = None) -> Dict[str, Any]:
    """Get all highlights from a specific book"""
    try:
        client = get_client()
        book_id = None
        book_info = None
        
        # If bookId provided directly, use it
        if request.bookId:
            book_id = request.bookId
            if ctx:
                await ctx.info(f"Getting highlights for book ID {book_id}")
        else:
            # Search for book by title/author first (proper API workflow)
            if ctx:
                search_terms = []
                if request.title: search_terms.append(f"title: {request.title}")
                if request.author: search_terms.append(f"author: {request.author}")
                await ctx.info(f"Searching for book by {', '.join(search_terms)}")
            
            # Get list of books and search for matching title/author
            books_response = client.list_books(page_size=100)
            matching_books = []
            
            for book in books_response.data.get('results', []):
                title_match = not request.title or (request.title.lower() in book.get('title', '').lower())
                author_match = not request.author or (request.author.lower() in book.get('author', '').lower())
                
                if title_match and author_match:
                    matching_books.append(book)
            
            if not matching_books:
                return {
                    "success": False,
                    "error": f"No books found matching title='{request.title or 'any'}' author='{request.author or 'any'}'"
                }
            
            if len(matching_books) > 1:
                # Return multiple matches for user to choose from
                return {
                    "success": True,
                    "multiple_matches": True,
                    "books": [{"id": b["id"], "title": b["title"], "author": b["author"]} for b in matching_books],
                    "message": f"Found {len(matching_books)} matching books. Please use readwise_get_book_highlights with specific bookId."
                }
            
            # Single match found
            book_info = matching_books[0]
            book_id = book_info["id"]
            if ctx:
                await ctx.info(f"Found book: '{book_info['title']}' by {book_info['author']} (ID: {book_id})")
        
        # Get highlights for the book using proper API pattern
        response = client.get_book_highlights(book_id)
        
        result = {
            "success": True,
            "data": response.data,
            "bookId": book_id,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
        
        if book_info:
            result["book_info"] = {
                "title": book_info["title"],
                "author": book_info["author"],
                "id": book_info["id"]
            }
            
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def readwise_export_highlights(request: ExportHighlightsRequest) -> Dict[str, Any]:
    """Bulk export highlights for analysis and backup"""
    try:
        params = {k: v for k, v in request.model_dump().items() if v is not None}
        response = get_client().export_highlights(**params)
        return {
            "success": True,
            "data": response.data,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool
def readwise_create_highlight(request: CreateHighlightRequest) -> Dict[str, Any]:
    """Manually add highlights with full metadata support"""
    try:
        response = get_client().create_highlight(request.highlights)
        return {
            "success": True,
            "data": response.data,
            "created_count": len(request.highlights),
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    mcp.run()