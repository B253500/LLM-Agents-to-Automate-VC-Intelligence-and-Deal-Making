"""
Gemini utilities for faster web searches, optimized for team section enrichment.
"""

import os
import re
from typing import Optional, Dict, Any
from google.generativeai import GenerativeModel
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = GenerativeModel('gemini-1.5-flash')

def search_gemini(query: str, max_results: int = 3, evaluator=None, section_name="unknown", agent_name="unknown") -> Optional[str]:
    """
    Use Gemini for web search with faster response times.
    Optimized for team section queries like LinkedIn profiles and executive bios.
    """
    try:
        # Add web search instruction to the query
        search_query = f"Search the web for: {query}. Return only factual information, no explanations."
        
        response = model.generate_content(search_query)
        
        if response and response.text:
            # Clean up the response
            cleaned_result = response.text.strip()
            
            # Track token usage if evaluator is provided
            if evaluator:
                from core.llm_utils import track_web_search_tokens
                track_web_search_tokens(query, cleaned_result, "gemini", section_name, agent_name, evaluator)
            
            # Remove common AI thinking patterns
            thinking_patterns = [
                r'<think>.*?</think>',
                r'Okay, let me.*?\.',
                r'Let me search.*?\.',
                r'Based on.*?\.',
                r'According to.*?\.',
                r'I found.*?\.',
                r'Here is.*?\.',
                r'The search.*?\.',
                r'Looking at.*?\.',
                r'From the search.*?\.'
            ]
            
            for pattern in thinking_patterns:
                cleaned_result = re.sub(pattern, '', cleaned_result, flags=re.DOTALL | re.IGNORECASE)
            
            # Clean up extra whitespace
            cleaned_result = re.sub(r'\n\s*\n', '\n', cleaned_result)
            cleaned_result = cleaned_result.strip()
            
            return cleaned_result if len(cleaned_result) > 20 else None
            
    except Exception as e:
        print(f"[Gemini] Search error: {e}")
        return None

def find_linkedin_profile_gemini(name: str, company_name: str = None) -> Optional[str]:
    """
    Find LinkedIn profile URL using Gemini (faster than Perplexity).
    """
    query = f"LinkedIn profile URL for {name}"
    if company_name:
        query += f" at {company_name}"
    
    result = search_gemini(query)
    
    if result:
        # Extract LinkedIn URL with flexible patterns
        linkedin_patterns = [
            r'https?://[\w./-]*linkedin\.com/in/[\w/_-]+',
            r'https://www\.linkedin\.com/in/[\w/_-]+',
            r'https://linkedin\.com/in/[\w/_-]+',
            r'linkedin\.com/in/[\w/_-]+'
        ]
        
        for pattern in linkedin_patterns:
            match = re.search(pattern, result)
            if match:
                linkedin_url = match.group(0)
                # Ensure it starts with https://
                if linkedin_url.startswith('linkedin.com'):
                    linkedin_url = 'https://' + linkedin_url
                # Clean up any trailing characters
                linkedin_url = re.sub(r'[^\w/._-]+$', '', linkedin_url)
                return linkedin_url
    
    return None

def get_executive_bio_gemini(name: str, role: str, company_name: str) -> Optional[str]:
    """
    Generate executive bio using Gemini (faster than Perplexity).
    """
    query = f"Professional background and bio for {name}, {role} at {company_name}. Include past roles and achievements."
    
    result = search_gemini(query)
    
    if result and len(result.split()) > 8:
        # Clean up the bio - remove AI thinking text
        bio = result.strip()
        
        # Remove common AI thinking patterns
        thinking_patterns = [
            r'<think>.*?</think>',
            r'Okay, let me.*?\.',
            r'Let me analyze.*?\.',
            r'Based on.*?\.',
            r'According to.*?\.',
            r'First, looking at.*?\.',
            r'Now, putting this together.*?\.',
            r'I need to.*?\.',
            r'Let me start by.*?\.',
            r'Okay, I need to.*?\.',
            r'Let\'s tackle this.*?\.',
            r'Let me.*?\.',
            r'First,.*?\.',
            r'Now,.*?\.'
        ]
        
        for pattern in thinking_patterns:
            bio = re.sub(pattern, '', bio, flags=re.DOTALL | re.IGNORECASE)
        
        bio = bio.strip()
        
        # If bio is now too short, skip it
        if len(bio.split()) < 5:
            return None
            
        return bio
    
    return None

def get_executive_background_gemini(name: str, role: str, company_name: str) -> Optional[str]:
    """
    Get executive background summary using Gemini (faster than Perplexity).
    """
    query = f"Professional background summary for {name}, {role} at {company_name}. Include key achievements and experience."
    
    result = search_gemini(query)
    
    if result and len(result.split()) > 10:
        # Clean up the background
        background = result.strip()
        
        # Remove common AI thinking patterns
        thinking_patterns = [
            r'<think>.*?</think>',
            r'Okay, let me.*?\.',
            r'Let me search.*?\.',
            r'Based on.*?\.',
            r'According to.*?\.',
            r'I found.*?\.',
            r'Here is.*?\.',
            r'The search.*?\.',
            r'Looking at.*?\.',
            r'From the search.*?\.'
        ]
        
        for pattern in thinking_patterns:
            background = re.sub(pattern, '', background, flags=re.DOTALL | re.IGNORECASE)
        
        background = background.strip()
        
        # If background is now too short, skip it
        if len(background.split()) < 8:
            return None
            
        return background
    
    return None 