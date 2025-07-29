"""
Custom Business Model Diagram Generator
Creates simple, revenue-focused Mermaid diagrams for VC memos
"""

def generate_simple_revenue_diagram(company_name: str, revenue_streams: list, customer_segments: list) -> str:
    """
    Generate a simple, revenue-focused business model diagram
    
    Args:
        company_name: Name of the company
        revenue_streams: List of revenue streams (e.g., ["Direct Sales", "Licensing", "Partnerships"])
        customer_segments: List of customer segments (e.g., ["Automotive Manufacturers", "Battery Manufacturers"])
    
    Returns:
        Mermaid diagram code
    """
    
    # Clean and validate inputs
    company_name = company_name.replace(" ", "_").replace("-", "_")
    revenue_streams = [rs.replace(" ", "_").replace("-", "_") for rs in revenue_streams[:3]]  # Limit to 3
    customer_segments = [cs.replace(" ", "_").replace("-", "_") for cs in customer_segments[:3]]  # Limit to 3
    
    # Generate the diagram
    diagram_lines = [
        "graph TD;",
        f"    A[{company_name}] -->|Generates| B[Revenue_Streams];",
    ]
    
    # Add revenue streams
    for i, rs in enumerate(revenue_streams):
        diagram_lines.append(f"    B -->|{rs}| C{i+1}[{rs}];")
    
    # Add customer segments
    for i, cs in enumerate(customer_segments):
        diagram_lines.append(f"    C{i+1} -->|Serves| D{i+1}[{cs}];")
    
    return "\n".join(diagram_lines)

def generate_storedot_diagram() -> str:
    """Generate a simple diagram for StoreDot"""
    return generate_simple_revenue_diagram(
        company_name="StoreDot",
        revenue_streams=["Direct_Sales", "Licensing", "Partnerships"],
        customer_segments=["Automotive_Manufacturers", "Battery_Manufacturers", "Technology_Companies"]
    )

def generate_generic_tech_diagram() -> str:
    """Generate a simple diagram for generic tech companies"""
    return generate_simple_revenue_diagram(
        company_name="Tech_Company",
        revenue_streams=["SaaS_Subscriptions", "Licensing", "Consulting"],
        customer_segments=["Enterprise_Customers", "SMB_Customers", "Partners"]
    )

def generate_fintech_diagram() -> str:
    """Generate a simple diagram for fintech companies"""
    return generate_simple_revenue_diagram(
        company_name="FinTech_Company",
        revenue_streams=["Transaction_Fees", "Subscription_Fees", "Data_Services"],
        customer_segments=["Banks", "Merchants", "Consumers"]
    )

def generate_healthtech_diagram() -> str:
    """Generate a simple diagram for healthtech companies"""
    return generate_simple_revenue_diagram(
        company_name="HealthTech_Company",
        revenue_streams=["Software_Licenses", "Data_Analytics", "Clinical_Services"],
        customer_segments=["Hospitals", "Pharmaceutical_Companies", "Research_Institutions"]
    )

# Example usage
if __name__ == "__main__":
    print("🔧 Custom Business Model Diagram Generator")
    print("=" * 50)
    
    # Generate StoreDot diagram
    print("\n📊 StoreDot Business Model:")
    storedot_diagram = generate_storedot_diagram()
    print(storedot_diagram)
    
    print("\n" + "=" * 50)
    
    # Generate generic tech diagram
    print("\n📊 Generic Tech Company:")
    tech_diagram = generate_generic_tech_diagram()
    print(tech_diagram)
    
    print("\n" + "=" * 50)
    
    # Generate fintech diagram
    print("\n📊 FinTech Company:")
    fintech_diagram = generate_fintech_diagram()
    print(fintech_diagram)
    
    print("\n" + "=" * 50)
    
    # Generate healthtech diagram
    print("\n📊 HealthTech Company:")
    healthtech_diagram = generate_healthtech_diagram()
    print(healthtech_diagram)
    
    print("\n✅ All diagrams generated successfully!")
    print("💡 These diagrams are much simpler and focus on revenue streams.") 