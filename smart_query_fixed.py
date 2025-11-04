from folder_agent import find_best_file
from excel_sql_agent import process_excel_query
from word_image_extractor import process_word_images
from google import generativeai as genai
from helpers.config import api
import pandas as pd

# Global conversation storage (in production, use Redis or database)
conversation_sessions = {}

def get_conversation_history(session_id="default"):
    """Get conversation history for a session"""
    return conversation_sessions.get(session_id, [])

def add_to_conversation_history(session_id, query, response):
    """Add query and response to conversation history"""
    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = []
    
    conversation_sessions[session_id].append({
        'query': query,
        'response': response
    })
    
    # Keep only last 5 exchanges to avoid memory issues
    if len(conversation_sessions[session_id]) > 5:
        conversation_sessions[session_id] = conversation_sessions[session_id][-5:]

def clear_conversation_history(session_id="default"):
    """Clear conversation history for a session"""
    if session_id in conversation_sessions:
        del conversation_sessions[session_id]

def is_follow_up_query(query, session_id="default"):
    """Check if this is a follow-up query"""
    history = get_conversation_history(session_id)
    print(f"🔍 Debug - History exists: {bool(history)}")
    print(f"🔍 Debug - Query: '{query}'")
    
    if not history:
        print(f"🔍 Debug - No history, definitely NEW query")
        return False
    
    # Step 1: Check for explicit follow-up indicators
    explicit_follow_up_indicators = [
        'from the above', 'from above', 'above response', 'previous response',
        'from that response', 'from the response', 'from it', 'from that',
        'tell me more', 'more about that', 'details about that', 'explain that',
        'what about that', 'about that', 'that person', 'his details', 'her details',
        'more details about', 'elaborate on that', 'expand on that'
    ]
    
    is_explicit_follow_up = any(indicator in query.lower() for indicator in explicit_follow_up_indicators)
    print(f"🔍 Debug - Explicit follow-up indicators match: {is_explicit_follow_up}")
    
    if is_explicit_follow_up:
        print(f"🔍 Debug - Explicit follow-up detected, returning TRUE")
        return True
    
    # Step 2: Check for "get X details" pattern with specific context
    get_details_pattern = False
    if ('get' in query.lower() and 'details' in query.lower()) or ('show' in query.lower() and any(word in query.lower() for word in ['details', 'info', 'information'])):
        # Check if query mentions a specific person/item name that might be from previous response
        query_words = query.lower().split()
        # Look for capitalized words or names in the query (but exclude common action words)
        original_words = query.split()
        action_words = ['Show', 'Get', 'Find', 'List', 'Display', 'Retrieve', 'Give', 'Provide']
        has_specific_name = any(word[0].isupper() and len(word) > 3 and word not in action_words for word in original_words)
        
        # Also check if it's asking for specific person details (not general data)
        person_indicators = ['name', 'details', 'info', 'information']
        has_person_context = any(indicator in query.lower() for indicator in person_indicators)
        
        # Only consider it a "get details" pattern if:
        # 1. Has a specific name (not action words)
        # 2. Asking for personal details (not general data like "certification tracking")
        if has_specific_name and has_person_context and 'tracking' not in query.lower() and 'report' not in query.lower():
            get_details_pattern = True
            print(f"🔍 Debug - Get details pattern with specific name detected: {get_details_pattern}")
        else:
            print(f"🔍 Debug - Get details pattern NOT detected - this appears to be a general data request")
    
    # Step 3: Check for very short reference queries (1-3 words with pronouns)
    reference_follow_up = False
    query_words = query.lower().split()
    if len(query_words) <= 3:
        reference_words = ['that', 'it', 'this', 'those', 'these']
        reference_follow_up = any(word in query_words for word in reference_words)
        print(f"🔍 Debug - Very short reference query: {reference_follow_up}")
    
    # Step 4: Check if it's clearly a NEW query (override follow-up detection)
    new_query_actions = [
        'show me all', 'get all', 'find all', 'list all', 'display all'
    ]
    
    has_clear_new_action = any(action in query.lower() for action in new_query_actions)
    
    if has_clear_new_action:
        print(f"🔍 Debug - Clear new action detected, forcing NEW query: {has_clear_new_action}")
        return False
    
    # Step 5: Check if the query mentions someone/something from the previous response
    context_match = False
    if history:
        try:
            last_response = history[-1]['response']
            # Ensure the response is a string
            if isinstance(last_response, dict):
                # If it's a dict, try to get the text content
                last_response = str(last_response.get('output', '') or last_response.get('text', '') or str(last_response))
            elif not isinstance(last_response, str):
                last_response = str(last_response)
            
            last_response_lower = last_response.lower()
            query_words = query.split()
            
            # Look for proper names (capitalized words) in the query
            proper_names = [word for word in query_words if word[0].isupper() and len(word) > 2]
            
            if proper_names:
                # Check if any of the proper names appear in the last response
                for name in proper_names:
                    if name.lower() in last_response_lower:
                        context_match = True
                        print(f"🔍 Debug - Found '{name}' from query in previous response")
                        break
        except Exception as e:
            print(f"🔍 Debug - Error checking context match: {e}")
            context_match = False
    
    # Step 6: Check for broad data requests (likely new queries) - but only if no context match
    broad_data_requests = [
        'account details', 'all accounts', 'account data',
        'report data', 'all reports', 'monthly report',
        'certification data', 'all certifications'
    ]
    
    has_broad_request = any(request in query.lower() for request in broad_data_requests)
    
    if has_broad_request and not (get_details_pattern or reference_follow_up or context_match):
        print(f"🔍 Debug - Broad data request detected, forcing NEW query: {has_broad_request}")
        return False
    
    # Final decision
    is_follow_up = get_details_pattern or reference_follow_up or context_match
    
    print(f"🔍 Debug - Final follow-up decision: {is_follow_up}")
    return is_follow_up

