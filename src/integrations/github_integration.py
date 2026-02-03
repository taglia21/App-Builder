import os
from typing import Dict, List

import httpx


class GitHubIntegration:
    """Real GitHub API integration for repository management."""

    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN')
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.token}' if self.token else '',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }

    async def create_repository(self, name: str, description: str = '', private: bool = True) -> Dict:
        """Create a new GitHub repository."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.base_url}/user/repos',
                headers=self.headers,
                json={
                    'name': name,
                    'description': description,
                    'private': private,
                    'auto_init': True
                }
            )
            if response.status_code == 201:
                return {'success': True, 'data': response.json()}
            return {'success': False, 'error': response.json()}

    async def push_files(self, owner: str, repo: str, files: Dict[str, str], branch: str = 'main', message: str = 'Initial commit from LaunchForge') -> Dict:
        """Push multiple files to a repository."""
        try:
            async with httpx.AsyncClient() as client:
                # Get the current commit SHA
                ref_response = await client.get(
                    f'{self.base_url}/repos/{owner}/{repo}/git/refs/heads/{branch}',
                    headers=self.headers
                )
                if ref_response.status_code != 200:
                    # Branch doesn't exist, create it
                    return await self._create_branch_with_files(client, owner, repo, files, branch, message)

                current_sha = ref_response.json()['object']['sha']

                # Get current tree
                commit_response = await client.get(
                    f'{self.base_url}/repos/{owner}/{repo}/git/commits/{current_sha}',
                    headers=self.headers
                )
                tree_sha = commit_response.json()['tree']['sha']

                # Create blobs for each file
                tree_items = []
                for path, content in files.items():
                    blob_response = await client.post(
                        f'{self.base_url}/repos/{owner}/{repo}/git/blobs',
                        headers=self.headers,
                        json={'content': content, 'encoding': 'utf-8'}
                    )
                    if blob_response.status_code == 201:
                        tree_items.append({
                            'path': path,
                            'mode': '100644',
                            'type': 'blob',
                            'sha': blob_response.json()['sha']
                        })

                # Create new tree
                new_tree_response = await client.post(
                    f'{self.base_url}/repos/{owner}/{repo}/git/trees',
                    headers=self.headers,
                    json={'base_tree': tree_sha, 'tree': tree_items}
                )
                new_tree_sha = new_tree_response.json()['sha']

                # Create commit
                commit_response = await client.post(
                    f'{self.base_url}/repos/{owner}/{repo}/git/commits',
                    headers=self.headers,
                    json={
                        'message': message,
                        'tree': new_tree_sha,
                        'parents': [current_sha]
                    }
                )
                new_commit_sha = commit_response.json()['sha']

                # Update reference
                await client.patch(
                    f'{self.base_url}/repos/{owner}/{repo}/git/refs/heads/{branch}',
                    headers=self.headers,
                    json={'sha': new_commit_sha}
                )

                return {'success': True, 'commit_sha': new_commit_sha}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _create_branch_with_files(self, client, owner, repo, files, branch, message):
        """Create a new branch with files when branch doesn't exist."""
        # Create initial tree
        tree_items = []
        for path, content in files.items():
            blob_response = await client.post(
                f'{self.base_url}/repos/{owner}/{repo}/git/blobs',
                headers=self.headers,
                json={'content': content, 'encoding': 'utf-8'}
            )
            if blob_response.status_code == 201:
                tree_items.append({
                    'path': path,
                    'mode': '100644',
                    'type': 'blob',
                    'sha': blob_response.json()['sha']
                })

        tree_response = await client.post(
            f'{self.base_url}/repos/{owner}/{repo}/git/trees',
            headers=self.headers,
            json={'tree': tree_items}
        )
        tree_sha = tree_response.json()['sha']

        commit_response = await client.post(
            f'{self.base_url}/repos/{owner}/{repo}/git/commits',
            headers=self.headers,
            json={'message': message, 'tree': tree_sha, 'parents': []}
        )
        commit_sha = commit_response.json()['sha']

        await client.post(
            f'{self.base_url}/repos/{owner}/{repo}/git/refs',
            headers=self.headers,
            json={'ref': f'refs/heads/{branch}', 'sha': commit_sha}
        )

        return {'success': True, 'commit_sha': commit_sha}

    async def get_user_repos(self) -> List[Dict]:
        """Get list of user's repositories."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.base_url}/user/repos',
                headers=self.headers,
                params={'sort': 'updated', 'per_page': 100}
            )
            if response.status_code == 200:
                return response.json()
            return []

    async def delete_repository(self, owner: str, repo: str) -> Dict:
        """Delete a repository."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f'{self.base_url}/repos/{owner}/{repo}',
                headers=self.headers
            )
            return {'success': response.status_code == 204}
