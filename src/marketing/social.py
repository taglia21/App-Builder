"""Social media scheduling and posting.

Supports Twitter/X, LinkedIn, and mock provider for testing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import timezone, datetime
from enum import Enum
from typing import Any
import uuid


class SocialPlatform(str, Enum):
    """Social media platforms."""
    
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class PostStatus(str, Enum):
    """Post status."""
    
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass
class SocialMedia:
    """Media attachment for social posts."""
    
    url: str
    media_type: str = "image"  # image, video, gif
    alt_text: str | None = None


@dataclass
class SocialPost:
    """Social media post."""
    
    id: str
    content: str
    platform: SocialPlatform
    status: PostStatus = PostStatus.DRAFT
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    media: list[SocialMedia] = field(default_factory=list)
    url: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        content: str,
        platform: SocialPlatform,
        scheduled_at: datetime | None = None,
        media: list[SocialMedia] | None = None,
    ) -> "SocialPost":
        """Create a new social post."""
        return cls(
            id=str(uuid.uuid4()),
            content=content,
            platform=platform,
            status=PostStatus.SCHEDULED if scheduled_at else PostStatus.DRAFT,
            scheduled_at=scheduled_at,
            media=media or [],
        )


@dataclass
class PostResult:
    """Result of posting to social media."""
    
    success: bool
    post_id: str | None = None
    url: str | None = None
    error: str | None = None
    platform: SocialPlatform | None = None


class SocialProvider(ABC):
    """Base class for social media providers."""
    
    @property
    @abstractmethod
    def platform(self) -> SocialPlatform:
        """Get the platform this provider handles."""
        pass
    
    @abstractmethod
    async def post(self, content: str, media: list[SocialMedia] | None = None) -> PostResult:
        """Publish a post to the platform."""
        pass
    
    @abstractmethod
    async def delete(self, post_id: str) -> bool:
        """Delete a post from the platform."""
        pass
    
    @abstractmethod
    async def get_profile(self) -> dict[str, Any]:
        """Get the authenticated user's profile."""
        pass
    
    def validate_content(self, content: str) -> tuple[bool, str | None]:
        """Validate content for the platform."""
        return True, None


class TwitterProvider(SocialProvider):
    """Twitter/X provider."""
    
    MAX_LENGTH = 280
    
    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        access_token: str | None = None,
        access_secret: str | None = None,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_secret = access_secret
        self._base_url = "https://api.twitter.com/2"
    
    @property
    def platform(self) -> SocialPlatform:
        return SocialPlatform.TWITTER
    
    def validate_content(self, content: str) -> tuple[bool, str | None]:
        """Validate content length for Twitter."""
        if len(content) > self.MAX_LENGTH:
            return False, f"Content exceeds {self.MAX_LENGTH} characters"
        return True, None
    
    async def post(self, content: str, media: list[SocialMedia] | None = None) -> PostResult:
        """Post to Twitter."""
        valid, error = self.validate_content(content)
        if not valid:
            return PostResult(success=False, error=error, platform=self.platform)
        
        if not all([self.api_key, self.access_token]):
            return PostResult(
                success=False,
                error="Twitter credentials not configured",
                platform=self.platform,
            )
        
        try:
            import httpx
            
            # Note: Actual Twitter API requires OAuth 1.0a signing
            # This is a simplified placeholder
            payload = {"text": content}
            
            if media:
                # Would need to upload media first
                payload["media"] = {"media_ids": []}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/tweets",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                
                if response.status_code == 201:
                    data = response.json()
                    tweet_id = data.get("data", {}).get("id", "")
                    return PostResult(
                        success=True,
                        post_id=tweet_id,
                        url=f"https://twitter.com/user/status/{tweet_id}",
                        platform=self.platform,
                    )
                else:
                    return PostResult(
                        success=False,
                        error=response.text,
                        platform=self.platform,
                    )
        except Exception as e:
            return PostResult(success=False, error=str(e), platform=self.platform)
    
    async def delete(self, post_id: str) -> bool:
        """Delete a tweet."""
        if not self.access_token:
            return False
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self._base_url}/tweets/{post_id}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                return response.status_code == 200
        except Exception:
            return False
    
    async def get_profile(self) -> dict[str, Any]:
        """Get Twitter profile."""
        if not self.access_token:
            return {}
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/users/me",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                if response.status_code == 200:
                    return response.json().get("data", {})
        except Exception:
            pass
        
        return {}


