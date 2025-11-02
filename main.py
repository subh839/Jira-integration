from dotenv import load_dotenv
load_dotenv()  # This must be before other imports

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

# Initialize FastAPI app
app = FastAPI(
    title="Context Switcher API",
    description="AI-powered context aggregation for Jira issues",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI Service
ai_service = AIService() if os.getenv('OPENAI_API_KEY') else None

# Pydantic models for request/response validation
class SummarizeRequest(BaseModel):
    content: str
    max_length: Optional[int] = 100

class SummarizeResponse(BaseModel):
    summary: str

class ContextResponse(BaseModel):
    issue: Dict[str, Any]
    confluenceDocs: List[Dict[str, Any]]
    bitbucketCommits: List[Dict[str, Any]]
    serviceTickets: List[Dict[str, Any]]
    lastUpdated: str
    aiEnabled: bool
    aiSummary: Optional[str] = None
    aiSuggestions: Optional[List[str]] = None

class HealthResponse(BaseModel):
    status: str
    service: str
    ai_enabled: bool
    timestamp: str

# Dependency for authentication
async def verify_auth(
    authorization: str = Header(..., description="Bearer token from Forge"),
    x_cloud_id: str = Header(..., description="Atlassian Cloud ID")
):
    if not authorization or not x_cloud_id:
        raise HTTPException(status_code=401, detail="Missing authentication headers")
    
    token = authorization.replace("Bearer ", "")
    return {"token": token, "cloud_id": x_cloud_id}

@app.get("/", summary="API Root", response_model=Dict[str, Any])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Context Switcher API",
        "status": "running",
        "ai_enabled": ai_service.is_enabled() if ai_service else False,
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "context": "/api/context/{issue_key}"
        }
    }

@app.get(
    "/api/context/{issue_key}",
    summary="Get Issue Context",
    response_model=ContextResponse,
    responses={
        200: {"description": "Successfully retrieved context"},
        401: {"description": "Missing or invalid authentication"},
        404: {"description": "Issue not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_context(
    issue_key: str,
    auth: Dict[str, str] = Depends(verify_auth)
):
    """
    Get comprehensive context for a Jira issue including:
    - Related Confluence documents
    - Recent Bitbucket commits
    - Linked service tickets
    - AI-powered summaries and suggestions
    """
    try:
        logger.info(f"Fetching context for issue: {issue_key}")
        
        # Initialize Atlassian client
        client = AtlassianClient(auth["token"], auth["cloud_id"])
        
        # Fetch all context data
        context_data = client.get_issue_context(issue_key)
        
        if 'error' in context_data:
            raise HTTPException(status_code=404, detail=context_data['error'])
        
        # Add AI summaries if enabled
        if ai_service and ai_service.is_enabled():
            logger.info("Enhancing with AI features...")
            context_data = ai_service.enhance_with_ai(context_data)
        
        context_data['lastUpdated'] = datetime.utcnow().isoformat()
        context_data['aiEnabled'] = ai_service.is_enabled() if ai_service else False
        
        logger.info(f"Successfully fetched context for {issue_key}")
        return context_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching context for {issue_key}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post(
    "/api/summarize",
    summary="Summarize Text",
    response_model=SummarizeResponse,
    responses={
        200: {"description": "Successfully summarized text"},
        503: {"description": "AI service not available"}
    }
)
async def summarize_content(request: SummarizeRequest):
    """Summarize text content using AI"""
    if not ai_service or not ai_service.is_enabled():
        raise HTTPException(status_code=503, detail="AI service not configured")
    
    try:
        summary = ai_service.summarize_text(request.content, request.max_length)
        return SummarizeResponse(summary=summary)
        
    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

@app.get(
    "/health",
    summary="Health Check",
    response_model=HealthResponse
)
async def health_check():
    """Health check endpoint for deployment verification"""
    return HealthResponse(
        status="healthy",
        service="context-switcher-api",
        ai_enabled=ai_service.is_enabled() if ai_service else False,
        timestamp=datetime.utcnow().isoformat()
    )

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3001))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("FLASK_ENV") == "development"
    )