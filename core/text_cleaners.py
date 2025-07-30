"""
Text cleaning utilities for memo generation.
Extracted from main.py to improve code organization.
"""

import re
from typing import List


def clean_think_tags_and_debugging(text: str) -> str:
    """Comprehensive cleaning function to remove all think tags and debugging sentences."""
    if not isinstance(text, str):
        return text
    
    # Remove <think> tags and their content (handle nested tags)
    # First, remove all <think> and </think> tags completely
    text = re.sub(r'<think>', '', text)
    text = re.sub(r'</think>', '', text)
    
    # Remove thinking process markers (comprehensive list)
    thinking_patterns = [
        r'(Okay, so I need to figure out|First, from the|Looking at the|Based on the|From the search results|Let me start by|I need to analyze|Let me examine).*?(?=\n|$)',
        r'(Let me look through|I need to look through|Looking at result|Result mentions|First, result|Result from|Based on result).*?(?=\n|$)',
        r'(The user wants|The user asked|The user is asking|The query is about).*?(?=\n|$)',
        r'(I need to answer|I need to tackle|Let me tackle|Let me answer).*?(?=\n|$)',
        r'(Okay, let\'s tackle|Let\'s tackle|Let me tackle).*?(?=\n|$)',
        r'(The user wants me to|The user wants to know|The user is looking for).*?(?=\n|$)',
        r'(I should look|I need to look|Let me look).*?(?=\n|$)',
        r'(Based on the provided|Based on the search|From the search).*?(?=\n|$)',
        r'(Financial Research Summary for|Company:).*?(?=\n|$)',
        r'(First, looking at|Looking at result|Result mentions|First, result).*?(?=\n|$)',
        r'(Wait, but|Wait, the|Wait, that\'s|Wait, no).*?(?=\n|$)',
        r'(Hmm,|Hmm.|Hmm, but|Hmm, that\'s).*?(?=\n|$)',
        r'(So, putting this together|Putting this together).*?(?=\n|$)',
        r'(Need to check|Need to verify|Need to confirm).*?(?=\n|$)',
        r'(However,|However, the|However, there\'s).*?(?=\n|$)',
        r'(But wait,|But wait.|But wait, the).*?(?=\n|$)',
        r'(Maybe the|Maybe there\'s|Maybe it\'s).*?(?=\n|$)',
        r'(It\'s possible that|It\'s likely that).*?(?=\n|$)',
        r'(Without more|Without additional).*?(?=\n|$)',
        r'(The user might need|The user should know).*?(?=\n|$)',
        # Add more patterns for <think> sentences
        r'(<think>.*?</think>)',
        r'(Okay, I need to figure out.*?)(?=\n|$)',
        r'(Let me start by.*?)(?=\n|$)',
        r'(Based on the search results.*?)(?=\n|$)',
        r'(Looking at the data.*?)(?=\n|$)',
        r'(From the information provided.*?)(?=\n|$)',
        r'(I need to analyze.*?)(?=\n|$)',
        r'(Let me examine.*?)(?=\n|$)',
    ]
    
    for pattern in thinking_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL)
    
    # Remove numbered analysis that's part of thinking process
    text = re.sub(r'^\d+\.\s*[A-Z].*?(?=\n|$)', '', text, flags=re.MULTILINE)
    
    # Remove citation markers
    text = re.sub(r'\[\d+\]', '', text)
    
    # Remove hashtags and markdown formatting that might be artifacts
    text = re.sub(r'#+\s*[A-Za-z\s]+', '', text)
    
    # Remove standalone bullet points that don't have content
    text = re.sub(r'^\s*•\s*$', '', text, flags=re.MULTILINE)
    
    # Remove bullet points at the beginning of lines that are followed by whitespace
    text = re.sub(r'^\s*•\s+(?=\s|$)', '', text, flags=re.MULTILINE)
    
    # Remove lines that are just debugging markers
    text = re.sub(r'^\s*(Sources:|Source:|Sources|Source)\s*$', '', text, flags=re.MULTILINE)
    
    # Remove empty tables (lines with just | | |)
    text = re.sub(r'^\s*\|\s*\|\s*\|\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\|\s*Metric\s*\|\s*Value\s*\|\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\|\s*--------\s*\|\s*-------\s*\|\s*$', '', text, flags=re.MULTILINE)
    
    # Clean up extra whitespace and newlines
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()
    
    return text


