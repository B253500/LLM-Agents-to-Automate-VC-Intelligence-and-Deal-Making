from main import save_memo_with_template
from types import SimpleNamespace

# Dummy profile for testing
test_profile = SimpleNamespace(name="TestCompany")

# Sample memo text with section headers and body
test_memo_text = """1. DETAILED SUMMARY
This is a summary of the company.

2. COMPANY OVERVIEW
Company: TestCompany
Website: https://testcompany.com

Key Weaknesses
- No financial data

Opportunities
- Large market

3. PROBLEM STATEMENT
The problem is...

4. SOLUTION OVERVIEW
The solution is...
"""

output_path = "out/test_template_output.docx"
save_memo_with_template(test_memo_text, test_profile, output_path)
print(f"Test DOCX generated at {output_path}") 