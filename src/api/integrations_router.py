from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations import (
    GitHubIntegration,
    DeploymentService,
    BusinessFormationService,
    DomainService,
    LivePreviewService,
    ProjectPersistenceService
)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# Initialize services
github = GitHubIntegration()
deployment = DeploymentService()
business = BusinessFormationService()
domain = DomainService()
preview = LivePreviewService()
persistence = ProjectPersistenceService()

# Request models
class CreateRepoRequest(BaseModel):
    name: str
    description: str = ""
    private: bool = True

class PushFilesRequest(BaseModel):
    owner: str
    repo: str
    files: Dict[str, str]
    branch: str = "main"
    message: str = "Update from LaunchForge"

class DeployRequest(BaseModel):
    project_name: str
    files: Dict[str, str]
    platform: str = "railway"
    env_vars: Dict[str, str] = {}

class BusinessFormationRequest(BaseModel):
    company_name: str
    business_type: str = "llc"
    state: str = "DE"
    industry: str = ""
    founders: List[Dict] = []
    email: str = ""

class DomainCheckRequest(BaseModel):
    domain: str

class DomainSuggestRequest(BaseModel):
    business_name: str

class DnsSetupRequest(BaseModel):
    domain: str
    target_ip: str = None
    cname_target: str = None

class PreviewRequest(BaseModel):
    files: Dict[str, str]
    framework: str = "python"

class ProjectSaveRequest(BaseModel):
    user_id: str
    name: str
    description: str = ""
    framework: str = "fastapi"
    files: Dict[str, str]
    settings: Dict = {}

class ProjectLoadRequest(BaseModel):
    project_id: str
    user_id: str = None

# GitHub endpoints
@router.post("/github/create-repo")
async def create_repository(request: CreateRepoRequest):
    result = await github.create_repository(
        name=request.name,
        description=request.description,
        private=request.private
    )
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Failed to create repository'))
    return result

@router.post("/github/push")
async def push_files(request: PushFilesRequest):
    result = await github.push_files(
        owner=request.owner,
        repo=request.repo,
        files=request.files,
        branch=request.branch,
        message=request.message
    )
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Failed to push files'))
    return result

@router.get("/github/repos")
async def list_repos():
    repos = await github.get_user_repos()
    return {"success": True, "repos": repos}

# Deployment endpoints
@router.post("/deploy")
async def deploy_project(request: DeployRequest):
    if request.platform == "railway":
        result = await deployment.deploy_to_railway(
            project_name=request.project_name,
            files=request.files,
            env_vars=request.env_vars
        )
    elif request.platform == "vercel":
        result = await deployment.deploy_to_vercel(
            project_name=request.project_name,
            files=request.files
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported platform")
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Deployment failed'))
    return result

@router.get("/deploy/status/{project_id}")
async def get_deployment_status(project_id: str):
    result = await deployment.get_deployment_status(project_id)
    return result

# Business Formation endpoints
@router.post("/business/start-atlas")
async def start_atlas(request: BusinessFormationRequest):
    result = await business.start_atlas_application({
        'company_name': request.company_name,
        'business_type': request.business_type,
        'state': request.state,
        'industry': request.industry,
        'founders': request.founders
    })
    return result

@router.post("/business/register-llc")
async def register_llc(request: BusinessFormationRequest):
    result = await business.register_llc(
        company_name=request.company_name,
        state=request.state,
        owner_info={'email': request.email, 'founders': request.founders}
    )
    return result

@router.get("/business/ein-info")
async def get_ein_info():
    return await business.get_ein_application_info()

@router.post("/business/operating-agreement")
async def create_operating_agreement(request: BusinessFormationRequest):
    result = await business.create_operating_agreement({
        'company_name': request.company_name,
        'state': request.state,
        'members': request.founders
    })
    return result

@router.post("/business/stripe-connect")
async def setup_stripe_connect(business_id: str, request: BusinessFormationRequest):
    result = await business.setup_stripe_connect(
        business_id=business_id,
        business_info={
            'company_name': request.company_name,
            'email': request.email
        }
    )
    return result

@router.get("/business/checklist/{business_type}")
async def get_business_checklist(business_type: str = "llc"):
    return await business.get_business_checklist(business_type)

# Domain endpoints
@router.post("/domain/check")
async def check_domain(request: DomainCheckRequest):
    result = await domain.check_domain_availability(request.domain)
    return result

@router.post("/domain/suggest")
async def suggest_domains(request: DomainSuggestRequest):
    suggestions = await domain.suggest_domains(request.business_name)
    return {"success": True, "suggestions": suggestions}

@router.post("/domain/setup-dns")
async def setup_dns(request: DnsSetupRequest):
    result = await domain.setup_cloudflare_dns(
        domain=request.domain,
        target_ip=request.target_ip,
        cname_target=request.cname_target
    )
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'DNS setup failed'))
    return result

# Preview endpoints
@router.post("/preview/sandbox")
async def create_sandbox_preview(request: PreviewRequest):
    result = await preview.create_sandbox_preview(
        files=request.files,
        framework=request.framework
    )
    return result

@router.post("/preview/html")
async def generate_html_preview(request: PreviewRequest):
    result = await preview.generate_html_preview(request.files)
    return result

@router.post("/preview/replit")
async def create_replit_preview(request: PreviewRequest):
    result = await preview.create_replit_preview(
        files=request.files,
        language=request.framework
    )
    return result

# Project Persistence endpoints
@router.post("/projects/save")
async def save_project(request: ProjectSaveRequest):
    result = await persistence.save_project(
        user_id=request.user_id,
        project_data={
            'name': request.name,
            'description': request.description,
            'framework': request.framework,
            'files': request.files,
            'settings': request.settings
        }
    )
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Failed to save project'))
    return result

@router.post("/projects/load")
async def load_project(request: ProjectLoadRequest):
    result = await persistence.load_project(
        project_id=request.project_id,
        user_id=request.user_id
    )
    if not result.get('success'):
        raise HTTPException(status_code=404, detail=result.get('error', 'Project not found'))
    return result

@router.get("/projects/list/{user_id}")
async def list_projects(user_id: str):
    result = await persistence.list_projects(user_id)
    return result

@router.post("/projects/{project_id}/version")
async def create_version(project_id: str, files: Dict[str, str], message: str = ""):
    result = await persistence.create_version(
        project_id=project_id,
        files=files,
        message=message
    )
    return result

@router.post("/projects/{project_id}/restore/{version}")
async def restore_version(project_id: str, version: int):
    result = await persistence.restore_version(
        project_id=project_id,
        version=version
    )
    return result

@router.get("/projects/{project_id}/export")
async def export_project(project_id: str, format: str = "zip"):
    result = await persistence.export_project(
        project_id=project_id,
        format=format
    )
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Export failed'))
    return result

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user_id: str):
    result = await persistence.delete_project(
        project_id=project_id,
        user_id=user_id
    )
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Delete failed'))
    return result
