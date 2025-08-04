import { parse } from 'node-html-parser';

// Convert URL content using jina.ai
export async function convertWithJina(url: string): Promise<string> {
  const jinaUrl = `https://r.jina.ai/${url}`;
  
  const response = await fetch(jinaUrl, {
    headers: {
      'Accept': 'text/plain',
      'User-Agent': 'Readwise-MCP-Server/1.0.0'
    }
  });
  
  if (!response.ok) {
    throw new Error(`Jina conversion failed: ${response.status}`);
  }
  
  return response.text();
}

// Extract text content from HTML string
export function extractTextFromHtml(htmlContent: string): string {
  if (!htmlContent?.trim()) {
    return '';
  }
  
  const root = parse(htmlContent);
  
  // Remove non-content elements
  root.querySelectorAll('script, style, nav, header, footer').forEach(el => el.remove());
  
  // Get title and body text
  const title = root.querySelector('title')?.text?.trim() || '';
  const bodyText = root.querySelector('body')?.text || root.text || '';
  
  // Clean up whitespace while preserving word boundaries
  const cleanText = bodyText
    .replace(/\r\n/g, '\n')  // Normalize line breaks
    .replace(/\r/g, '\n')   // Convert remaining carriage returns
    .replace(/\n+/g, ' ')   // Convert line breaks to spaces
    .replace(/\s+/g, ' ')   // Collapse multiple spaces to single spaces
    .replace(/(\w)([A-Z])/g, '$1 $2')  // Add space before capital letters if missing
    .trim();
  
  return title ? `${title}\n\n${cleanText}` : cleanText;
}

// Process content with pagination and filtering options
export function processContentWithOptions(
  content: string, 
  options: {
    maxLength?: number;
    startOffset?: number;
    filterKeywords?: string[];
  } = {}
): { 
  content: string; 
  truncated: boolean; 
  totalLength: number;
  extractedSections?: string[];
  debug?: any;
} {
  if (!content?.trim()) {
    return { content: '', truncated: false, totalLength: 0 };
  }
  
  const totalLength = content.length;
  let processedContent = content;
  let truncated = false;
  let extractedSections: string[] | undefined;
  let keywordFilteringApplied = false;
  
  // Filter by keywords if provided
  if (options.filterKeywords && options.filterKeywords.length > 0) {
    const sections: string[] = [];
    let paragraphs = content.split(/\n\s*\n/);
    
    // If paragraph splitting results in only one section (continuous text like YouTube transcripts),
    // fall back to sentence-based splitting
    if (paragraphs.length === 1 && paragraphs[0].length > 2000) {
      paragraphs = content.split(/\.\s+/).map(sentence => sentence.trim() + '.');
      
      // If sentences are still too long, use sliding window approach
      if (paragraphs.some(p => p.length > 1500)) {
        paragraphs = [];
        const windowSize = 800;
        const overlap = 100;
        
        for (let i = 0; i < content.length; i += (windowSize - overlap)) {
          const chunk = content.substring(i, i + windowSize);
          if (chunk.trim()) {
            paragraphs.push(chunk.trim());
          }
        }
      }
    }
    
    for (let i = 0; i < paragraphs.length; i++) {
      const paragraph = paragraphs[i];
      const hasKeyword = options.filterKeywords.some(keyword => 
        paragraph.toLowerCase().includes(keyword.toLowerCase())
      );
      
      if (hasKeyword) {
        // Include surrounding context: previous 2 and next 2 paragraphs for more context
        const contextStart = Math.max(0, i - 2);
        const contextEnd = Math.min(paragraphs.length, i + 3);
        const contextChunk = paragraphs.slice(contextStart, contextEnd).join('. ').trim();
        
        // Avoid duplicate sections by checking if we already have overlapping content
        const isDuplicate = sections.some(existing => 
          existing.includes(paragraph.trim()) || paragraph.trim().includes(existing)
        );
        
        if (!isDuplicate) {
          sections.push(contextChunk);
        }
      }
    }
    
    if (sections.length > 0) {
      extractedSections = sections;
      keywordFilteringApplied = true;
      
      // Instead of joining all sections, distribute the maxLength across chunks
      const maxLength = options.maxLength || 50000;
      const chunks: string[] = [];
      let totalUsed = 0;
      
      // Calculate how much space each chunk should get
      const avgChunkSize = Math.floor(maxLength / Math.min(sections.length, 10)); // Max 10 chunks
      const minChunkSize = 200; // Minimum viable chunk size
      
      for (let i = 0; i < sections.length && totalUsed < maxLength && chunks.length < 10; i++) {
        const section = sections[i];
        const remainingSpace = maxLength - totalUsed;
        const chunkSize = Math.max(minChunkSize, Math.min(avgChunkSize, remainingSpace));
        
        if (section.length <= chunkSize) {
          // Section fits entirely
          chunks.push(section);
          totalUsed += section.length + 4; // +4 for separator
        } else if (remainingSpace >= minChunkSize) {
          // Truncate section to fit
          chunks.push(section.substring(0, chunkSize - 3) + '...');
          totalUsed += chunkSize + 4;
        } else {
          // Not enough space left
          break;
        }
      }
      
      processedContent = chunks.join('\n\n--- \n\n');
    } else {
      processedContent = '[No content found matching the specified keywords]';
    }
  }
  
  // Apply offset if specified
  const startOffset = options.startOffset || 0;
  if (startOffset > 0 && startOffset < processedContent.length) {
    processedContent = processedContent.substring(startOffset);
    truncated = true;
  }
  
  // Apply max length if specified (but skip if keyword filtering already handled it)
  if (!keywordFilteringApplied) {
    const maxLength = options.maxLength || 50000; // Default to 50k chars
    if (processedContent.length > maxLength) {
      processedContent = processedContent.substring(0, maxLength);
      truncated = true;
    }
  }
  
  return { 
    content: processedContent, 
    truncated, 
    totalLength,
    extractedSections,
    // Debug info for troubleshooting
    debug: options.filterKeywords ? {
      keywordCount: options.filterKeywords.length,
      originalLength: content.length,
      paragraphCount: options.filterKeywords ? content.split(/\n\s*\n/).length : 0,
      keywordFilteringApplied,
      finalLength: processedContent.length
    } : undefined
  };
}

// Convert URL content to LLM-friendly text
export async function convertUrlToText(url: string, category?: string): Promise<string> {
  if (!url?.trim()) {
    return '';
  }
  
  try {
    // Use jina for articles and PDFs, lightweight HTML parsing for others
    const shouldUseJina = !category || category === 'article' || category === 'pdf';
    
    if (shouldUseJina) {
      return await convertWithJina(url);
    } else {
      // For non-article/pdf content, we'll rely on HTML content from Readwise
      // This function is now mainly used as a fallback
      const response = await fetch(url, {
        headers: {
          'User-Agent': 'Readwise-MCP-Server/1.0.0',
          'Accept': 'text/html,application/xhtml+xml'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTML fetch failed: ${response.status}`);
      }
      
      const html = await response.text();
      return extractTextFromHtml(html);
    }
  } catch (error) {
    console.warn('Error converting URL to text:', error);
    return '[Content unavailable - conversion error]';
  }
} 