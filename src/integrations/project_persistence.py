import os
import json
import hashlib
from typing import Dict, List, Optional
from datetime import timezone, datetime
import httpx

class ProjectPersistenceService:
    """Project persistence and version control service."""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.storage_path = os.environ.get('STORAGE_PATH', '/tmp/launchforge_projects')
        self.s3_bucket = os.environ.get('AWS_S3_BUCKET')
        self.s3_region = os.environ.get('AWS_REGION', 'us-east-1')
    
    async def save_project(self, user_id: str, project_data: Dict) -> Dict:
        """Save project to database and file storage."""
        try:
            project_id = project_data.get('id') or self._generate_project_id(user_id)
            
            # Create project record
            project_record = {
                'id': project_id,
                'user_id': user_id,
                'name': project_data.get('name', 'Untitled Project'),
                'description': project_data.get('description', ''),
                'framework': project_data.get('framework', 'fastapi'),
                'files': project_data.get('files', {}),
                'settings': project_data.get('settings', {}),
                'version': project_data.get('version', 1),
                'created_at': project_data.get('created_at', datetime.now(timezone.utc).isoformat()),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'status': project_data.get('status', 'draft')
            }
            
            # Save to local storage (fallback)
            await self._save_to_local(project_id, project_record)
            
            return {
                'success': True,
                'project_id': project_id,
                'version': project_record['version']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def load_project(self, project_id: str, user_id: str = None) -> Dict:
        """Load project from storage."""
        try:
            # Try local storage first
            project = await self._load_from_local(project_id)
            
            if project:
                if user_id and project.get('user_id') != user_id:
                    return {'success': False, 'error': 'Unauthorized'}
                return {'success': True, 'project': project}
            
            return {'success': False, 'error': 'Project not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def list_projects(self, user_id: str) -> Dict:
        """List all projects for a user."""
        try:
            projects = await self._list_local_projects(user_id)
            return {
                'success': True,
                'projects': projects,
                'count': len(projects)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def create_version(self, project_id: str, files: Dict[str, str], message: str = '') -> Dict:
        """Create a new version of the project."""
        try:
            project = await self._load_from_local(project_id)
            if not project:
                return {'success': False, 'error': 'Project not found'}
            
            # Increment version
            new_version = project.get('version', 1) + 1
            
            # Create version record
            version_record = {
                'version': new_version,
                'files': files,
                'message': message,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'file_hash': self._hash_files(files)
            }
            
            # Update project
            project['version'] = new_version
            project['files'] = files
            project['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            if 'versions' not in project:
                project['versions'] = []
            project['versions'].append(version_record)
            
            await self._save_to_local(project_id, project)
            
            return {
                'success': True,
                'version': new_version,
                'hash': version_record['file_hash']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def restore_version(self, project_id: str, version: int) -> Dict:
        """Restore project to a specific version."""
        try:
            project = await self._load_from_local(project_id)
            if not project:
                return {'success': False, 'error': 'Project not found'}
            
            versions = project.get('versions', [])
            target_version = next((v for v in versions if v['version'] == version), None)
            
            if not target_version:
                return {'success': False, 'error': 'Version not found'}
            
            project['files'] = target_version['files']
            project['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            await self._save_to_local(project_id, project)
            
            return {
                'success': True,
                'restored_version': version,
                'files': target_version['files']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def delete_project(self, project_id: str, user_id: str) -> Dict:
        """Delete a project."""
        try:
            project = await self._load_from_local(project_id)
            if not project:
                return {'success': False, 'error': 'Project not found'}
            
            if project.get('user_id') != user_id:
                return {'success': False, 'error': 'Unauthorized'}
            
            await self._delete_from_local(project_id)
            
            return {'success': True, 'message': 'Project deleted'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def export_project(self, project_id: str, format: str = 'zip') -> Dict:
        """Export project files."""
        try:
            project = await self._load_from_local(project_id)
            if not project:
                return {'success': False, 'error': 'Project not found'}
            
            if format == 'json':
                return {
                    'success': True,
                    'data': json.dumps(project, indent=2),
                    'filename': f"{project['name']}.json"
                }
            elif format == 'zip':
                # Create zip content (base64 encoded for JSON response)
                import zipfile
                import io
                import base64
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for filename, content in project.get('files', {}).items():
                        zf.writestr(filename, content)
                
                zip_buffer.seek(0)
                zip_base64 = base64.b64encode(zip_buffer.read()).decode()
                
                return {
                    'success': True,
                    'data': zip_base64,
                    'filename': f"{project['name']}.zip",
                    'encoding': 'base64'
                }
            
            return {'success': False, 'error': 'Unsupported format'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_project_id(self, user_id: str) -> str:
        """Generate unique project ID."""
        import uuid
        return f"proj_{uuid.uuid4().hex[:12]}"
    
    def _hash_files(self, files: Dict[str, str]) -> str:
        """Generate hash of all files."""
        content = json.dumps(files, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def _save_to_local(self, project_id: str, data: Dict):
        """Save project to local filesystem."""
        os.makedirs(self.storage_path, exist_ok=True)
        filepath = os.path.join(self.storage_path, f"{project_id}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def _load_from_local(self, project_id: str) -> Optional[Dict]:
        """Load project from local filesystem."""
        filepath = os.path.join(self.storage_path, f"{project_id}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    
    async def _list_local_projects(self, user_id: str) -> List[Dict]:
        """List all projects from local storage."""
        projects = []
        if os.path.exists(self.storage_path):
            for filename in os.listdir(self.storage_path):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.storage_path, filename)
                    with open(filepath, 'r') as f:
                        project = json.load(f)
                        if project.get('user_id') == user_id:
                            projects.append({
                                'id': project['id'],
                                'name': project['name'],
                                'updated_at': project.get('updated_at'),
                                'status': project.get('status')
                            })
        return sorted(projects, key=lambda x: x.get('updated_at', ''), reverse=True)
    
    async def _delete_from_local(self, project_id: str):
        """Delete project from local filesystem."""
        filepath = os.path.join(self.storage_path, f"{project_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
