"""
GitHub Integration

Manages GitHub repositories for deployed projects.
"""

import os
import base64
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from github import Github, GithubException
from github.Repository import Repository
from github.ContentFile import ContentFile

logger = logging.getLogger(__name__)


class GitHubError(Exception):
    """GitHub API error."""
    pass


class RepositoryExistsError(GitHubError):
    """Repository already exists."""
    pass


class AuthenticationError(GitHubError):
    """GitHub authentication failed."""
    pass


@dataclass
class GitHubRepo:
    """GitHub repository information."""
    id: int
    name: str
    full_name: str
    private: bool
    html_url: str
    clone_url: str
    ssh_url: str
    default_branch: str
    created_at: datetime
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "full_name": self.full_name,
            "private": self.private,
            "html_url": self.html_url,
            "clone_url": self.clone_url,
            "ssh_url": self.ssh_url,
            "default_branch": self.default_branch,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
        }


@dataclass
class GitHubWorkflow:
    """GitHub Actions workflow information."""
    id: int
    name: str
    path: str
    state: str
    html_url: str


@dataclass
class WorkflowRun:
    """GitHub Actions workflow run."""
    id: int
    name: str
    status: str
    conclusion: Optional[str]
    html_url: str
    created_at: datetime
    
    @property
    def is_success(self) -> bool:
        return self.conclusion == "success"
    
    @property
    def is_running(self) -> bool:
        return self.status in ["queued", "in_progress", "pending"]


