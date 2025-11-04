import zipfile
import os
import base64
import json
import io
from PIL import Image
import re
import google.generativeai as genai
from helpers.config import api
from langchain_google_genai import ChatGoogleGenerativeAI

def extract_images_from_docx(docx_path):
    """Extract images from Word document without python-docx"""
    images = []
    
    try:
        with zipfile.ZipFile(docx_path, 'r') as docx_zip:
            # Get list of image files in the docx
            image_files = [f for f in docx_zip.namelist() if f.startswith('word/media/')]
            
            for img_file in image_files:
                # Extract image data
                img_data = docx_zip.read(img_file)
                img_base64 = base64.b64encode(img_data).decode()
                
                # Determine image type from filename
                img_type = 'jpeg' if img_file.lower().endswith(('.jpg', '.jpeg')) else 'png'
                
                images.append({
                    'filename': os.path.basename(img_file),
                    'data': img_base64,
                    'type': img_type
                })
    
    except Exception as e:
        return f"Error extracting images: {str(e)}"
    
    return images

def extract_utilisation_for_query(table_data, user_query):
    # print(json.dumps(table_data, indent=2))
    prompt=f"""Given the following table data extracted from a utilization report:
{json.dumps(table_data, indent=2)}

User Query: {user_query}

Extract the relevant information from the table data based on the user query.
Return the answer as a JSON array:
[{{"Account": "Name", "HC": "Number", "Utilization": "Percentage"}}]
"""
    llm=ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api, temperature=0)
    response=llm.invoke(prompt)
    response_text=response.content.strip()
    print(f"LLM response for utilisation extraction: {response_text}")
    return response_text

def extract_table_data_from_image(image_base64, filename,user_query):
    """Send image to Gemini Vision using LangChain for table extraction"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage
        
        # Use the working model
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", google_api_key=api)
        
        prompt = """Analyze this utilization report image and extract table data.
        
Return ONLY a JSON array of objects with this exact format:
[{"Account": "AccountName", "HC": "Number", "Utilization": "XX%"}, ...]
        
Extract all visible account names, HC (head count) numbers, and utilization percentages from the table.

Do not include any explanation, just the JSON array.
"""
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                }
            ]
        )
        
        response = llm.invoke([message])
        response_text = response.content.strip()
        
        print(f"Gemini response: {response_text}")
        
        # Clean and parse JSON response
        if response_text.startswith('```json'):
            response_text = response_text[7:-3]
        elif response_text.startswith('```'):
            response_text = response_text[3:-3]
        
        try:
            table_data = json.loads(response_text)
            # print(f"Table data: {table_data}")
            result=extract_utilisation_for_query(table_data, user_query)
            print("-----------------------")
            print(f"Final result: {result}")
            print("--------------------------")
            if result.startswith('```json'):
                result = result[7:-3]
            elif result.startswith('```'):
                result = result[3:-3]
            # return result
            table_data = json.loads(result)
            return table_data
            # return table_data if isinstance(table_data, list) else []
        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {response_text}")
            return []
        
    except Exception as e:
        print(f"Vision API Error: {e}")
        return []

def process_word_images(file_path, user_query):
    """Process Word document and extract table data from images"""
    images = extract_images_from_docx(file_path)
    
    if isinstance(images, str):  # Error message
        return {"success": False, "error": images}
    
    if not images:
        return {"success": False, "error": f"No images found in {os.path.basename(file_path)}"}
    
    # Extract table data from the first image
    filename = os.path.basename(file_path)
    table_data = extract_table_data_from_image(images[0]['data'], filename,user_query)
    # return table_data
    
    return {
        "success": True,
        "result": {
            "text": f"Data extracted from {filename} utilization report:",
            "tableData": table_data
        }
    }
 