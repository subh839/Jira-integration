from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from datetime import datetime
import logging

from services.atlassian_client import AtlassianClient
from services.ai_service import AIService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Context Switcher API",
    description="AI-powered context aggregation for Jira issues",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI Service
ai_service = AIService() if os.getenv('OPENAI_API_KEY') else None

# Pydantic v1 models
class SummarizeRequest(BaseModel):
    content: str
    max_length: Optional[int] = 100

class HealthResponse(BaseModel):
    status: str
    service: str
    ai_enabled: bool
    timestamp: str

def verify_auth(authorization: str = Header(...), x_cloud_id: str = Header(...)):
    if not authorization or not x_cloud_id:
        raise HTTPException(status_code=401, detail="Missing authentication headers")
    
    token = authorization.replace("Bearer ", "")
    return {"token": token, "cloud_id": x_cloud_id}

@app.get("/")
async def root():
    return {
        "message": "Context Switcher API",
        "status": "running",
        "ai_enabled": ai_service.is_enabled() if ai_service else False,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/context/{issue_key}")
async def get_context(issue_key: str, auth: Dict[str, str] = Depends(verify_auth)):
    try:
        logger.info(f"Fetching context for issue: {issue_key}")
        
        client = AtlassianClient(auth["token"], auth["cloud_id"])
        context_data = await client.get_issue_context(issue_key)
        
        if 'error' in context_data:
            raise HTTPException(status_code=404, detail=context_data['error'])
        
        if ai_service and ai_service.is_enabled():
            context_data = ai_service.enhance_with_ai(context_data)
        
        context_data['lastUpdated'] = datetime.utcnow().isoformat()
        context_data['aiEnabled'] = ai_service.is_enabled() if ai_service else False
        
        return context_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/summarize")
async def summarize_content(request: SummarizeRequest):
    if not ai_service or not ai_service.is_enabled():
        raise HTTPException(status_code=503, detail="AI service not configured")
    
    try:
        summary = ai_service.summarize_text(request.content, request.max_length)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

@app.get("/health")
async def health_check():
    return HealthResponse(
        status="healthy",
        service="context-switcher-api",
        ai_enabled=ai_service.is_enabled() if ai_service else False,
        timestamp=datetime.utcnow().isoformat()
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3001))
    uvicorn.run(app, host="0.0.0.0", port=port)