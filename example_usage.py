from excel_sql_agent import process_excel_query
from helpers.config import api
import os

# Example usage
if __name__ == "__main__":
    # Set your Gemini API key
    api_key = api
    
    # Path to your Excel file
    excel_file = r"C:\Users\HariVardhanaShubhash\Downloads\OneDrive_2025-10-09 1\Ops Bot\Account Details\Platform, App & Infra.xlsx"
    
    # Natural language queries
    queries = [
        "List all the employees who are under Platform, App & Infra TSC.Note: Don't use any limit , Do generate the data in Json Format ",
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        result = process_excel_query(excel_file, query, api_key)
        # print(f"Result: {result['output']}")
        print("Result:", result['output'] if isinstance(result, dict) and 'output' in result else result)