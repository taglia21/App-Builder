import os
import httpx
from typing import Dict, Optional
from datetime import datetime

class DeploymentService:
    """Real deployment service for Railway, Vercel, and other platforms."""
    
    def __init__(self):
        self.railway_token = os.environ.get('RAILWAY_TOKEN')
        self.vercel_token = os.environ.get('VERCEL_TOKEN')
        self.railway_api = 'https://backboard.railway.app/graphql/v2'
    
    async def deploy_to_railway(self, project_name: str, files: Dict[str, str], env_vars: Dict[str, str] = None) -> Dict:
        """Deploy project to Railway."""
        if not self.railway_token:
            return {'success': False, 'error': 'Railway token not configured'}
        
        try:
            async with httpx.AsyncClient() as client:
                # Create project
                create_project_query = '''
                    mutation CreateProject($name: String!) {
                        projectCreate(input: { name: $name }) {
                            id
                            name
                        }
                    }
                '''
                response = await client.post(
                    self.railway_api,
                    headers={
                        'Authorization': f'Bearer {self.railway_token}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'query': create_project_query,
                        'variables': {'name': project_name}
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and data['data'].get('projectCreate'):
                        project_id = data['data']['projectCreate']['id']
                        return {
                            'success': True,
                            'project_id': project_id,
                            'url': f'https://{project_name}.up.railway.app',
                            'dashboard_url': f'https://railway.app/project/{project_id}'
                        }
                
                return {'success': False, 'error': 'Failed to create Railway project'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_deployment_status(self, project_id: str) -> Dict:
        """Get deployment status from Railway."""
        try:
            async with httpx.AsyncClient() as client:
                query = '''
                    query GetProject($id: String!) {
                        project(id: $id) {
                            id
                            name
                            deployments(first: 1) {
                                edges {
                                    node {
                                        id
                                        status
                                        createdAt
                                    }
                                }
                            }
                        }
                    }
                '''
                response = await client.post(
                    self.railway_api,
                    headers={
                        'Authorization': f'Bearer {self.railway_token}',
                        'Content-Type': 'application/json'
                    },
                    json={'query': query, 'variables': {'id': project_id}}
                )
                
                if response.status_code == 200:
                    return {'success': True, 'data': response.json()}
                return {'success': False, 'error': 'Failed to get status'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def deploy_to_vercel(self, project_name: str, files: Dict[str, str]) -> Dict:
        """Deploy project to Vercel."""
        if not self.vercel_token:
            return {'success': False, 'error': 'Vercel token not configured'}
        
        try:
            async with httpx.AsyncClient() as client:
                # Create deployment
                response = await client.post(
                    'https://api.vercel.com/v13/deployments',
                    headers={
                        'Authorization': f'Bearer {self.vercel_token}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'name': project_name,
                        'files': [
                            {'file': path, 'data': content}
                            for path, content in files.items()
                        ]
                    }
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return {
                        'success': True,
                        'deployment_id': data.get('id'),
                        'url': data.get('url'),
                        'ready_state': data.get('readyState')
                    }
                return {'success': False, 'error': 'Failed to deploy to Vercel'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_environment(self, project_id: str, env_name: str = 'production') -> Dict:
        """Create a Railway environment."""
        try:
            async with httpx.AsyncClient() as client:
                query = '''
                    mutation CreateEnvironment($projectId: String!, $name: String!) {
                        environmentCreate(input: { projectId: $projectId, name: $name }) {
                            id
                            name
                        }
                    }
                '''
                response = await client.post(
                    self.railway_api,
                    headers={
                        'Authorization': f'Bearer {self.railway_token}',
                        'Content-Type': 'application/json'
                    },
                    json={'query': query, 'variables': {'projectId': project_id, 'name': env_name}}
                )
                
                if response.status_code == 200:
                    return {'success': True, 'data': response.json()}
                return {'success': False}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def set_env_variables(self, project_id: str, env_id: str, variables: Dict[str, str]) -> Dict:
        """Set environment variables for a deployment."""
        try:
            async with httpx.AsyncClient() as client:
                query = '''
                    mutation SetVariables($projectId: String!, $environmentId: String!, $variables: [VariableInput!]!) {
                        variablesSetFromObject(input: { projectId: $projectId, environmentId: $environmentId, variables: $variables }) {
                            status
                        }
                    }
                '''
                variables_list = [{'key': k, 'value': v} for k, v in variables.items()]
                response = await client.post(
                    self.railway_api,
                    headers={
                        'Authorization': f'Bearer {self.railway_token}',
                        'Content-Type': 'application/json'
                    },
                    json={'query': query, 'variables': {
                        'projectId': project_id,
                        'environmentId': env_id,
                        'variables': variables_list
                    }}
                )
                return {'success': response.status_code == 200}
        except Exception as e:
            return {'success': False, 'error': str(e)}