class LinkedInProvider(SocialProvider):
    """LinkedIn provider."""
    
    MAX_LENGTH = 3000
    
    def __init__(self, access_token: str | None = None):
        self.access_token = access_token
        self._base_url = "https://api.linkedin.com/v2"
    
    @property
    def platform(self) -> SocialPlatform:
        return SocialPlatform.LINKEDIN
    
    def validate_content(self, content: str) -> tuple[bool, str | None]:
        """Validate content length for LinkedIn."""
        if len(content) > self.MAX_LENGTH:
            return False, f"Content exceeds {self.MAX_LENGTH} characters"
        return True, None
    
    async def post(self, content: str, media: list[SocialMedia] | None = None) -> PostResult:
        """Post to LinkedIn."""
        valid, error = self.validate_content(content)
        if not valid:
            return PostResult(success=False, error=error, platform=self.platform)
        
        if not self.access_token:
            return PostResult(
                success=False,
                error="LinkedIn credentials not configured",
                platform=self.platform,
            )
        
        try:
            import httpx
            
            # Get user URN first
            profile = await self.get_profile()
            user_urn = profile.get("id")
            
            if not user_urn:
                return PostResult(
                    success=False,
                    error="Could not get LinkedIn profile",
                    platform=self.platform,
                )
            
            payload = {
                "author": f"urn:li:person:{user_urn}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                },
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/ugcPosts",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                )
                
                if response.status_code == 201:
                    post_id = response.headers.get("x-restli-id", "")
                    return PostResult(
                        success=True,
                        post_id=post_id,
                        url=f"https://www.linkedin.com/feed/update/{post_id}",
                        platform=self.platform,
                    )
                else:
                    return PostResult(
                        success=False,
                        error=response.text,
                        platform=self.platform,
                    )
        except Exception as e:
            return PostResult(success=False, error=str(e), platform=self.platform)
    
    async def delete(self, post_id: str) -> bool:
        """Delete a LinkedIn post."""
        if not self.access_token:
            return False
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self._base_url}/ugcPosts/{post_id}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                return response.status_code == 204
        except Exception:
            return False
    
    async def get_profile(self) -> dict[str, Any]:
        """Get LinkedIn profile."""
        if not self.access_token:
            return {}
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/me",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        
        return {}


class MockSocialProvider(SocialProvider):
    """Mock social provider for testing."""
    
    def __init__(
        self,
        platform: SocialPlatform = SocialPlatform.TWITTER,
        should_fail: bool = False,
    ):
        self._platform = platform
        self.should_fail = should_fail
        self.posts: list[dict[str, Any]] = []
        self.post_count = 0
    
    @property
    def platform(self) -> SocialPlatform:
        return self._platform
    
    async def post(self, content: str, media: list[SocialMedia] | None = None) -> PostResult:
        """Post (mock)."""
        if self.should_fail:
            return PostResult(
                success=False,
                error="Mock failure",
                platform=self.platform,
            )
        
        self.post_count += 1
        post_id = f"mock_post_{self.post_count}"
        
        self.posts.append({
            "id": post_id,
            "content": content,
            "media": media,
            "platform": self.platform,
            "created_at": datetime.now(timezone.utc),
        })
        
        return PostResult(
            success=True,
            post_id=post_id,
            url=f"https://mock.social/{post_id}",
            platform=self.platform,
        )
    
    async def delete(self, post_id: str) -> bool:
        """Delete (mock)."""
        self.posts = [p for p in self.posts if p["id"] != post_id]
        return True
    
    async def get_profile(self) -> dict[str, Any]:
        """Get profile (mock)."""
        return {
            "id": "mock_user_123",
            "name": "Mock User",
            "username": "mockuser",
            "platform": self.platform.value,
        }


