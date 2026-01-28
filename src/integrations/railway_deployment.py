import os
import httpx
import json
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class RailwayDeploymentService:
    """Real Railway deployment service using Railway API."""
    
    def __init__(self):
        self.api_token = os.getenv('RAILWAY_TOKEN')
        self.api_url = 'https://backboard.railway.app/graphql/v2'
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    async def create_project(self, name: str) -> Dict[str, Any]:
        """Create a new Railway project."""
        query = '''
        mutation projectCreate($input: ProjectCreateInput!) {
            projectCreate(input: $input) {
                id
                name
                environments {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        }
        '''
        variables = {
            'input': {
                'name': name,
                'isPublic': False
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers=self.headers,
                json={'query': query, 'variables': variables},
                timeout=30.0
            )
            data = response.json()
            
            if 'errors' in data:
                logger.error(f"Railway API error: {data['errors']}")
                return {'success': False, 'error': data['errors'][0]['message']}
            
            project = data['data']['projectCreate']
            return {
                'success': True,
                'project_id': project['id'],
                'name': project['name'],
                'environments': project['environments']['edges']
            }
    
    async def create_service_from_github(
        self,
        project_id: str,
        environment_id: str,
        repo_full_name: str,
        branch: str = 'main'
    ) -> Dict[str, Any]:
        """Create a service from a GitHub repository."""
        query = '''
        mutation serviceCreate($input: ServiceCreateInput!) {
            serviceCreate(input: $input) {
                id
                name
            }
        }
        '''
        variables = {
            'input': {
                'projectId': project_id,
                'source': {
                    'repo': repo_full_name
                },
                'branch': branch
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers=self.headers,
                json={'query': query, 'variables': variables},
                timeout=30.0
            )
            data = response.json()
            
            if 'errors' in data:
                logger.error(f"Railway service create error: {data['errors']}")
                return {'success': False, 'error': data['errors'][0]['message']}
            
            service = data['data']['serviceCreate']
            return {
                'success': True,
                'service_id': service['id'],
                'name': service['name']
            }

    async def generate_domain(self, project_id: str, service_id: str, environment_id: str) -> Dict[str, Any]:
        """Generate a Railway subdomain for the service."""
        query = '''
        mutation serviceDomainCreate($input: ServiceDomainCreateInput!) {
            serviceDomainCreate(input: $input) {
                id
                domain
            }
        }
        '''
        variables = {
            'input': {
                'serviceId': service_id,
                'environmentId': environment_id
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers=self.headers,
                json={'query': query, 'variables': variables},
                timeout=30.0
            )
            data = response.json()
            
            if 'errors' in data:
                logger.error(f"Railway domain create error: {data['errors']}")
                return {'success': False, 'error': data['errors'][0]['message']}
            
            domain_data = data['data']['serviceDomainCreate']
            return {
                'success': True,
                'domain_id': domain_data['id'],
                'domain': domain_data['domain']
            }
    
    async def set_environment_variables(
        self,
        project_id: str,
        service_id: str,
        environment_id: str,
        variables: Dict[str, str]
    ) -> Dict[str, Any]:
        """Set environment variables for a service."""
        query = '''
        mutation variableCollectionUpsert($input: VariableCollectionUpsertInput!) {
            variableCollectionUpsert(input: $input)
        }
        '''
        gql_variables = {
            'input': {
                'projectId': project_id,
                'serviceId': service_id,
                'environmentId': environment_id,
                'variables': variables
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers=self.headers,
                json={'query': query, 'variables': gql_variables},
                timeout=30.0
            )
            data = response.json()
            
            if 'errors' in data:
                logger.error(f"Railway env vars error: {data['errors']}")
                return {'success': False, 'error': data['errors'][0]['message']}
            
            return {'success': True}
    
    async def trigger_deployment(self, service_id: str, environment_id: str) -> Dict[str, Any]:
        """Trigger a new deployment."""
        query = '''
        mutation deploymentCreate($input: DeploymentCreateInput!) {
            deploymentCreate(input: $input) {
                id
                status
            }
        }
        '''
        variables = {
            'input': {
                'serviceId': service_id,
                'environmentId': environment_id
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers=self.headers,
                json={'query': query, 'variables': variables},
                timeout=30.0
            )
            data = response.json()
            
            if 'errors' in data:
                logger.error(f"Railway deployment error: {data['errors']}")
                return {'success': False, 'error': data['errors'][0]['message']}
            
            deployment = data['data']['deploymentCreate']
            return {
                'success': True,
                'deployment_id': deployment['id'],
                'status': deployment['status']
            }

    async def deploy_app(
        self,
        app_name: str,
        github_repo: str,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Full deployment pipeline: create project, service, domain, deploy."""
        try:
            # Step 1: Create Railway project
            project_result = await self.create_project(app_name)
            if not project_result.get('success'):
                return project_result
            
            project_id = project_result['project_id']
            env_id = project_result['environments'][0]['node']['id'] if project_result['environments'] else None
            
            if not env_id:
                return {'success': False, 'error': 'No environment found'}
            
            # Step 2: Create service from GitHub repo
            service_result = await self.create_service_from_github(
                project_id=project_id,
                environment_id=env_id,
                repo_full_name=github_repo
            )
            if not service_result.get('success'):
                return service_result
            
            service_id = service_result['service_id']
            
            # Step 3: Set environment variables if provided
            if env_vars:
                await self.set_environment_variables(
                    project_id=project_id,
                    service_id=service_id,
                    environment_id=env_id,
                    variables=env_vars
                )
            
            # Step 4: Generate domain
            domain_result = await self.generate_domain(
                project_id=project_id,
                service_id=service_id,
                environment_id=env_id
            )
            
            domain = domain_result.get('domain', f"{app_name.lower()}.up.railway.app")
            
            # Step 5: Trigger deployment
            deploy_result = await self.trigger_deployment(
                service_id=service_id,
                environment_id=env_id
            )
            
            return {
                'success': True,
                'project_id': project_id,
                'service_id': service_id,
                'environment_id': env_id,
                'domain': domain,
                'url': f"https://{domain}",
                'deployment_id': deploy_result.get('deployment_id'),
                'status': 'deploying'
            }
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            return {'success': False, 'error': str(e)}


# Singleton instance
railway_deployment = RailwayDeploymentService()
