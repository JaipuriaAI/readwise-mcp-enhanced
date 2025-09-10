"""
Readwise API client for Python FastMCP server
Port of the TypeScript readwise-client.ts to Python
"""

import os
import re
import requests
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import time

@dataclass
class ReadwiseDocument:
    id: str
    url: str
    source_url: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    summary: Optional[str] = None
    published_date: Optional[Union[str, int]] = None
    image_url: Optional[str] = None
    location: str = 'new'  # 'new' | 'later' | 'shortlist' | 'archive' | 'feed'
    category: Optional[str] = None  # 'article' | 'book' | 'tweet' | 'pdf' | 'email' | 'youtube' | 'podcast' | 'video'
    tags: Optional[Union[List[str], Dict]] = None
    site_name: Optional[str] = None
    word_count: Optional[int] = None
    created_at: str = ""
    updated_at: str = ""
    notes: Optional[str] = None
    parent_id: Optional[str] = None
    reading_progress: Optional[float] = None
    first_opened_at: Optional[str] = None
    last_opened_at: Optional[str] = None
    saved_at: Optional[str] = None
    last_moved_at: Optional[str] = None
    html_content: Optional[str] = None

@dataclass
class ReadwiseTag:
    key: str
    name: str

@dataclass
class ReadwiseHighlight:
    id: int
    text: str
    note: Optional[str] = None
    location: Optional[int] = None
    location_type: str = 'order'  # 'page' | 'order' | 'time_offset'
    highlighted_at: Optional[str] = None
    url: Optional[str] = None
    color: str = 'yellow'  # 'yellow' | 'blue' | 'pink' | 'orange' | 'green' | 'purple'
    updated: str = ""
    book_id: int = 0
    tags: List[ReadwiseTag] = field(default_factory=list)

@dataclass
class ReadwiseBook:
    id: int
    user_book_id: int
    title: str
    author: str
    readable_title: str
    source: str
    cover_image_url: Optional[str] = None
    unique_url: Optional[str] = None
    book_tags: List[ReadwiseTag] = field(default_factory=list)
    category: str = 'books'  # 'books' | 'articles' | 'tweets' | 'podcasts' | 'supplementals'
    document_note: Optional[str] = None
    summary: Optional[str] = None
    readwise_url: str = ""
    source_url: Optional[str] = None
    asin: Optional[str] = None
    num_highlights: int = 0
    last_highlight_at: Optional[str] = None
    updated: str = ""
    highlights: List[ReadwiseHighlight] = field(default_factory=list)

@dataclass
class APIMessage:
    type: str  # 'info' | 'warning' | 'error'
    content: str

@dataclass
class APIResponse:
    data: Any
    messages: Optional[List[APIMessage]] = None

@dataclass
class SearchHighlightsResult:
    highlight: ReadwiseHighlight
    book: Dict[str, Any]  # Book without highlights
    score: int
    matched_fields: List[str]

class ReadwiseClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = 'https://readwise.io/api/v3'
        self.v2_base_url = 'https://readwise.io/api/v2'
        self.auth_url = 'https://readwise.io/api/v2/auth/'
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        })

    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None, use_v2_api: bool = False) -> Dict:
        """Make HTTP request to Readwise API"""
        base_url = self.v2_base_url if use_v2_api else self.base_url
        
        if endpoint.startswith('http'):
            url = endpoint
        else:
            url = f"{base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = self.session.get(url)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'PATCH':
                response = self.session.patch(url, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url)
            
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                retry_after_seconds = int(retry_after)
                raise Exception(f'RATE_LIMIT:{retry_after_seconds}')
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.HTTPError as e:
            error_text = response.text if 'response' in locals() else str(e)
            raise Exception(f"Readwise API error: {response.status_code if 'response' in locals() else 'Unknown'} - {error_text}")

    def _create_response(self, data: Any, messages: Optional[List[APIMessage]] = None) -> APIResponse:
        return APIResponse(data=data, messages=messages or [])

    def _create_info_message(self, content: str) -> APIMessage:
        return APIMessage(type='info', content=content)

    def _create_error_message(self, content: str) -> APIMessage:
        return APIMessage(type='error', content=content)

    # ========== READER API METHODS (v3) ==========

    def validate_auth(self) -> APIResponse:
        """Validate authentication"""
        try:
            result = self._make_request(self.auth_url)
            return self._create_response(result)
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def create_document(self, url: str, html: Optional[str] = None, tags: Optional[List[str]] = None, 
                       location: str = 'new', category: Optional[str] = None) -> APIResponse:
        """Save a document to Readwise Reader"""
        try:
            data = {'url': url}
            if html:
                data['html'] = html
            if tags:
                data['tags'] = tags
            if location:
                data['location'] = location
            if category:
                data['category'] = category
                
            result = self._make_request('/save/', method='POST', data=data)
            return self._create_response(result)
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def list_documents(self, **params) -> APIResponse:
        """List documents with optional filtering"""
        try:
            # Extract client-side parameters
            limit = params.pop('limit', None)
            content_max_length = params.pop('contentMaxLength', None)
            content_start_offset = params.pop('contentStartOffset', None)
            content_filter_keywords = params.pop('contentFilterKeywords', None)
            
            # Handle withFullContent performance warnings
            if params.get('withFullContent'):
                # First check document count
                count_params = {k: v for k, v in params.items() if k not in ['withFullContent', 'withHtmlContent']}
                
                query_params = []
                for key, value in count_params.items():
                    if value is not None:
                        query_params.append(f"{key}={value}")
                
                query_string = '&'.join(query_params)
                count_endpoint = f"/list/{'?' + query_string if query_string else ''}"
                
                count_response = self._make_request(count_endpoint)
                
                user_limit = limit or 5
                if count_response['count'] > user_limit:
                    # Get limited documents with full content
                    query_params = []
                    for key, value in params.items():
                        if value is not None:
                            query_params.append(f"{key}={value}")
                    
                    query_string = '&'.join(query_params)
                    endpoint = f"/list/{'?' + query_string if query_string else ''}"
                    
                    result = self._make_request(endpoint)
                    
                    # Apply client-side limit
                    limited_results = result['results'][:user_limit]
                    limited_response = {
                        **result,
                        'results': limited_results,
                        'count': len(limited_results)
                    }
                    
                    if count_response['count'] <= 20:
                        message = self._create_info_message(
                            f"Found {count_response['count']} documents, but only returning the first {user_limit} due to full content request. "
                            f"To get the remaining {count_response['count'] - user_limit} documents with full content, "
                            f"you can fetch them individually by their IDs using the update/read document API."
                        )
                    else:
                        message = self._create_error_message(
                            f"Found {count_response['count']} documents, but only returning the first {user_limit} due to full content request. "
                            f"Getting full content for more than 20 documents is not supported due to performance limitations."
                        )
                    
                    return self._create_response(limited_response, [message])

            # Regular request
            query_params = []
            for key, value in params.items():
                if value is not None:
                    query_params.append(f"{key}={value}")
            
            query_string = '&'.join(query_params)
            endpoint = f"/list/{'?' + query_string if query_string else ''}"
            
            result = self._make_request(endpoint)
            
            # Apply client-side limit if specified
            if limit and limit > 0:
                limited_results = result['results'][:limit]
                limited_response = {
                    **result,
                    'results': limited_results,
                    'count': len(limited_results)
                }
                return self._create_response(limited_response)
            
            return self._create_response(result)
            
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def update_document(self, document_id: str, **data) -> APIResponse:
        """Update document metadata"""
        try:
            result = self._make_request(f'/update/{document_id}/', method='PATCH', data=data)
            return self._create_response(result)
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def delete_document(self, document_id: str) -> APIResponse:
        """Delete a document"""
        try:
            self._make_request(f'/delete/{document_id}/', method='DELETE')
            return self._create_response(None)
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def list_tags(self) -> APIResponse:
        """List all document tags"""
        try:
            result = self._make_request('/tags/')
            return self._create_response(result['results'])
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def search_documents_by_topic(self, search_terms: List[str]) -> APIResponse:
        """Search documents by topic using regex patterns"""
        try:
            # Fetch all documents without full content for performance
            all_documents = []
            next_page_cursor = None
            
            while True:
                params = {
                    'withFullContent': False,
                    'withHtmlContent': False,
                }
                
                if next_page_cursor:
                    params['pageCursor'] = next_page_cursor
                
                response = self.list_documents(**params)
                all_documents.extend(response.data['results'])
                next_page_cursor = response.data.get('nextPageCursor')
                
                if not next_page_cursor:
                    break

            # Create regex patterns from search terms (case-insensitive)
            regex_patterns = []
            for term in search_terms:
                escaped_term = re.escape(term)
                regex_patterns.append(re.compile(escaped_term, re.IGNORECASE))

            # Filter documents that match any of the search terms
            matching_documents = []
            for doc in all_documents:
                # Extract searchable text fields
                searchable_fields = [
                    doc.get('title', ''),
                    doc.get('summary', ''),
                    doc.get('notes', ''),
                    # Handle tags - they can be string array or object
                    ' '.join(doc.get('tags', [])) if isinstance(doc.get('tags'), list) else '',
                ]

                searchable_text = ' '.join(searchable_fields).lower()

                # Check if any regex pattern matches
                if any(pattern.search(searchable_text) for pattern in regex_patterns):
                    matching_documents.append(doc)

            return self._create_response(matching_documents)
            
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    # ========== HIGHLIGHTS API METHODS (v2) ==========

    def list_highlights(self, **params) -> APIResponse:
        """List highlights with filtering"""
        try:
            query_params = []
            for key, value in params.items():
                if value is not None:
                    query_params.append(f"{key}={value}")
            
            query_string = '&'.join(query_params)
            endpoint = f"/highlights/{'?' + query_string if query_string else ''}"
            
            result = self._make_request(endpoint, use_v2_api=True)
            return self._create_response(result)
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def create_highlight(self, highlights: List[Dict]) -> APIResponse:
        """Create highlights manually"""
        try:
            data = {'highlights': highlights}
            result = self._make_request('/highlights/', method='POST', data=data, use_v2_api=True)
            return self._create_response(result)
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def export_highlights(self, **params) -> APIResponse:
        """Export highlights for backup/analysis"""
        try:
            query_params = []
            for key, value in params.items():
                if value is not None:
                    query_params.append(f"{key}={value}")
            
            query_string = '&'.join(query_params)
            endpoint = f"/export/{'?' + query_string if query_string else ''}"
            
            result = self._make_request(endpoint, use_v2_api=True)
            return self._create_response(result)
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def get_daily_review(self) -> APIResponse:
        """Get daily review highlights for spaced repetition"""
        try:
            result = self._make_request('/review/', use_v2_api=True)
            return self._create_response(result)
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def list_books(self, **params) -> APIResponse:
        """List books with metadata"""
        try:
            query_params = []
            for key, value in params.items():
                if value is not None:
                    query_params.append(f"{key}={value}")
            
            query_string = '&'.join(query_params)
            endpoint = f"/books/{'?' + query_string if query_string else ''}"
            
            result = self._make_request(endpoint, use_v2_api=True)
            return self._create_response(result)
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def get_book_highlights(self, book_id: int) -> APIResponse:
        """Get all highlights from a specific book"""
        try:
            result = self.list_highlights(book_id=book_id, page_size=1000)
            return self._create_response(result.data['results'])
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def search_highlights(self, text_query: Optional[str] = None, field_queries: Optional[List[Dict]] = None, 
                         book_id: Optional[int] = None, limit: Optional[int] = None) -> APIResponse:
        """Advanced search across highlights with scoring"""
        try:
            results = []
            
            # Strategy: Use export API for comprehensive search across all data
            export_response = self.export_highlights()
            books = export_response.data['results']
            
            # Search through exported data
            for book in books:
                # Filter by bookId if specified
                if book_id and book['id'] != book_id:
                    continue
                
                for highlight in book['highlights']:
                    score = 0
                    matched_fields = []
                    
                    # Text query search (main search term)
                    if text_query:
                        query = text_query.lower()
                        if query in highlight['text'].lower():
                            score += 10
                            matched_fields.append('highlight_text')
                        if highlight.get('note') and query in highlight['note'].lower():
                            score += 8
                            matched_fields.append('highlight_note')
                        if query in book['title'].lower():
                            score += 6
                            matched_fields.append('document_title')
                        if query in book['author'].lower():
                            score += 4
                            matched_fields.append('document_author')
                    
                    # Field-specific queries
                    if field_queries:
                        for field_query in field_queries:
                            search_term = field_query['searchTerm'].lower()
                            field = field_query['field']
                            
                            if field == 'document_title' and search_term in book['title'].lower():
                                score += 8
                                matched_fields.append('document_title')
                            elif field == 'document_author' and search_term in book['author'].lower():
                                score += 8
                                matched_fields.append('document_author')
                            elif field == 'highlight_text' and search_term in highlight['text'].lower():
                                score += 10
                                matched_fields.append('highlight_text')
                            elif field == 'highlight_note' and highlight.get('note') and search_term in highlight['note'].lower():
                                score += 8
                                matched_fields.append('highlight_note')
                            elif field == 'highlight_tags':
                                for tag in highlight.get('tags', []):
                                    if search_term in tag['name'].lower():
                                        score += 6
                                        matched_fields.append('highlight_tags')
                                        break
                    
                    # If we have matches, add to results
                    if score > 0:
                        book_without_highlights = {k: v for k, v in book.items() if k != 'highlights'}
                        results.append({
                            'highlight': highlight,
                            'book': book_without_highlights,
                            'score': score,
                            'matched_fields': list(set(matched_fields))  # Remove duplicates
                        })
            
            # Sort by score and apply limit
            results.sort(key=lambda x: x['score'], reverse=True)
            if limit:
                results = results[:limit]
            
            return self._create_response(results)
            
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error

    def search_documents_and_highlights(self, search_terms: List[str]) -> APIResponse:
        """Enhanced topic search that includes both documents and highlights"""
        try:
            # Get documents (existing functionality)
            documents_response = self.search_documents_by_topic(search_terms)
            
            # Search highlights using the same terms
            highlights_response = self.search_highlights(
                text_query=' '.join(search_terms),
                limit=50
            )
            
            # Get relevant books
            book_ids = list(set([result['book']['id'] for result in highlights_response.data]))
            books_response = self.list_books(page_size=min(len(book_ids), 100))
            relevant_books = [book for book in books_response.data['results'] if book['id'] in book_ids]
            
            results = {
                'documents': documents_response.data,
                'highlights': highlights_response.data,
                'books': relevant_books
            }
            
            return self._create_response(results)
            
        except Exception as error:
            if str(error).startswith('RATE_LIMIT:'):
                seconds = int(str(error).split(':')[1])
                raise Exception(f"Rate limit exceeded. Too many requests. Please retry after {seconds} seconds.")
            raise error