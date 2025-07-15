from main import enrich_executive_details_with_perplexity

if __name__ == "__main__":
    company_name = "StoreDot"
    executives = [
        {"name": "Doron Myersdorf", "role": "CEO"}
    ]
    enriched = enrich_executive_details_with_perplexity(company_name, executives)
    print(enriched) 