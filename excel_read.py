#Enhanced version with better data handling and conversation history
import pandas as pd
import google.generativeai as genai
import os

class ExcelAnalyzer:
    def __init__(self, api_key):
        """Initialize the Excel Analyzer with Gemini AI"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.df = None
        self.sheet_info = {}
        self.conversation_history = []
        self.current_file_path = None
    
    def load_excel_file(self, file_path):
        """Load Excel file and analyze its structure"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Store current file path
        self.current_file_path = file_path
        
        # Read all sheets
        all_sheets = pd.read_excel(file_path, sheet_name=None)
        
        print("Available sheets:")
        for sheet_name, sheet_df in all_sheets.items():
            print(f"- {sheet_name}: {sheet_df.shape[0]} rows, {sheet_df.shape[1]} columns")
            self.sheet_info[sheet_name] = {
                'rows': sheet_df.shape[0],
                'columns': sheet_df.columns.tolist()
            }
        
        # Combine all sheets
        self.df = pd.concat(all_sheets.values(), ignore_index=True)
        
        print(f"\nCombined DataFrame: {self.df.shape[0]} rows, {self.df.shape[1]} columns")
        return self.df
    
    def get_data_summary(self):
        """Get a summary of the loaded data"""
        if self.df is None:
            return "No data loaded"
        
        summary = []
        summary.append(f"Total rows: {len(self.df)}")
        summary.append(f"Total columns: {len(self.df.columns)}")
        summary.append(f"Columns: {', '.join(self.df.columns.tolist())}")
        summary.append(f"Sheets processed: {len(self.sheet_info)}")
        
        return "\n".join(summary)
    
    def add_to_history(self, query, response):
        """Add query and response to conversation history"""
        self.conversation_history.append({
            'query': query,
            'response': response
        })
        # Keep only last 5 exchanges to avoid token limits
        if len(self.conversation_history) > 5:
            self.conversation_history = self.conversation_history[-5:]
    
    def get_conversation_context(self):
        """Get formatted conversation history"""
        if not self.conversation_history:
            return ""
        
        context = "\nPrevious conversation:\n"
        for i, exchange in enumerate(self.conversation_history, 1):
            context += f"Q{i}: {exchange['query']}\n"
            # Keep full response for better context, but limit very long responses
            response_text = exchange['response']
            if len(response_text) > 800:
                response_text = response_text[:800] + "..."
            context += f"A{i}: {response_text}\n\n"
        
        return context
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("✅ Conversation history cleared!")
    
    def show_history(self):
        """Display conversation history"""
        if not self.conversation_history:
            print("📝 No conversation history yet.")
            return
        
        print("\n📜 Conversation History:")
        print("="*60)
        for i, exchange in enumerate(self.conversation_history, 1):
            print(f"Q{i}: {exchange['query']}")
            print(f"A{i}: {exchange['response'][:300]}{'...' if len(exchange['response']) > 300 else ''}")
            print("-" * 60)
    
    def process_query(self, query):
        """Process user query with intelligent data sampling and conversation context"""
        if self.df is None:
            return "No data loaded. Please load an Excel file first."
        
        # Get conversation history
        conversation_context = self.get_conversation_context()
        
        # Simple but effective follow-up detection
        follow_up_indicators = [
            'from the above', 'from above', 'above', 'from that', 'from it',
            'get the', 'show me the', 'extract the', 'find the',
            'tell me more', 'more about', 'details about', 'explain that',
            'what about', 'about that', 'that person', 'his details', 'her details'
        ]
        
        is_follow_up = any(indicator in query.lower() for indicator in follow_up_indicators)
        
        # Additional check: if conversation exists and query is short and references something
        if conversation_context and len(query.split()) <= 10:
            reference_words = ['that', 'it', 'this', 'above', 'previous', 'earlier']
            if any(word in query.lower() for word in reference_words):
                is_follow_up = True
        
        print(f"🔍 Debug - Query: '{query}'")
        print(f"🔍 Debug - Has conversation history: {bool(conversation_context)}")
        print(f"🔍 Debug - Detected as follow-up: {is_follow_up}")
        
        if is_follow_up and conversation_context:
            print("📝 Processing as FOLLOW-UP question...")
            # For follow-up questions, focus on conversation history
            prompt = f"""
            Previous conversation history:
            {conversation_context}
            
            User's follow-up question: {query}
            
            INSTRUCTIONS:
            - This is a follow-up question about the previous conversation
            - Look ONLY at the conversation history above
            - Extract or clarify information from previous responses
            - Do NOT analyze any new Excel data
            - If asking for specific person's details, find them in the previous responses
            
            Provide the requested information based solely on the conversation history.
            """
        else:
            print("📊 Processing as NEW data analysis question...")
            # For new questions, include data context
            sample_size = min(50, len(self.df))
            sample_df = self.df.head(sample_size)
            
            context_parts = [
                f"Data Summary: {len(self.df)} total rows, showing first {sample_size}",
                f"Columns: {', '.join(self.df.columns.tolist())}",
                f"Sheet Information: {list(self.sheet_info.keys())}",
                f"\nSample Data:\n{sample_df.to_string()}"
            ]
            
            prompt = f"""
            You are analyzing Excel data. Here's the context:
            
            {chr(10).join(context_parts)}
            
            {conversation_context}
            
            Current User Question: {query}
            
            Please provide a comprehensive answer based on the data. Include:
            1. Direct answer to the question
            2. Relevant statistics or insights
            3. Any notable patterns or observations
            
            Format your response clearly and concisely.
            """
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Add to conversation history
            self.add_to_history(query, response_text)
            
            return response_text
        except Exception as e:
            return f"Error processing query: {str(e)}"

# Usage
def main():
    # Initialize analyzer
    analyzer = ExcelAnalyzer('AIzaSyBvBnlgt1z0JUG7mW-qCOwT4MMOaUSjrao')
    
    # Load file
    file_path = "C:\Users\MohansaiAnde\Downloads\OneDrive_2025-10-09\Ops Bot/Account Details/Platform, App & Infra.xlsx"
    
    try:
        analyzer.load_excel_file(file_path)
        print("\n" + "="*50)
        print("EXCEL ANALYZER READY")
        print("="*50)
        print(analyzer.get_data_summary())
        print("="*50)
        
        # Interactive loop
        while True:
            user_query = input("\n🔍 Enter your question (or 'quit'/'help'): ")
            
            if user_query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            elif user_query.lower() == 'help':
                print("""
                📋 Available commands:
                - Ask any question about your data
                - 'summary' - Show data summary
                - 'columns' - List all columns
                - 'history' - Show conversation history
                - 'clear' - Clear conversation history
                - 'help' - Show this help
                - 'quit' - Exit the program
                
                💡 Example questions:
                - "How many records are there?"
                - "What are the unique values in column X?"
                - "Show me statistics for numerical columns"
                - "What patterns do you see in this data?"
                - "Can you explain that in more detail?" (follow-up)
                - "What about the previous point you mentioned?" (follow-up)
                """)
            elif user_query.lower() == 'summary':
                print(analyzer.get_data_summary())
            elif user_query.lower() == 'columns':
                print("Columns:", ', '.join(analyzer.df.columns.tolist()))
            elif user_query.lower() == 'history':
                analyzer.show_history()
            elif user_query.lower() == 'clear':
                analyzer.clear_history()
            elif user_query.strip():
                print("🤔 Processing your query...")
                answer = analyzer.process_query(user_query)
                print(f"\n📊 Answer:\n{answer}")
            else:
                print("❓ Please enter a valid question or command.")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()