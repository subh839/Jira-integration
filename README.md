# Context Switcher for Jira 🚀

An AI-powered Atlassian Forge app that provides developers with instant context switching by aggregating related Confluence documents, Bitbucket commits, and Jira Service Management tickets in one place.

## Features

- 🤖 **AI-Powered Summaries** - Get intelligent context summaries using OpenAI
- 📄 **Confluence Integration** - Find related documents automatically  
- 🔨 **Bitbucket Commits** - See recent commits mentioning the issue
- 🎫 **Service Management** - View linked service tickets
- ⚡ **FastAPI Backend** - High-performance async API
- 🎨 **Modern UI** - Clean, intuitive interface

## Tech Stack

- **Backend**: FastAPI, Python
- **AI**: OpenAI GPT-3.5-turbo
- **Frontend**: Next.js, TypeScript, Forge UI
- **Deployment**: Railway, Atlassian Forge
- **Authentication**: Atlassian Forge OAuth

## API Endpoints

- `GET /health` - Health check
- `GET /` - API information
- `GET /api/context/{issue_key}` - Get issue context
- `POST /api/summarize` - AI text summarization

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `.env`
4. Run: `uvicorn main:app --reload`

## Environment Variables

```env
FLASK_ENV=development
PORT=3001
OPENAI_API_KEY=your_openai_key