class GitHubClient:
    """
    GitHub API client for repository and deployment management.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token (defaults to GITHUB_TOKEN env var)
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        
        if not self.token:
            raise AuthenticationError("GitHub token not provided")
        
        try:
            self._client = Github(self.token)
            self._user = self._client.get_user()
            logger.info(f"Authenticated as GitHub user: {self._user.login}")
        except GithubException as e:
            raise AuthenticationError(f"GitHub authentication failed: {e}")
    
    @property
    def username(self) -> str:
        """Get authenticated username."""
        return self._user.login
    
    # ==================== Repository Operations ====================
    
    def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = True,
        auto_init: bool = False,
        gitignore_template: Optional[str] = None,
        license_template: Optional[str] = None,
    ) -> GitHubRepo:
        """
        Create a new GitHub repository.
        
        Args:
            name: Repository name
            description: Repository description
            private: Whether repository is private
            auto_init: Initialize with README
            gitignore_template: Gitignore template (e.g., "Python", "Node")
            license_template: License template (e.g., "mit", "apache-2.0")
            
        Returns:
            GitHubRepo object
        """
        try:
            repo = self._user.create_repo(
                name=name,
                description=description or "",
                private=private,
                auto_init=auto_init,
                gitignore_template=gitignore_template,
                license_template=license_template,
            )
            
            logger.info(f"Created repository: {repo.full_name}")
            
            return self._parse_repo(repo)
            
        except GithubException as e:
            if e.status == 422 and "name already exists" in str(e):
                raise RepositoryExistsError(f"Repository '{name}' already exists")
            raise GitHubError(f"Failed to create repository: {e}")
    
    def get_repository(self, full_name: str) -> GitHubRepo:
        """
        Get a repository by full name (owner/repo).
        
        Args:
            full_name: Full repository name (e.g., "user/repo")
            
        Returns:
            GitHubRepo object
        """
        try:
            repo = self._client.get_repo(full_name)
            return self._parse_repo(repo)
        except GithubException as e:
            raise GitHubError(f"Failed to get repository: {e}")
    
    def delete_repository(self, full_name: str) -> bool:
        """
        Delete a repository.
        
        Args:
            full_name: Full repository name
            
        Returns:
            True if deleted successfully
        """
        try:
            repo = self._client.get_repo(full_name)
            repo.delete()
            logger.info(f"Deleted repository: {full_name}")
            return True
        except GithubException as e:
            raise GitHubError(f"Failed to delete repository: {e}")
    
    def list_repositories(
        self,
        visibility: str = "all",
        sort: str = "updated",
        limit: int = 30,
    ) -> List[GitHubRepo]:
        """
        List user's repositories.
        
        Args:
            visibility: Filter by visibility (all, public, private)
            sort: Sort by (created, updated, pushed, full_name)
            limit: Maximum number of results
            
        Returns:
            List of GitHubRepo objects
        """
        try:
            repos = self._user.get_repos(
                visibility=visibility,
                sort=sort,
            )
            
            return [self._parse_repo(r) for r in list(repos)[:limit]]
            
        except GithubException as e:
            raise GitHubError(f"Failed to list repositories: {e}")
    
    def _parse_repo(self, repo: Repository) -> GitHubRepo:
        """Parse GitHub repository object."""
        return GitHubRepo(
            id=repo.id,
            name=repo.name,
            full_name=repo.full_name,
            private=repo.private,
            html_url=repo.html_url,
            clone_url=repo.clone_url,
            ssh_url=repo.ssh_url,
            default_branch=repo.default_branch,
            created_at=repo.created_at,
            description=repo.description,
        )
    
    # ==================== File Operations ====================
    
    def upload_file(
        self,
        repo_name: str,
        path: str,
        content: str,
        message: str = "Add file",
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a single file to a repository.
        
        Args:
            repo_name: Full repository name
            path: Path in repository
            content: File content
            message: Commit message
            branch: Target branch (defaults to default branch)
            
        Returns:
            Commit information
        """
        try:
            repo = self._client.get_repo(repo_name)
            
            # Check if file exists
            try:
                existing = repo.get_contents(path, ref=branch)
                # Update existing file
                result = repo.update_file(
                    path=path,
                    message=message,
                    content=content,
                    sha=existing.sha,
                    branch=branch,
                )
            except GithubException:
                # Create new file
                result = repo.create_file(
                    path=path,
                    message=message,
                    content=content,
                    branch=branch,
                )
            
            return {
                "commit_sha": result["commit"].sha,
                "path": path,
            }
            
        except GithubException as e:
            raise GitHubError(f"Failed to upload file: {e}")
    
    def upload_directory(
        self,
        repo_name: str,
        local_path: Path,
        remote_path: str = "",
        message: str = "Upload files",
        branch: Optional[str] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Upload a local directory to a repository.
        
        Args:
            repo_name: Full repository name
            local_path: Local directory path
            remote_path: Target path in repository
            message: Commit message
            branch: Target branch
            exclude_patterns: File patterns to exclude
            
        Returns:
            Upload summary
        """
        exclude = exclude_patterns or [
            "__pycache__",
            ".git",
            "node_modules",
            ".env",
            ".venv",
            "*.pyc",
            ".DS_Store",
        ]
        
        uploaded_files = []
        errors = []
        
        local_path = Path(local_path)
        
        for file_path in local_path.rglob("*"):
            if file_path.is_file():
                # Check exclusions
                skip = False
                for pattern in exclude:
                    if pattern in str(file_path):
                        skip = True
                        break
                
                if skip:
                    continue
                
                relative_path = file_path.relative_to(local_path)
                target_path = f"{remote_path}/{relative_path}" if remote_path else str(relative_path)
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                    self.upload_file(
                        repo_name=repo_name,
                        path=target_path,
                        content=content,
                        message=f"{message}: {relative_path}",
                        branch=branch,
                    )
                    uploaded_files.append(target_path)
                except Exception as e:
                    # Try binary upload for non-text files
                    try:
                        content = base64.b64encode(file_path.read_bytes()).decode()
                        # Note: For binary files, you'd need to use the Git Data API
                        errors.append(f"{target_path}: Binary file (skipped)")
                    except Exception as e2:
                        errors.append(f"{target_path}: {str(e)}")
        
        return {
            "uploaded": len(uploaded_files),
            "files": uploaded_files,
            "errors": errors,
        }
    
    def get_file_content(
        self,
        repo_name: str,
        path: str,
        branch: Optional[str] = None,
    ) -> str:
        """
        Get file content from repository.
        
        Args:
            repo_name: Full repository name
            path: File path
            branch: Branch name
            
        Returns:
            File content
        """
        try:
            repo = self._client.get_repo(repo_name)
            content = repo.get_contents(path, ref=branch)
            
            if isinstance(content, ContentFile):
                return base64.b64decode(content.content).decode("utf-8")
            
            raise GitHubError(f"Path is a directory: {path}")
            
        except GithubException as e:
            raise GitHubError(f"Failed to get file: {e}")
    
    # ==================== Secrets Operations ====================
    
    def set_repository_secret(
        self,
        repo_name: str,
        secret_name: str,
        secret_value: str,
    ) -> bool:
        """
        Set a repository secret for GitHub Actions.
        
        Args:
            repo_name: Full repository name
            secret_name: Secret name
            secret_value: Secret value
            
        Returns:
            True if set successfully
        """
        try:
            repo = self._client.get_repo(repo_name)
            repo.create_secret(secret_name, secret_value)
            logger.info(f"Set secret {secret_name} for {repo_name}")
            return True
        except GithubException as e:
            raise GitHubError(f"Failed to set secret: {e}")
    
    def set_repository_secrets(
        self,
        repo_name: str,
        secrets: Dict[str, str],
    ) -> Dict[str, bool]:
        """
        Set multiple repository secrets.
        
        Args:
            repo_name: Full repository name
            secrets: Dictionary of secret name to value
            
        Returns:
            Dictionary of secret name to success status
        """
        results = {}
        for name, value in secrets.items():
            try:
                self.set_repository_secret(repo_name, name, value)
                results[name] = True
            except GitHubError:
                results[name] = False
        return results
    
    # ==================== GitHub Actions ====================
    
    def list_workflows(self, repo_name: str) -> List[GitHubWorkflow]:
        """
        List GitHub Actions workflows.
        
        Args:
            repo_name: Full repository name
            
        Returns:
            List of workflows
        """
        try:
            repo = self._client.get_repo(repo_name)
            workflows = repo.get_workflows()
            
            return [
                GitHubWorkflow(
                    id=w.id,
                    name=w.name,
                    path=w.path,
                    state=w.state,
                    html_url=w.html_url,
                )
                for w in workflows
            ]
            
        except GithubException as e:
            raise GitHubError(f"Failed to list workflows: {e}")
    
    def trigger_workflow(
        self,
        repo_name: str,
        workflow_id: str,
        ref: str = "main",
        inputs: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Trigger a GitHub Actions workflow.
        
        Args:
            repo_name: Full repository name
            workflow_id: Workflow ID or filename
            ref: Branch or tag to run on
            inputs: Workflow inputs
            
        Returns:
            True if triggered successfully
        """
        try:
            repo = self._client.get_repo(repo_name)
            workflow = repo.get_workflow(workflow_id)
            workflow.create_dispatch(ref=ref, inputs=inputs or {})
            logger.info(f"Triggered workflow {workflow_id} on {repo_name}")
            return True
        except GithubException as e:
            raise GitHubError(f"Failed to trigger workflow: {e}")
    
    def get_workflow_runs(
        self,
        repo_name: str,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> List[WorkflowRun]:
        """
        Get workflow runs.
        
        Args:
            repo_name: Full repository name
            workflow_id: Filter by workflow ID
            status: Filter by status (queued, in_progress, completed)
            limit: Maximum number of results
            
        Returns:
            List of workflow runs
        """
        try:
            repo = self._client.get_repo(repo_name)
            
            if workflow_id:
                workflow = repo.get_workflow(workflow_id)
                runs = workflow.get_runs(status=status) if status else workflow.get_runs()
            else:
                runs = repo.get_workflow_runs(status=status) if status else repo.get_workflow_runs()
            
            return [
                WorkflowRun(
                    id=r.id,
                    name=r.name,
                    status=r.status,
                    conclusion=r.conclusion,
                    html_url=r.html_url,
                    created_at=r.created_at,
                )
                for r in list(runs)[:limit]
            ]
            
        except GithubException as e:
            raise GitHubError(f"Failed to get workflow runs: {e}")
    
    def wait_for_workflow(
        self,
        repo_name: str,
        run_id: int,
        timeout_seconds: int = 600,
        poll_interval: int = 10,
    ) -> WorkflowRun:
        """
        Wait for a workflow run to complete.
        
        Args:
            repo_name: Full repository name
            run_id: Workflow run ID
            timeout_seconds: Maximum wait time
            poll_interval: Seconds between checks
            
        Returns:
            Final workflow run state
        """
        import time
        
        try:
            repo = self._client.get_repo(repo_name)
            start_time = time.time()
            
            while time.time() - start_time < timeout_seconds:
                run = repo.get_workflow_run(run_id)
                
                if run.status == "completed":
                    return WorkflowRun(
                        id=run.id,
                        name=run.name,
                        status=run.status,
                        conclusion=run.conclusion,
                        html_url=run.html_url,
                        created_at=run.created_at,
                    )
                
                time.sleep(poll_interval)
            
            raise GitHubError(f"Workflow run {run_id} timed out")
            
        except GithubException as e:
            raise GitHubError(f"Failed to wait for workflow: {e}")
    
    # ==================== Branch Operations ====================
    
    def create_branch(
        self,
        repo_name: str,
        branch_name: str,
        from_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new branch.
        
        Args:
            repo_name: Full repository name
            branch_name: New branch name
            from_branch: Source branch (defaults to default branch)
            
        Returns:
            Branch information
        """
        try:
            repo = self._client.get_repo(repo_name)
            source = from_branch or repo.default_branch
            
            source_ref = repo.get_git_ref(f"heads/{source}")
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source_ref.object.sha,
            )
            
            logger.info(f"Created branch {branch_name} from {source}")
            
            return {
                "name": branch_name,
                "source": source,
                "sha": source_ref.object.sha,
            }
            
        except GithubException as e:
            raise GitHubError(f"Failed to create branch: {e}")
    
    def delete_branch(self, repo_name: str, branch_name: str) -> bool:
        """
        Delete a branch.
        
        Args:
            repo_name: Full repository name
            branch_name: Branch to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            repo = self._client.get_repo(repo_name)
            ref = repo.get_git_ref(f"heads/{branch_name}")
            ref.delete()
            logger.info(f"Deleted branch {branch_name}")
            return True
        except GithubException as e:
            raise GitHubError(f"Failed to delete branch: {e}")
    
    # ==================== Deployment Environments ====================
    
    def create_environment(
        self,
        repo_name: str,
        environment_name: str,
        wait_timer: int = 0,
        reviewers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a deployment environment.
        
        Args:
            repo_name: Full repository name
            environment_name: Environment name (production, staging, etc.)
            wait_timer: Minutes to wait before deployment
            reviewers: List of reviewer usernames
            
        Returns:
            Environment information
        """
        try:
            repo = self._client.get_repo(repo_name)
            
            # GitHub API for environments
            env = repo.create_environment(environment_name)
            
            return {
                "name": environment_name,
                "url": env.html_url if hasattr(env, 'html_url') else None,
            }
            
        except GithubException as e:
            raise GitHubError(f"Failed to create environment: {e}")
    
    def set_environment_secret(
        self,
        repo_name: str,
        environment_name: str,
        secret_name: str,
        secret_value: str,
    ) -> bool:
        """
        Set an environment-specific secret.
        
        Args:
            repo_name: Full repository name
            environment_name: Environment name
            secret_name: Secret name
            secret_value: Secret value
            
        Returns:
            True if set successfully
        """
        try:
            repo = self._client.get_repo(repo_name)
            repo.create_secret(
                secret_name=secret_name,
                unencrypted_value=secret_value,
                secret_type="environment",
                environment=environment_name,
            )
            return True
        except GithubException as e:
            raise GitHubError(f"Failed to set environment secret: {e}")
