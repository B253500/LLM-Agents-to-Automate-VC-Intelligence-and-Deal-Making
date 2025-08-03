# CoreSignal API Analysis

## Executive Information Availability

**❌ CoreSignal does NOT provide executive information directly.**

The code explicitly states this limitation:
```python
# Step 2: Try CoreSignal (but CoreSignal doesn't provide executive data, so skip)
```

## What CoreSignal Actually Provides

### Company-Level Data (45 total fields available)

#### **Basic Company Information**
- `name` - Company name (e.g., "Monzo Bank")
- `id` - Company ID (e.g., 10508195)
- `description` - Company description
- `industry` - Industry classification (e.g., "Banking")
- `type` - Company status (e.g., "Privately Held")
- `founded` - Year founded (e.g., 2015)
- `size` - Employee count range (e.g., "1,001-5,000 employees")
- `employees_count` - Exact employee count (e.g., 3893)

#### **Website & Online Presence**
- `website` - Company website (e.g., "https://monzo.com")
- `url` - LinkedIn company page
- `canonical_url` - Canonical LinkedIn URL
- `logo_url` - Company logo URL

#### **Location Data**
- `headquarters_new_address` - HQ address (e.g., "London, England")
- `headquarters_country_parsed` - HQ country (e.g., "United Kingdom")
- `company_locations_collection` - All office locations

#### **Social Media & Followers**
- `followers` - LinkedIn follower count (e.g., 605618)

#### **Featured Employees Collection**
- `company_featured_employees_collection` - **This is the closest to executive data**

This field contains LinkedIn URLs of featured employees, but:
- Most entries are marked as `deleted: 1` (inactive)
- Only a few are `deleted: 0` (active)
- Contains LinkedIn profile URLs but no names or titles
- Not structured as executive data

#### **Funding & Financial Data**
- `company_funding_rounds_collection` - Funding round details
- `company_featured_investors_collection` - Investor information

#### **Company Relationships**
- `company_affiliated_collection` - Affiliated companies
- `company_similar_collection` - Similar companies
- `company_also_viewed_collection` - Companies also viewed

#### **Company Details**
- `company_specialties_collection` - Company specialties
- `company_updates_collection` - Company updates/news
- `company_crunchbase_info_collection` - Crunchbase links

## Executive Data Source

Since CoreSignal doesn't provide executive information, the system uses:

1. **PDF Extraction** - Extracts executives from pitch decks
2. **Web Search (Perplexity)** - Searches for executive information online
3. **LinkedIn Data** - Enriches executives with LinkedIn profiles

## Field Mapping in Code

The system maps CoreSignal fields to profile attributes:

```python
mapping = {
    "company_id": coresignal_data.get("id"),
    "name": coresignal_data.get("name"),
    "legal_name": coresignal_data.get("company_legal_name"),
    "description": coresignal_data.get("description"),
    "industry": coresignal_data.get("industry"),
    "domain": coresignal_data.get("website"),
    "size_range": coresignal_data.get("size"),
    "founded_year": coresignal_data.get("founded"),
    "status": coresignal_data.get("type"),
    "hq_city": coresignal_data.get("headquarters_new_address"),
    "linkedin_followers": coresignal_data.get("followers"),
    "employees_count": coresignal_data.get("employees_count"),
    # ... and many more
}
```

## Key Findings

1. **No Direct Executive Data**: CoreSignal provides company-level data, not executive-level data
2. **Featured Employees**: The only executive-related field is `company_featured_employees_collection`, but it's limited and mostly contains inactive/deleted entries
3. **Rich Company Data**: CoreSignal provides comprehensive company information including funding, locations, social media, and industry data
4. **Employee Count**: Provides exact employee count (`employees_count`) and size range (`size`)
5. **Social Media**: Provides LinkedIn follower count and company social media presence

## Conclusion

**CoreSignal is designed for company-level enrichment, not executive data extraction.** For executive information, the system relies on PDF extraction and web search rather than CoreSignal's API. 