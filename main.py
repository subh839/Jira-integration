from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import logging
from datetime import datetime
import openai

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

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

# Initialize OpenAI
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    openai.api_key = openai_api_key
    ai_enabled = True
    logger.info("OpenAI API configured successfully")
else:
    ai_enabled = False
    logger.warning("OpenAI API key not found. AI features disabled.")

# Pydantic models
class SummarizeRequest(BaseModel):
    content: str
    max_length: Optional[int] = 100

class HealthResponse(BaseModel):
    status: str
    service: str
    ai_enabled: bool
    timestamp: str

def summarize_with_ai(text: str, max_length: int = 100) -> str:
    """Summarize text using OpenAI"""
    if not ai_enabled:
        return f"AI not configured. Would summarize: {text[:max_length]}..."
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a concise text summarizer."},
                {"role": "user", "content": f"Summarize this in under {max_length} characters: {text}"}
            ],
            max_tokens=50,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI summarization failed: {e}")
        return f"AI service error: {str(e)}"

@app.get("/")
async def root():
    return {
        "message": "Context Switcher API",
        "status": "running",
        "ai_enabled": ai_enabled,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/summarize")
async def summarize_content(request: SummarizeRequest):
    try:
        summary = summarize_with_ai(request.content, request.max_length)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

@app.get("/health")
async def health_check():
    return HealthResponse(
        status="healthy",
        service="context-switcher-api",
        ai_enabled=ai_enabled,
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/api/context/{issue_key}")
async def get_context(issue_key: str):
    # Generate AI summary for the context
    context_summary = ""
    if ai_enabled:
        try:
            prompt = f"Provide a brief summary for Jira issue {issue_key} which is about software development context switching."
            context_summary = summarize_with_ai(prompt, 150)
        except Exception as e:
            context_summary = f"AI summary unavailable: {str(e)}"
    
    return {
        "issue": {
            "key": issue_key,
            "summary": "Sample issue for demonstration",
            "project": "TEST",
            "status": "In Progress",
            "issueType": "Bug"
        },
        "confluenceDocs": [
            {
                "id": "doc-1",
                "title": "Sample Confluence Document",
                "type": "page",
                "_links": {"webui": "/spaces/TEST/pages/doc-1"}
            }
        ],
        "bitbucketCommits": [
            {
                "id": "commit-1",
                "message": f"Fixed {issue_key}: Sample commit",
                "author": "Developer",
                "authorTimestamp": 1672531200000,
                "repository": "sample-repo"
            }
        ],
        "serviceTickets": [],
        "lastUpdated": datetime.utcnow().isoformat(),
        "aiEnabled": ai_enabled,
        "aiSummary": context_summary if ai_enabled else "AI not configured",
        "aiSuggestions": [
            "Check related documentation",
            "Review recent code changes",
            "Verify service dependencies"
        ] if ai_enabled else []
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3001))
    uvicorn.run(app, host="0.0.0.0", port=port)