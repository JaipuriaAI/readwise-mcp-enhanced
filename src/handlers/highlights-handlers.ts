import { initializeClient } from '../utils/client-init.js';

export async function handleListHighlights(args: any) {
  const client = await initializeClient();
  
  const params = {
    page_size: args.page_size,
    page: args.page,
    book_id: args.book_id,
    updated__lt: args.updated__lt,
    updated__gt: args.updated__gt,
    highlighted_at__lt: args.highlighted_at__lt,
    highlighted_at__gt: args.highlighted_at__gt,
  };
  
  const response = await client.listHighlights(params);
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(response.data, null, 2),
      },
    ],
  };
}

export async function handleCreateHighlight(args: any) {
  const client = await initializeClient();
  
  const response = await client.createHighlight(args);
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(response.data, null, 2),
      },
    ],
  };
}

export async function handleExportHighlights(args: any) {
  const client = await initializeClient();
  
  const params = {
    updatedAfter: args.updatedAfter,
    ids: args.ids,
    includeDeleted: args.includeDeleted,
    pageCursor: args.pageCursor,
  };
  
  const response = await client.exportHighlights(params);
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(response.data, null, 2),
      },
    ],
  };
}

export async function handleGetDailyReview(args: any) {
  const client = await initializeClient();
  
  const response = await client.getDailyReview();
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(response.data, null, 2),
      },
    ],
  };
}

export async function handleListBooks(args: any) {
  const client = await initializeClient();
  
  const params = {
    page_size: args.page_size,
    page: args.page,
    category: args.category,
    source: args.source,
    updated__lt: args.updated__lt,
    updated__gt: args.updated__gt,
    last_highlight_at__lt: args.last_highlight_at__lt,
    last_highlight_at__gt: args.last_highlight_at__gt,
  };
  
  const response = await client.listBooks(params);
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(response.data, null, 2),
      },
    ],
  };
}

export async function handleGetBookHighlights(args: any) {
  const client = await initializeClient();
  
  const response = await client.getBookHighlights(args.bookId);
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(response.data, null, 2),
      },
    ],
  };
}

export async function handleSearchHighlights(args: any) {
  const client = await initializeClient();
  
  const params = {
    textQuery: args.textQuery,
    fieldQueries: args.fieldQueries,
    bookId: args.bookId,
    limit: args.limit,
  };
  
  const response = await client.searchHighlights(params);
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(response.data, null, 2),
      },
    ],
  };
}

// Enhanced topic search handler that replaces the existing one
export async function handleEnhancedTopicSearch(args: any) {
  const client = await initializeClient();
  
  const response = await client.searchDocumentsAndHighlights(args.searchTerms);
  
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(response.data, null, 2),
      },
    ],
  };
}