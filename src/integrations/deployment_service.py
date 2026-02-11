"""
Real deployment service for Railway and Vercel.

Railway path: create GitHub repo -> push files -> Railway project + service + domain + deploy.
Vercel path:  base64-encode files -> POST /v13/deployments.
"""

import base64
import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class DeploymentService:
    """Orchestrates real deployments to Railway or Vercel."""

    def __init__(self):
        self.railway_token = os.environ.get("RAILWAY_TOKEN")
        self.vercel_token = os.environ.get("VERCEL_TOKEN")
        self.github_token = os.environ.get("GITHUB_TOKEN")
        self.railway_api = "https://backboard.railway.app/graphql/v2"

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def deploy(
        self,
        project_name: str,
        files: Dict[str, str],
        platform: str = "railway",
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Deploy generated code to *platform*.

        Args:
            project_name: Slug-safe project name (e.g. "my-todo-app")
            files: Mapping of filepath -> file-content produced by the code generator
            platform: "railway" or "vercel"
            env_vars: Optional env-vars to set on the deployment

        Returns:
            Dict with at least {success, url | error}.
        """
        if not files:
            return {"success": False, "error": "No files to deploy"}

        if platform == "vercel":
            return await self._deploy_to_vercel(project_name, files)
        else:
            return await self._deploy_to_railway(project_name, files, env_vars)

    # ------------------------------------------------------------------
    # Railway  (GitHub repo -> Railway project -> service -> domain -> deploy)
    # ------------------------------------------------------------------

    async def _deploy_to_railway(
        self,
        project_name: str,
        files: Dict[str, str],
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not self.railway_token:
            return {
                "success": False,
                "error": "RAILWAY_TOKEN is not configured. Set it in your environment variables.",
            }
        if not self.github_token:
            return {
                "success": False,
                "error": "GITHUB_TOKEN is not configured. Railway deployments require a GitHub repo. Set GITHUB_TOKEN in your environment variables.",
            }

        try:
            # Step 1 - Create a GitHub repo and push the generated files
            repo_full_name = await self._create_github_repo_with_files(project_name, files)
            logger.info("Created GitHub repo %s", repo_full_name)

            # Step 2 - Use the complete Railway deployment pipeline
            from src.integrations.railway_deployment import RailwayDeploymentService

            railway = RailwayDeploymentService()
            result = await railway.deploy_app(
                app_name=project_name,
                github_repo=repo_full_name,
                env_vars=env_vars,
            )

            if result.get("success"):
                return {
                    "success": True,
                    "url": result["url"],
                    "dashboard_url": f"https://railway.app/project/{result['project_id']}",
                    "github_url": f"https://github.com/{repo_full_name}",
                    "project_id": result["project_id"],
                    "message": "Successfully deployed to Railway!",
                }

            return {
                "success": False,
                "error": result.get("error", "Railway deployment failed"),
                "github_url": f"https://github.com/{repo_full_name}",
            }

        except Exception as e:
            logger.error("Railway deployment error: %s", e)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Vercel  (direct file upload via API)
    # ------------------------------------------------------------------

    async def _deploy_to_vercel(
        self,
        project_name: str,
        files: Dict[str, str],
    ) -> Dict[str, Any]:
        if not self.vercel_token:
            return {
                "success": False,
                "error": "VERCEL_TOKEN is not configured. Set it in your environment variables.",
            }

        try:
            # Vercel /v13/deployments accepts files with base64-encoded data
            vercel_files = []
            for path, content in files.items():
                encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
                vercel_files.append({"file": path, "data": encoded, "encoding": "base64"})

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.vercel.com/v13/deployments",
                    headers={
                        "Authorization": f"Bearer {self.vercel_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "name": project_name,
                        "files": vercel_files,
                        "projectSettings": {
                            "framework": None,
                        },
                    },
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    url = data.get("url", "")
                    if url and not url.startswith("https://"):
                        url = f"https://{url}"
                    return {
                        "success": True,
                        "deployment_id": data.get("id"),
                        "url": url,
                        "ready_state": data.get("readyState"),
                        "message": "Successfully deployed to Vercel!",
                    }

                error_body = response.text
                logger.error("Vercel deploy failed (%s): %s", response.status_code, error_body)
                return {
                    "success": False,
                    "error": f"Vercel API returned {response.status_code}: {error_body}",
                }

        except Exception as e:
            logger.error("Vercel deployment error: %s", e)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # GitHub helpers  (async, using httpx against the REST API)
    # ------------------------------------------------------------------

    async def _create_github_repo_with_files(
        self,
        project_name: str,
        files: Dict[str, str],
    ) -> str:
        """
        Create a **private** GitHub repo named *project_name* and push all
        *files* in a single commit using the Git Data API (tree + commit).

        Returns the repo full_name (``owner/repo``).
        """
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with httpx.AsyncClient(
            base_url="https://api.github.com", headers=headers, timeout=30.0
        ) as gh:
            # 1. Create repo (auto_init to get a default branch + initial commit)
            resp = await gh.post(
                "/user/repos",
                json={
                    "name": project_name,
                    "private": True,
                    "auto_init": True,
                    "description": "Generated by Valeric App Builder",
                },
            )

            if resp.status_code == 422:
                # Repo already exists - use it
                user_resp = await gh.get("/user")
                owner = user_resp.json()["login"]
                full_name = f"{owner}/{project_name}"
                logger.info("Repo %s already exists, pushing to it", full_name)
            elif resp.status_code in (200, 201):
                full_name = resp.json()["full_name"]
            else:
                raise RuntimeError(
                    f"GitHub repo creation failed ({resp.status_code}): {resp.text}"
                )

            # 2. Get the SHA of the current HEAD commit on the default branch
            import asyncio

            ref_resp = await gh.get(f"/repos/{full_name}/git/ref/heads/main")
            if ref_resp.status_code != 200:
                # Might still be initializing - wait briefly
                await asyncio.sleep(2)
                ref_resp = await gh.get(f"/repos/{full_name}/git/ref/heads/main")

            if ref_resp.status_code != 200:
                raise RuntimeError(
                    f"Could not resolve HEAD for {full_name}: {ref_resp.text}"
                )

            head_sha = ref_resp.json()["object"]["sha"]

            # 3. Get the tree SHA of that commit
            commit_resp = await gh.get(
                f"/repos/{full_name}/git/commits/{head_sha}"
            )
            base_tree_sha = commit_resp.json()["tree"]["sha"]

            # 4. Build the tree entries (blobs created inline)
            tree_items = []
            for path, content in files.items():
                blob_resp = await gh.post(
                    f"/repos/{full_name}/git/blobs",
                    json={"content": content, "encoding": "utf-8"},
                )
                if blob_resp.status_code != 201:
                    logger.warning(
                        "Blob creation failed for %s: %s", path, blob_resp.text
                    )
                    continue
                tree_items.append(
                    {
                        "path": path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_resp.json()["sha"],
                    }
                )

            if not tree_items:
                raise RuntimeError("No files could be uploaded to GitHub")

            # 5. Create the tree
            tree_resp = await gh.post(
                f"/repos/{full_name}/git/trees",
                json={"base_tree": base_tree_sha, "tree": tree_items},
            )
            if tree_resp.status_code != 201:
                raise RuntimeError(f"Tree creation failed: {tree_resp.text}")
            new_tree_sha = tree_resp.json()["sha"]

            # 6. Create the commit
            commit_create_resp = await gh.post(
                f"/repos/{full_name}/git/commits",
                json={
                    "message": "Initial app code from Valeric",
                    "tree": new_tree_sha,
                    "parents": [head_sha],
                },
            )
            if commit_create_resp.status_code != 201:
                raise RuntimeError(
                    f"Commit creation failed: {commit_create_resp.text}"
                )
            new_commit_sha = commit_create_resp.json()["sha"]

            # 7. Update HEAD ref to point to the new commit
            update_resp = await gh.patch(
                f"/repos/{full_name}/git/refs/heads/main",
                json={"sha": new_commit_sha},
            )
            if update_resp.status_code != 200:
                raise RuntimeError(f"Ref update failed: {update_resp.text}")

            logger.info("Pushed %d files to %s", len(tree_items), full_name)
            return full_name

    # ------------------------------------------------------------------
    # Backward-compatible wrappers (used by deploy_start_api)
    # ------------------------------------------------------------------

    async def deploy_to_railway(
        self, project_name: str, files: Dict[str, str], env_vars: Dict[str, str] = None
    ) -> Dict:
        return await self._deploy_to_railway(project_name, files, env_vars)

    async def deploy_to_vercel(self, project_name: str, files: Dict[str, str]) -> Dict:
        return await self._deploy_to_vercel(project_name, files)

    async def get_deployment_status(self, project_id: str) -> Dict:
        """Get deployment status from Railway."""
        if not self.railway_token:
            return {"success": False, "error": "Railway token not configured"}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                query = """
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
                """
                response = await client.post(
                    self.railway_api,
                    headers={
                        "Authorization": f"Bearer {self.railway_token}",
                        "Content-Type": "application/json",
                    },
                    json={"query": query, "variables": {"id": project_id}},
                )
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                return {"success": False, "error": "Failed to get status"}
        except Exception as e:
            return {"success": False, "error": str(e)}