def clean_blank_bullets(text: str) -> str:
    """Remove blank bullet points and redundant elements from text."""
    lines = text.split('\n')
    cleaned = []
    for i, line in enumerate(lines):
        # Removing lines that are just a bullet or a bullet with whitespace
        if line.strip() in ['•', '-', '*']:
            # Also skipping if the next line is blank or whitespace
            if i + 1 < len(lines) and not lines[i + 1].strip():
                continue
            # Or if it's the last line
            if i + 1 == len(lines):
                continue
            # Or if it's followed by another bullet point
            if i + 1 < len(lines) and lines[i + 1].strip() in ['•', '-', '*']:
                continue
        cleaned.append(line)
    
    # Removing trailing bullet points and redundant elements
    result = '\n'.join(cleaned)
    result = re.sub(r'\n\s*•\s*$', '', result, flags=re.MULTILINE)  # Remove trailing bullet point
    result = re.sub(r'\n\s*-\s*$', '', result, flags=re.MULTILINE)   # Remove trailing dash
    result = re.sub(r'\n\s*\*\s*$', '', result, flags=re.MULTILINE)  # Remove trailing asterisk
    
    # Removing multiple consecutive blank lines at the end
    result = re.sub(r'\n\s*\n\s*$', '\n', result, flags=re.MULTILINE)
    
    # Removing any trailing whitespace
    result = result.rstrip()
    
    return result


def clean_discussion_section(discussion: str) -> str:
    """Clean discussion section by removing redundant elements."""
    lines = discussion.split('\n')
    cleaned = []
    conclusion_found = False
    
    for i, line in enumerate(lines):
        # Check if we've reached the conclusion
        if 'conclusion:' in line.lower():
            conclusion_found = True
        
        # If we're after the conclusion, be more aggressive about removing bullets
        if conclusion_found:
            # Remove any standalone bullet points after conclusion
            if line.strip() in ['•', '-', '*']:
                continue
            # Remove bullet points that are the last content before the footer
            if line.strip() in ['•', '-', '*'] and i == len(lines) - 2:  # Second to last line
                continue
        
        # Normal cleaning for lines before conclusion
        if not conclusion_found and line.strip() in ['•', '-', '*', '']:
            continue
        
        # Removing leading bullet from the first non-empty line
        if cleaned == [] and line.strip().startswith('•'):
            line = line.lstrip('•').strip()
        
        cleaned.append(line)
    
    # Removing redundant conclusion at the bottom
    result = '\n'.join(cleaned)
    
    # Removing the redundant "Conclusion:" line at the bottom
    result = re.sub(r'\n\s*Conclusion:\s*\n\s*Based on the analysis above, this investment opportunity presents both significant potential and notable risks that require careful consideration\.\s*$', '', result, flags=re.MULTILINE)
    
    # Remove any bullet points that appear after "Conclusion:" 
    result = re.sub(r'(Conclusion:.*?)(\n\s*•\s*)+', r'\1', result, flags=re.MULTILINE | re.DOTALL)
    
    # Remove any standalone bullet points at the very end (before footer)
    result = re.sub(r'\n\s*•\s*\n\s*Generated by', '\n\nGenerated by', result, flags=re.MULTILINE)
    
    # Removing trailing bullet points and redundant elements - MORE AGGRESSIVE CLEANING
    result = re.sub(r'\n\s*•\s*$', '', result, flags=re.MULTILINE)  # Remove trailing bullet point
    result = re.sub(r'\n\s*-\s*$', '', result, flags=re.MULTILINE)   # Remove trailing dash
    result = re.sub(r'\n\s*\*\s*$', '', result, flags=re.MULTILINE)  # Remove trailing asterisk
    
    # Remove any standalone bullet points at the end
    result = re.sub(r'\n\s*•\s*\n\s*$', '\n', result, flags=re.MULTILINE)
    result = re.sub(r'\n\s*•\s*$', '', result, flags=re.MULTILINE)
    
    # Removing multiple consecutive blank lines at the end
    result = re.sub(r'\n\s*\n\s*$', '\n', result, flags=re.MULTILINE)
    
    # Removing any trailing whitespace
    result = result.rstrip()
    
    return result


def deduplicate_memo(text: str) -> str:
    """De-duplication post-processing for memo text."""
    lines = text.split('\n')
    seen = set()
    result = []
    for line in lines:
        l = line.strip()
        if l and l not in seen:
            result.append(line)
            seen.add(l)
        elif l and len(l) > 30 and not any(l in r for r in result):
            result.append(line)
    
    # Applying additional cleaning to remove redundant elements
    result_text = '\n'.join(result)
    result_text = clean_blank_bullets(result_text)
    
    return result_text


def clean(text: str) -> str:
    """Clean up text by removing hashtags, special markers, and normalizing formatting."""
    if not isinstance(text, str):
        return text
    # Removing hashtags only
    text = re.sub(r'#+\s*[A-Za-z\s]+', '', text)
    # Removing extra whitespace and normalising line breaks
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    return text.strip() 