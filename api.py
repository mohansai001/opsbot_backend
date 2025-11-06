from fastapi import FastAPI
from pydantic import BaseModel
from smart_query import smart_excel_query, get_conversation_history, add_to_conversation_history, is_follow_up_query
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["*"] for all (not safe in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    session_id: str = "default"

@app.post("/query")
async def process_query(request: QueryRequest):
    try:
        result = smart_excel_query(request.query, request.session_id)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/history/{session_id}")
async def get_history(session_id: str = "default"):
    try:
        history = get_conversation_history(session_id)
        return {"success": True, "history": history}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/history/{session_id}")
async def clear_history(session_id: str = "default"):
    try:
        # Import and call clear function
        from smart_query import clear_conversation_history
        clear_conversation_history(session_id)
        return {"success": True, "message": "History cleared"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    return {"message": "Excel Query API is running"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)