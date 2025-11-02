import os
from openai import OpenAI
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OpenAI API key not found. AI features disabled.")
            return
        
        try:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("AI Service initialized successfully with OpenAI v1.3.0")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def is_enabled(self) -> bool:
        return self.api_key is not None and self.client is not None
    
    def enhance_with_ai(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add AI-powered enhancements to context data"""
        if not self.is_enabled():
            context_data['aiSummary'] = "AI features not configured"
            return context_data
        
        try:
            # Generate overall context summary
            summary = self._generate_context_summary(context_data)
            context_data['aiSummary'] = summary
            
            # Generate smart suggestions
            suggestions = self._generate_suggestions(context_data)
            context_data['aiSuggestions'] = suggestions
            
        except Exception as e:
            logger.error(f"AI enhancement failed: {str(e)}")
            context_data['aiSummary'] = "AI analysis temporarily unavailable"
        
        return context_data
    
    def _generate_context_summary(self, context_data: Dict[str, Any]) -> str:
        """Generate an intelligent summary of the issue context"""
        if not self.is_enabled():
            return "AI service unavailable"
        
        prompt = f"""
        Analyze this Jira issue context and provide a concise summary (2-3 sentences):
        
        Issue: {context_data['issue']['key']} - {context_data['issue']['summary']}
        Status: {context_data['issue']['status']}
        Type: {context_data['issue']['issueType']}
        
        Related Documents: {len(context_data['confluenceDocs'])} found
        Recent Commits: {len(context_data['bitbucketCommits'])} found  
        Linked Service Tickets: {len(context_data['serviceTickets'])} found
        
        Focus on:
        1. What's the current progress?
        2. Any potential blockers or dependencies?
        3. Key related resources developer should check?
        
        Keep it very concise and actionable.
        """
        
        try:
            response = self.client.chat.completions.create(
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
        
        prompt = f"""
        Based on this Jira issue context, suggest 2-3 actionable next steps for the developer:
        
        Issue: {context_data['issue']['key']} - {context_data['issue']['summary']}
        Status: {context_data['issue']['status']}
        Type: {context_data['issue']['issueType']}
        
        Documents: {len(context_data['confluenceDocs'])} related
        Commits: {len(context_data['bitbucketCommits'])} recent
        Service Tickets: {len(context_data['serviceTickets'])} linked
        
        Provide suggestions as a bullet point list. Be very concise and practical.
        Focus on immediate next actions.
        """
        
        try:
            response = self.client.chat.completions.create(
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
            
            return suggestions[:3]
            
        except Exception as e:
            logger.error(f"AI suggestions generation failed: {str(e)}")
            return ["Check related documents", "Review recent commits", "Verify service dependencies"]
    
    def summarize_text(self, text: str, max_length: int = 100) -> str:
        """Generic text summarization"""
        if not self.is_enabled():
            return text[:max_length] + "..." if len(text) > max_length else text
        
        try:
            prompt = f"Summarize this text in under {max_length} characters: {text[:1000]}"
            
            response = self.client.chat.completions.create(
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