class SocialScheduler:
    """Schedule and manage social media posts."""
    
    def __init__(self, providers: dict[SocialPlatform, SocialProvider] | None = None):
        self.providers = providers or {}
        self.scheduled_posts: list[SocialPost] = []
        self.published_posts: list[SocialPost] = []
    
    def add_provider(self, provider: SocialProvider) -> None:
        """Add a social provider."""
        self.providers[provider.platform] = provider
    
    async def schedule(
        self,
        content: str,
        platform: SocialPlatform,
        scheduled_at: datetime,
        media: list[SocialMedia] | None = None,
    ) -> SocialPost:
        """Schedule a post for later."""
        post = SocialPost.create(
            content=content,
            platform=platform,
            scheduled_at=scheduled_at,
            media=media,
        )
        
        self.scheduled_posts.append(post)
        return post
    
    async def publish_now(
        self,
        content: str,
        platform: SocialPlatform,
        media: list[SocialMedia] | None = None,
    ) -> SocialPost:
        """Publish a post immediately."""
        post = SocialPost.create(content=content, platform=platform, media=media)
        
        provider = self.providers.get(platform)
        if not provider:
            post.status = PostStatus.FAILED
            post.error = f"No provider configured for {platform.value}"
            return post
        
        result = await provider.post(content, media)
        
        if result.success:
            post.status = PostStatus.PUBLISHED
            post.published_at = datetime.now(timezone.utc)
            post.url = result.url
            self.published_posts.append(post)
        else:
            post.status = PostStatus.FAILED
            post.error = result.error
        
        return post
    
    async def publish_scheduled(self) -> list[SocialPost]:
        """Publish all posts that are due."""
        now = datetime.now(timezone.utc)
        published = []
        
        for post in list(self.scheduled_posts):
            if post.scheduled_at and post.scheduled_at <= now:
                provider = self.providers.get(post.platform)
                if not provider:
                    post.status = PostStatus.FAILED
                    post.error = f"No provider for {post.platform.value}"
                    continue
                
                result = await provider.post(post.content, post.media)
                
                if result.success:
                    post.status = PostStatus.PUBLISHED
                    post.published_at = datetime.now(timezone.utc)
                    post.url = result.url
                    self.scheduled_posts.remove(post)
                    self.published_posts.append(post)
                    published.append(post)
                else:
                    post.status = PostStatus.FAILED
                    post.error = result.error
        
        return published
    
    async def cancel(self, post_id: str) -> bool:
        """Cancel a scheduled post."""
        for post in self.scheduled_posts:
            if post.id == post_id:
                self.scheduled_posts.remove(post)
                return True
        return False
    
    async def cross_post(
        self,
        content: str,
        platforms: list[SocialPlatform],
        media: list[SocialMedia] | None = None,
        scheduled_at: datetime | None = None,
    ) -> list[SocialPost]:
        """Post to multiple platforms."""
        posts = []
        
        for platform in platforms:
            if scheduled_at:
                post = await self.schedule(content, platform, scheduled_at, media)
            else:
                post = await self.publish_now(content, platform, media)
            posts.append(post)
        
        return posts
    
    def get_scheduled(self) -> list[SocialPost]:
        """Get all scheduled posts."""
        return sorted(self.scheduled_posts, key=lambda p: p.scheduled_at or datetime.max)
    
    def get_published(self) -> list[SocialPost]:
        """Get all published posts."""
        return sorted(
            self.published_posts,
            key=lambda p: p.published_at or datetime.min,
            reverse=True,
        )


def create_social_scheduler(
    twitter_credentials: dict[str, str] | None = None,
    linkedin_token: str | None = None,
    use_mock: bool = False,
) -> SocialScheduler:
    """Factory function to create social scheduler."""
    scheduler = SocialScheduler()
    
    if use_mock:
        scheduler.add_provider(MockSocialProvider(SocialPlatform.TWITTER))
        scheduler.add_provider(MockSocialProvider(SocialPlatform.LINKEDIN))
        return scheduler
    
    if twitter_credentials:
        scheduler.add_provider(TwitterProvider(**twitter_credentials))
    
    if linkedin_token:
        scheduler.add_provider(LinkedInProvider(access_token=linkedin_token))
    
    return scheduler
