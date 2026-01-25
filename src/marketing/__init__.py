"""SEO & Marketing Module.

Tools for search engine optimization, analytics, and marketing automation.
"""

from src.marketing.seo import (
    SEOConfig,
    MetaTags,
    StructuredData,
    Sitemap,
    RobotsConfig,
    SEOAnalyzer,
    generate_meta_tags,
    generate_structured_data,
    generate_sitemap,
    generate_robots_txt,
)
from src.marketing.analytics import (
    AnalyticsConfig,
    AnalyticsProvider,
    GoogleAnalytics,
    PlausibleAnalytics,
    MixpanelAnalytics,
    AnalyticsTracker,
    create_tracker,
)
from src.marketing.email import (
    EmailTemplate,
    EmailCampaign,
    EmailProvider,
    ResendProvider,
    SendGridProvider,
    MockEmailProvider,
    EmailService,
    create_email_service,
)
from src.marketing.social import (
    SocialPlatform,
    SocialPost,
    SocialProvider,
    TwitterProvider,
    LinkedInProvider,
    MockSocialProvider,
    SocialScheduler,
    create_social_scheduler,
)

__all__ = [
    # SEO
    "SEOConfig",
    "MetaTags",
    "StructuredData",
    "Sitemap",
    "RobotsConfig",
    "SEOAnalyzer",
    "generate_meta_tags",
    "generate_structured_data",
    "generate_sitemap",
    "generate_robots_txt",
    # Analytics
    "AnalyticsConfig",
    "AnalyticsProvider",
    "GoogleAnalytics",
    "PlausibleAnalytics",
    "MixpanelAnalytics",
    "AnalyticsTracker",
    "create_tracker",
    # Email
    "EmailTemplate",
    "EmailCampaign",
    "EmailProvider",
    "ResendProvider",
    "SendGridProvider",
    "MockEmailProvider",
    "EmailService",
    "create_email_service",
    # Social
    "SocialPlatform",
    "SocialPost",
    "SocialProvider",
    "TwitterProvider",
    "LinkedInProvider",
    "MockSocialProvider",
    "SocialScheduler",
    "create_social_scheduler",
]
