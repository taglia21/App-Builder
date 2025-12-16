"""
GitHub data source for gathering developer intelligence.
"""

from datetime import datetime
from typing import Any, Dict, List

try:
    from github import Github
except ImportError:
    Github = None

from loguru import logger

from ...models import SourceType
from ..base import DataSource, register_source


@register_source("github")
class GitHubSource(DataSource):
    """GitHub source for developer ecosystem insights."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize GitHub source."""
        super().__init__(config)
        self.token = config.get("token")
        self.trending_period = config.get("trending_period", "weekly")
        self.languages = config.get("languages", [])

        if self.enabled and self.token and Github is not None:
            self.client = Github(self.token)
        else:
            self.client = None
            if Github is None:
                logger.warning("PyGithub package not installed. Install with: pip install PyGithub")
            else:
                logger.warning("GitHub source not properly configured")

    def get_source_type(self) -> SourceType:
        """Get source type."""
        return SourceType.GITHUB

    async def gather(self) -> List[Dict[str, Any]]:
        """Gather data from GitHub."""
        if not self.client:
            logger.warning("GitHub client not initialized")
            return []

        all_data = []

        # Get trending repositories
        for language in self.languages:
            try:
                logger.info(f"Gathering trending {language} repositories")

                # Search for repositories created in the last month with high stars
                query = f"language:{language} created:>2024-01-01 stars:>100"
                repos = self.client.search_repositories(query=query, sort="stars", order="desc")

                count = 0
                for repo in repos:
                    if count >= 50:  # Limit per language
                        break

                    # Get issues to understand pain points
                    issues_sample = []
                    try:
                        for issue in repo.get_issues(state="open", sort="comments")[:10]:
                            issues_sample.append(
                                {
                                    "title": issue.title,
                                    "body": issue.body,
                                    "comments": issue.comments,
                                }
                            )
                    except:
                        pass

                    data_point = {
                        "source_type": "github",
                        "source_url": repo.html_url,
                        "name": repo.full_name,
                        "description": repo.description or "",
                        "stars": repo.stargazers_count,
                        "forks": repo.forks_count,
                        "language": repo.language,
                        "topics": repo.get_topics(),
                        "created_at": repo.created_at.isoformat(),
                        "updated_at": repo.updated_at.isoformat(),
                        "open_issues": repo.open_issues_count,
                        "issues_sample": issues_sample,
                        "readme": self._get_readme(repo),
                    }

                    all_data.append(data_point)
                    count += 1

                logger.info(f"Collected {count} repositories for {language}")

            except Exception as e:
                logger.error(f"Error gathering GitHub data for {language}: {e}")
                continue

        logger.info(f"Total GitHub data points collected: {len(all_data)}")
        return all_data

    def _get_readme(self, repo) -> str:
        """Get repository README content."""
        try:
            readme = repo.get_readme()
            return readme.decoded_content.decode("utf-8")[:1000]  # First 1000 chars
        except:
            return ""
