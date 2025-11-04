import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from helpers.config import api

class FolderAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api, temperature=0)
        self.base_path = r"C:\Users\MohansaiAnde\Downloads\OneDrive_2025-10-09\Ops Bot"
        self.folder_details = self.load_folder_details()
    
    def load_folder_details(self):
        with open('helpers/detail.json', 'r') as f:
            return json.load(f)
    
    def get_folder_files(self, folder_name):
        folder_path = os.path.join(self.base_path, folder_name)
        if os.path.exists(folder_path):
            return [f for f in os.listdir(folder_path) if f.endswith(('.xlsx', '.xls', '.csv', '.docx'))]
        return []
    
    def predict_best_folder_and_file(self, user_query):
        # Create context for LLM
        folder_context = ""
        for key, folder_info in self.folder_details.items():
            # print("key:", key)
            folder_name = folder_info['foldername']
            files = self.get_folder_files(folder_name)
            sheets_info = folder_info.get('sheets', {})
            # print(sheets_info)
            # print("sheets_info:",sheets_info)
            folder_context += f"Folder: {folder_name}\nDescription: {folder_info['Detail']}\nFiles: {files}\nSheets: {sheets_info}\n\n"
        
        prompt = f"""Based on the user query and folder descriptions, predict the most relevant folder and file.

User Query: {user_query}

Available Folders and Files:
{folder_context}

Return only the folder name and most probable filename in this format:
FOLDER: [folder_name]
FILE: [filename]
sheet: [sheetname of the excel if any or return none] """
        
        response = self.llm.invoke(prompt)
        return self.parse_response(response.content)
    
    def parse_response(self, response):
        lines = response.strip().split('\n')
        folder = None
        file = None
        sheet = None
        
        for line in lines:
            if line.startswith('FOLDER:'):
                folder = line.replace('FOLDER:', '').strip()
            elif line.startswith('FILE:'):
                file = line.replace('FILE:', '').strip()
            elif line.startswith('sheet:'):
                sheet = line.replace('sheet:', '').strip()

        # print("Predicted - Folder:", folder, "File:", file, "Sheet:", sheet)
        
        return folder, file, sheet
    
    def get_file_path(self, user_query):
        folder, file,sheet = self.predict_best_folder_and_file(user_query)
        if folder and file:
            return os.path.join(self.base_path, folder, file ), sheet
        return None

# Usage
def find_best_file(user_query):
    agent = FolderAgent()
    
    user_query=user_query
    print("user_query:", user_query)
    return agent.get_file_path(user_query)
if __name__ == "__main__":
    query = input("Enter your query: ")
    best_file = find_best_file(query)
    print(f"Best file for the query: {best_file}")