def process_follow_up_query(query, session_id="default"):
    """Process a follow-up query using conversation history"""
    history = get_conversation_history(session_id)
    
    # Format conversation history with increased limits for follow-ups
    conversation_context = ""
    for i, exchange in enumerate(history, 1):
        conversation_context += f"Q{i}: {exchange['query']}\n"
        # Keep substantial context but limit very long responses
        response_text = exchange['response']
        if isinstance(response_text, dict):
            response_text = str(response_text.get('output', '') or response_text.get('text', '') or str(response_text))
        elif not isinstance(response_text, str):
            response_text = str(response_text)
        
        # For follow-ups, keep much more context (up to 8000 chars per response)
        if len(response_text) > 8000:
            response_text = response_text[:8000] + "..."
        conversation_context += f"A{i}: {response_text}\n\n"
    
    print(f"🔍 Debug - Conversation context length: {len(conversation_context)} chars")
    print(f"🔍 Debug - Preserving full context for better extraction")
    
    # Extract the person's name from the query for better targeting
    query_words = query.split()
    proper_names = [word for word in query_words if word[0].isupper() and len(word) > 2]
    target_name = " ".join(proper_names) if proper_names else ""
    
    print(f"🔍 Debug - Target name extracted: '{target_name}'")
    
    # Configure Gemini
    genai.configure(api_key=api)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Enhanced prompt with specific name targeting
    prompt = f"""
    Previous conversation history (COMPLETE):
    {conversation_context}
    
    User's follow-up question: {query}
    Target person: {target_name}
    
    INSTRUCTIONS:
    - Search through the ENTIRE conversation history above for "{target_name}"
    - The data might be in HTML table format or plain text
    - Look carefully through all the data - the person might be listed anywhere in the response
    - Extract ALL available information about this specific person
    - If you find the person's information, provide it in a clear, formatted way
    - Include all details available (Employee ID, certifications, dates, status, etc.)
    - Focus specifically on: {target_name}
    
    Search the complete conversation history and extract all information about {target_name}.
    """
    
    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        
        print(f"🔍 Debug - AI found information for {target_name}: {len(result) > 100}")
        
        # Check if the AI response indicates it couldn't find the information
        not_found_indicators = [
            "could not find", "couldn't find", "not found", "no information", 
            "not listed", "not available", "sorry", "apologize"
        ]
        
        response_indicates_not_found = any(indicator in result.lower() for indicator in not_found_indicators)
        
        if response_indicates_not_found:
            print(f"🔄 AI couldn't find {target_name} in conversation history")
            print(f"🔄 Falling back to new query processing...")
            return process_new_query(query, session_id)
        
        # Add to conversation history
        add_to_conversation_history(session_id, query, result)
        
        return result
    except Exception as e:
        print(f"📋 Follow-up processing error: {e}")
        print(f"🔄 Falling back to new query processing...")
        # Fallback to new query on error
        return process_new_query(query, session_id)

def process_new_query(query, session_id="default"):
    """Process a new query by finding files and analyzing data"""
    # Find the most relevant file
    file_path, sheet = find_best_file(query)
    
    if file_path:
        print(f"Selected file: {file_path} and sheet: {sheet}")
        if file_path.endswith(('.xlsx', '.xls')):
            
            print(f"🔍 Debug - Sheet parameter received: '{sheet}'")
            print(f"🔍 Debug - Sheet type: {type(sheet)}")
            
            if sheet != "none":
                try:
                    # First, let's see what sheets are available
                    all_sheets = pd.read_excel(file_path, sheet_name=None)
                    available_sheets = list(all_sheets.keys())
                    print(f"🔍 Debug - Available sheets in file: {available_sheets}")
                    
                    # Try to read the specific sheet
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    print(f"✅ Successfully read sheet: '{sheet}'")
                except Exception as e:
                    print(f"❌ Error reading sheet '{sheet}': {e}")
                    print(f"🔄 Falling back to first sheet")
                    df = pd.read_excel(file_path)
            else:
                df = pd.read_excel(file_path)
            print("++++++++++++++++++++++++++++++++++++++++")
            
            print(df)
            print("++++++++++++++++++++++++++++++++++++++++")
            # Process the query with the selected file
            result = process_excel_query(df, query, api)
            
            # Add to conversation history
            add_to_conversation_history(session_id, query, result)
            print(f"💾 Added to conversation history for session: {session_id}")
            
            return result
        elif file_path.endswith('.docx'):
            result = process_word_images(file_path, query)
            
            # Add to conversation history
            add_to_conversation_history(session_id, query, result)
            print(f"💾 Added to conversation history for session: {session_id}")
            
            return result
    
    return "No suitable file found for the query."

def smart_excel_query(user_query, session_id="default"):
    """Find the best file and process the query with conversation awareness"""
    
    print(f"📋 Processing query: '{user_query}' for session: {session_id}")
    
    # Check if this is a follow-up query
    if is_follow_up_query(user_query, session_id):
        print(f"✅ Detected as FOLLOW-UP question")
        print(f"📝 Processing follow-up from conversation history...")
        return process_follow_up_query(user_query, session_id)
    
    print(f"✅ Detected as NEW data analysis question")
    print(f"📊 Processing with file selection...")
    
    return process_new_query(user_query, session_id)

# Usage
if __name__ == "__main__":
    query = input()
    
    print(f"\nQuery: {query}")
    result = smart_excel_query(query)
    print(f"Result: {result}")