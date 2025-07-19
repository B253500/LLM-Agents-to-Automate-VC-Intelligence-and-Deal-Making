import os
from datetime import datetime

def test_memo_saving():
    # Simulate merged agent outputs (mocked, no LLM calls)
    profile_dict = {
        "company_name": "TestCompany",
        "sector": "Battery Tech",
        "business_model": "Licensing",
        # ... add other fields as needed ...
    }
    company_name = profile_dict.get("company_name", "UnknownCompany")
    date_str = datetime.now().strftime("%Y%m%d")
    print(f"[DEBUG] company_name before filename: {company_name} (type: {type(company_name)})")
    if not company_name or not isinstance(company_name, str):
        company_name = 'UnknownCompany'
    docx_filename = f"memo_{company_name.replace(' ', '_')}_{date_str}.docx"
    print(f"[INFO] Memo would be generated and saved as: {docx_filename}")
    # Optionally, test file creation (mocked)
    # with open(docx_filename, 'w') as f:
    #     f.write("This is a test memo.")
    # print(f"[INFO] Test memo file created: {docx_filename}")

if __name__ == "__main__":
    test_memo_saving() 