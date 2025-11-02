import requests
import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class AtlassianClient:
    """
    Client for interacting with Atlassian REST APIs
    """
    
    def __init__(self, token: str, cloud_id: str):
        self.token = token
        self.cloud_id = cloud_id
        self.base_headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        self.timeout = 30
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def _make_async_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make async HTTP request"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=self.base_headers, 
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.warning(f"Resource not found: {url}")
                        return None
                    else:
                        logger.error(f"API request failed. Status: {response.status}, URL: {url}")
                        return None
        except Exception as e:
            logger.error(f"Async request failed for URL: {url}: {str(e)}")
            return None
    def _make_sync_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make synchronous HTTP request (for compatibility)"""
        try:
            response = requests.get(
                url, 
                headers=self.base_headers, 
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Resource not found: {url}")
                return None
            else:
                logger.error(f"API request failed. Status: {response.status_code}, URL: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Request failed for URL: {url}: {str(e)}")
            return None
        

    async def _make_request(self, url: str, params: Optional[Dict] = None, async_op: bool = True) -> Optional[Dict[str, Any]]:
        """Generic request method that can be async or sync"""
        if async_op:
            return await self._make_async_request(url, params)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, 
                self._make_sync_request, 
                url, 
                params
            )
        
    async def get_issue_context(self, issue_key: str) -> Dict[str, Any]:
        """
        Main method to gather all context data for a Jira issue
        """
        logger.info(f"Gathering context for issue: {issue_key}")
        
        # Get basic issue information
        issue_data = await self._get_issue_data(issue_key)
        if not issue_data:
            return {'error': f'Issue {issue_key} not found or inaccessible'}
        
        project_key = issue_data['fields']['project']['key']
        
        # Gather data from all sources concurrently
        confluence_docs, bitbucket_commits, service_tickets = await asyncio.gather(
            self._get_confluence_docs(issue_key, project_key),
            self._get_bitbucket_commits(issue_key, project_key),
            self._get_linked_service_tickets(issue_key),
            return_exceptions=True
        )

        if isinstance(confluence_docs, Exception):
            logger.error(f"Confluence docs error: {confluence_docs}")
            confluence_docs = []
        if isinstance(bitbucket_commits, Exception):
            logger.error(f"Bitbucket commits error: {bitbucket_commits}")
            bitbucket_commits = []
        if isinstance(service_tickets, Exception):
            logger.error(f"Service tickets error: {service_tickets}")
            service_tickets = []
        
        return {
            'issue': {
                'key': issue_key,
                'summary': issue_data['fields']['summary'],
                'project': project_key,
                'status': issue_data['fields']['status']['name'],
                'issueType': issue_data['fields']['issuetype']['name']
            },
            'confluenceDocs': confluence_docs,
            'bitbucketCommits': bitbucket_commits,
            'serviceTickets': service_tickets
        }
    

    async def _get_issue_data(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Get basic Jira issue data"""
        url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}/rest/api/3/issue/{issue_key}"
        return await self._make_request(url)
    
    async def _get_confluence_docs(self, issue_key: str, project_key: str) -> List[Dict[str, Any]]:
        """Search Confluence for documents related to the issue"""
        docs = []
        search_queries = [
            f'"{issue_key}"',
            f'~"{issue_key}"',
            project_key
        ]
        
        tasks = []
        for query in search_queries:
            url = f"https://api.atlassian.com/ex/confluence/{self.cloud_id}/rest/api/content/search"
            params = {
                'cql': f'text ~ "{query}"',
                'limit': 10
            }
            tasks.append(self._make_request(url, params))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict) and 'results' in result:
                for doc in result['results']:
                    docs.append({
                        'id': doc['id'],
                        'title': doc['title'],
                        'type': doc['type'],
                        'lastModified': doc.get('version', {}).get('when', ''),
                        '_links': doc['_links']
                    })
        
        # Remove duplicates and limit results
        seen_ids = set()
        unique_docs = []
        for doc in docs:
            if doc['id'] not in seen_ids:
                seen_ids.add(doc['id'])
                unique_docs.append(doc)
        
        return unique_docs[:8]
    


    async def _get_bitbucket_commits(self, issue_key: str, project_key: str) -> List[Dict[str, Any]]:
        """Get Bitbucket commits that mention the issue key"""
        commits = []
        
        # Get repositories in the project
        repos_url = f"https://api.atlassian.com/ex/bitbucket/{self.cloud_id}/rest/api/1.0/projects/{project_key}/repos"
        repos_data = await self._make_request(repos_url)
        
        if not repos_data or 'values' not in repos_data:
            return commits
        
        # Check commits in each repository concurrently
        commit_tasks = []
        for repo in repos_data['values'][:3]:
            repo_slug = repo['slug']
            repo_name = repo['name']
            
            commits_url = f"https://api.atlassian.com/ex/bitbucket/{self.cloud_id}/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/commits"
            commits_params = {'limit': 50}
            
            commit_tasks.append(self._get_commits_for_repo(commits_url, commits_params, repo_name, repo_slug, issue_key))

            repo_commits = await asyncio.gather(*commit_tasks, return_exceptions=True)
        
        for commit_list in repo_commits:
            if isinstance(commit_list, list):
                commits.extend(commit_list)
        
        return commits[:15]
    

    async def _get_commits_for_repo(self, commits_url: str, params: Dict, repo_name: str, repo_slug: str, issue_key: str) -> List[Dict[str, Any]]:
        """Get commits for a specific repository"""
        commits_data = await self._make_request(commits_url, params)
        repo_commits = []
        
        if commits_data and 'values' in commits_data:
            for commit in commits_data['values']:
                commit_message = commit.get('message', '')
                if issue_key.upper() in commit_message.upper():
                    repo_commits.append({
                        'id': commit['id'],
                        'message': commit_message,
                        'author': commit['author'].get('displayName', 'Unknown'),
                        'authorTimestamp': commit['authorTimestamp'],
                        'repository': repo_name,
                        'repoSlug': repo_slug
                    })
        
        return repo_commits
    
    async def _get_linked_service_tickets(self, issue_key: str) -> List[Dict[str, Any]]:
        """Get linked Jira Service Management tickets"""
        service_tickets = []
        
        url = f"https://api.atlassian.com/ex/jira/{self.cloud_id}/rest/api/3/issue/{issue_key}"
        params = {'fields': 'issuelinks,project'}
        
        issue_data = await self._make_request(url, params)
        if not issue_data or 'fields' not in issue_data:
            return service_tickets
        
        links = issue_data['fields'].get('issuelinks', [])
        
        for link in links:
            linked_issue = link.get('outwardIssue') or link.get('inwardIssue')
            if linked_issue:
                issue_type_name = linked_issue['fields']['issuetype']['name'].lower()
                
                if any(keyword in issue_type_name for keyword in ['service', 'request', 'incident', 'problem']):
                    service_tickets.append({
                        'key': linked_issue['key'],
                        'summary': linked_issue['fields']['summary'],
                        'status': linked_issue['fields']['status']['name'],
                        'issueType': linked_issue['fields']['issuetype']['name'],
                        'priority': linked_issue['fields'].get('priority', {}).get('name', 'Not set')
                    })
        
        return service_tickets
    
    def __del__(self):
        """Cleanup executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

            