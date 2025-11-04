import pandas as pd
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
import sqlite3
import os

class ExcelSQLAgent:
    def __init__(self, df, gemini_api_key):
        self.df = df
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=gemini_api_key, temperature=0)
        self.headers = []
        self.db_path = "temp_excel.db"
        
    def extract_headers(self):
        """Extract headers from Excel sheet"""
        # df = pd.read_excel(self.excel_path)
        df=self.df
        self.headers = df.columns.tolist()
        return self.headers
    
    def create_temp_db(self):
        """Create temporary SQLite database from Excel"""
        # df = pd.read_excel(self.excel_path)
        df=self.df
        conn = sqlite3.connect(self.db_path)
        df.to_sql('data_table', conn, if_exists='replace', index=False)
        conn.close()
        
    def setup_sql_agent(self):
        """Setup LangChain SQL agent"""
        db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")
        
        # Custom prefix to prevent automatic LIMIT clauses
        custom_prefix = """You are a SQL query assistant. When generating SQL queries:
- Do NOT add LIMIT clauses unless the user explicitly asks for a limited number of results
- Return all matching rows by default
- Only use LIMIT when the user specifically mentions words like 'top', 'first', 'limit', or specifies a number of results

You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct sqlite query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 10 results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the below tools. Only use the information returned by the below tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

If the question does not seem related to the database, just return "I don't know" as the answer.
Note: Generate the output in tabular html format for the feasible data  generated in the response"""
        
        self.agent = create_sql_agent(
            llm=self.llm,
            db=db,
            verbose=True,
            agent_type="openai-tools",
            prefix=custom_prefix,
            max_execution_time = 1800,
        )
        
    def query(self, natural_language_query):
        """Process natural language query and return results"""
        self.extract_headers()
        self.create_temp_db()
        self.setup_sql_agent()
        
        # Add context about available columns
        enhanced_query = f"Available columns: {', '.join(self.headers)}. Query: {natural_language_query}"
        
        try:
            result = self.agent.invoke({"input": enhanced_query})
            return result
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            # Cleanup
            try:
                if os.path.exists(self.db_path):
                    os.remove(self.db_path)
            except:
                pass

# Usage example
# def process_excel_query(excel_file_path, user_query, gemini_api_key):
def process_excel_query(df, user_query, gemini_api_key):
    agent = ExcelSQLAgent(df, gemini_api_key)
    return agent.query(user_query)