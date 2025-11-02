import os
import openai  # Change this import
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = None
        
        if not self.api_key:
            logger.warning("OpenAI API key not found. AI features disabled.")
            return
        
        # Initialize OpenAI with old syntax
        try:
            openai.api_key = self.api_key
            # For v0.28.1, we don't create a client instance
            logger.info("AI Service initialized successfully (v0.28.1)")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
    
    def is_enabled(self) -> bool:
        return self.api_key is not None
    
    def enhance_with_ai(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add AI-powered enhancements to context data"""
        if not self.is_enabled():
            context_data['aiSummary'] = "AI features not configured"
            context_data['aiSuggestions'] = []
            return context_data
        
        try:
            # Generate overall context summary
            summary = self._generate_context_summary(context_data)
            context_data['aiSummary'] = summary
            
            # Generate smart suggestions
            suggestions = self._generate_suggestions(context_data)
            context_data['aiSuggestions'] = suggestions
            
            # Summarize long commit messages
            if 'bitbucketCommits' in context_data:
                context_data['bitbucketCommits'] = self._summarize_commits(
                    context_data['bitbucketCommits']
                )
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {str(e)}")
            context_data['aiSummary'] = "AI analysis temporarily unavailable"
            context_data['aiSuggestions'] = []
        
        return context_data
    
    def _generate_context_summary(self, context_data: Dict[str, Any]) -> str:
        """Generate an intelligent summary of the issue context"""
        if not self.is_enabled():
            return "AI service unavailable"
        
        # Safely get context data with defaults
        issue_key = context_data.get('issue', {}).get('key', 'Unknown')
        issue_summary = context_data.get('issue', {}).get('summary', 'No summary')
        issue_status = context_data.get('issue', {}).get('status', 'Unknown')
        issue_type = context_data.get('issue', {}).get('issueType', 'Unknown')
        
        confluence_count = len(context_data.get('confluenceDocs', []))
        commit_count = len(context_data.get('bitbucketCommits', []))
        ticket_count = len(context_data.get('serviceTickets', []))
        
        prompt = f"""
        Analyze this Jira issue context and provide a concise summary (2-3 sentences):
        
        Issue: {issue_key} - {issue_summary}
        Status: {issue_status}
        Type: {issue_type}
        
        Related Documents: {confluence_count} found
        Recent Commits: {commit_count} found  
        Linked Service Tickets: {ticket_count} found
        
        Focus on:
        1. What's the current progress?
        2. Any potential blockers or dependencies?
        3. Key related resources developer should check?
        
        Keep it very concise and actionable.
        """
        
        try:
            # OLD SYNTAX for v0.28.1
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes Jira issue context for developers. Be concise and practical."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"AI summary generation failed: {str(e)}")
            return "Unable to generate AI summary at this time."
    
    def _generate_suggestions(self, context_data: Dict[str, Any]) -> List[str]:
        """Generate smart suggestions based on context"""
        if not self.is_enabled():
            return ["Check related documents", "Review recent commits", "Verify service dependencies"]
        
        # Safely get context data with defaults
        issue_key = context_data.get('issue', {}).get('key', 'Unknown')
        issue_summary = context_data.get('issue', {}).get('summary', 'No summary')
        issue_status = context_data.get('issue', {}).get('status', 'Unknown')
        issue_type = context_data.get('issue', {}).get('issueType', 'Unknown')
        
        confluence_count = len(context_data.get('confluenceDocs', []))
        commit_count = len(context_data.get('bitbucketCommits', []))
        ticket_count = len(context_data.get('serviceTickets', []))
        
        prompt = f"""
        Based on this Jira issue context, suggest 2-3 actionable next steps for the developer:
        
        Issue: {issue_key} - {issue_summary}
        Status: {issue_status}
        Type: {issue_type}
        
        Documents: {confluence_count} related
        Commits: {commit_count} recent
        Service Tickets: {ticket_count} linked
        
        Provide suggestions as a bullet point list. Be very concise and practical.
        Focus on immediate next actions.
        """
        
        try:
            # OLD SYNTAX for v0.28.1
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You suggest practical next steps for software developers working on Jira issues."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.4
            )
            
            suggestions_text = response.choices[0].message.content.strip()
            suggestions = [s.strip().replace('- ', '').replace('• ', '').replace('* ', '') 
                          for s in suggestions_text.split('\n') if s.strip()]
            
            return suggestions[:3] if suggestions else ["Check related documents", "Review recent commits", "Verify service dependencies"]
            
        except Exception as e:
            logger.error(f"AI suggestions generation failed: {str(e)}")
            return ["Check related documents", "Review recent commits", "Verify service dependencies"]
    
    def _summarize_commits(self, commits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Summarize long commit messages using AI"""
        if not self.is_enabled() or not commits:
            return commits
        
        for commit in commits[:3]:
            if len(commit.get('message', '')) > 100:
                try:
                    prompt = f"Summarize this git commit message in under 60 characters: {commit['message'][:300]}"
                    
                    # OLD SYNTAX for v0.28.1
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You summarize git commit messages concisely while preserving technical details."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=30,
                        temperature=0.1
                    )
                    
                    commit['aiSummary'] = response.choices[0].message.content.strip()
                    
                except Exception as e:
                    logger.warning(f"Failed to summarize commit: {str(e)}")
                    commit['aiSummary'] = commit['message'][:80] + "..."
        
        return commits
    
    def summarize_text(self, text: str, max_length: int = 100) -> str:
        """Generic text summarization"""
        if not self.is_enabled():
            return text[:max_length] + "..." if len(text) > max_length else text
        
        try:
            prompt = f"Summarize this text in under {max_length} characters: {text[:1000]}"
            
            # OLD SYNTAX for v0.28.1
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a concise text summarizer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            return text[:max_length] + "..." if len(text) > max_length else text
    
    def test_connection(self):
        """Test if OpenAI API is working and has quota"""
        if not self.is_enabled():
            return False, "AI service not configured"
        
        try:
            # OLD SYNTAX for v0.28.1
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say 'Hello'"}],
                max_tokens=5
            )
            return True, "Connection successful"
        except Exception as e:
            return False, f"API error: {str(e)}"