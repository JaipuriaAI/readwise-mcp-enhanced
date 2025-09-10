#!/usr/bin/env python3
"""
Readwise MCP Enhanced - Python FastMCP Server
A comprehensive MCP server combining Readwise Reader + Highlights functionality
Ported from TypeScript to Python for FastMCP Cloud deployment
"""

import os
import re
from typing import List, Dict, Any, Optional, Union
import wordninja
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from readwise_client import ReadwiseClient

# Initialize FastMCP server
mcp = FastMCP("Readwise MCP Enhanced")

# Initialize Readwise client (will be initialized when first needed)
readwise_token = os.getenv('READWISE_TOKEN')
client = None

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
    bookId: int = Field(..., description="Book ID to get highlights from")

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

@mcp.tool
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

@mcp.tool
def readwise_list_documents(request: ListDocumentsRequest) -> Dict[str, Any]:
    """List documents from Readwise Reader with optional filtering and smart content controls"""
    try:
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

@mcp.tool
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

@mcp.tool
def readwise_list_tags() -> Dict[str, Any]:
    """Get all document tags from Readwise Reader"""
    try:
        response = get_client().list_tags()
        return {
            "success": True,
            "data": response.data,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
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

@mcp.tool
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

@mcp.tool
def readwise_get_book_highlights(request: GetBookHighlightsRequest) -> Dict[str, Any]:
    """Get all highlights from a specific book"""
    try:
        response = get_client().get_book_highlights(request.bookId)
        return {
            "success": True,
            "data": response.data,
            "bookId": request.bookId,
            "messages": [{"type": msg.type, "content": msg.content} for msg in (response.messages or [])]
        }
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