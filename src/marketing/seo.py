"""SEO tools and utilities.

Provides meta tag generation, structured data, sitemaps, and SEO analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urljoin
import re


class PageType(str, Enum):
    """Page type for structured data."""
    
    WEBSITE = "WebSite"
    ARTICLE = "Article"
    PRODUCT = "Product"
    ORGANIZATION = "Organization"
    FAQ = "FAQPage"
    BREADCRUMB = "BreadcrumbList"
    SOFTWARE = "SoftwareApplication"


@dataclass
class SEOConfig:
    """SEO configuration for a website."""
    
    site_name: str
    base_url: str
    default_title: str
    default_description: str
    default_image: str | None = None
    twitter_handle: str | None = None
    locale: str = "en_US"
    keywords: list[str] = field(default_factory=list)


@dataclass
class MetaTags:
    """HTML meta tags for SEO."""
    
    title: str
    description: str
    canonical_url: str
    og_type: str = "website"
    og_image: str | None = None
    twitter_card: str = "summary_large_image"
    twitter_site: str | None = None
    keywords: list[str] = field(default_factory=list)
    robots: str = "index, follow"
    author: str | None = None
    
    def to_html(self) -> str:
        """Generate HTML meta tags."""
        tags = [
            f'<title>{self.title}</title>',
            f'<meta name="description" content="{self.description}">',
            f'<link rel="canonical" href="{self.canonical_url}">',
            f'<meta property="og:title" content="{self.title}">',
            f'<meta property="og:description" content="{self.description}">',
            f'<meta property="og:type" content="{self.og_type}">',
            f'<meta property="og:url" content="{self.canonical_url}">',
            f'<meta name="twitter:card" content="{self.twitter_card}">',
            f'<meta name="robots" content="{self.robots}">',
        ]
        
        if self.og_image:
            tags.append(f'<meta property="og:image" content="{self.og_image}">')
            tags.append(f'<meta name="twitter:image" content="{self.og_image}">')
        
        if self.twitter_site:
            tags.append(f'<meta name="twitter:site" content="{self.twitter_site}">')
        
        if self.keywords:
            tags.append(f'<meta name="keywords" content="{", ".join(self.keywords)}">')
        
        if self.author:
            tags.append(f'<meta name="author" content="{self.author}">')
        
        return "\n".join(tags)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "canonical_url": self.canonical_url,
            "og_type": self.og_type,
            "og_image": self.og_image,
            "twitter_card": self.twitter_card,
            "twitter_site": self.twitter_site,
            "keywords": self.keywords,
            "robots": self.robots,
            "author": self.author,
        }


@dataclass
class StructuredData:
    """JSON-LD structured data for SEO."""
    
    type: PageType
    data: dict[str, Any]
    
    def to_json_ld(self) -> str:
        """Generate JSON-LD script tag."""
        import json
        
        ld_data = {
            "@context": "https://schema.org",
            "@type": self.type.value,
            **self.data,
        }
        
        return f'<script type="application/ld+json">{json.dumps(ld_data, indent=2)}</script>'


@dataclass
class SitemapEntry:
    """Single sitemap entry."""
    
    loc: str
    lastmod: datetime | None = None
    changefreq: str = "weekly"
    priority: float = 0.5


@dataclass
class Sitemap:
    """XML sitemap generator."""
    
    entries: list[SitemapEntry] = field(default_factory=list)
    
    def add(
        self,
        url: str,
        lastmod: datetime | None = None,
        changefreq: str = "weekly",
        priority: float = 0.5,
    ) -> None:
        """Add a URL to the sitemap."""
        self.entries.append(SitemapEntry(
            loc=url,
            lastmod=lastmod,
            changefreq=changefreq,
            priority=priority,
        ))
    
    def to_xml(self) -> str:
        """Generate XML sitemap."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        
        for entry in self.entries:
            lines.append("  <url>")
            lines.append(f"    <loc>{entry.loc}</loc>")
            if entry.lastmod:
                lines.append(f"    <lastmod>{entry.lastmod.strftime('%Y-%m-%d')}</lastmod>")
            lines.append(f"    <changefreq>{entry.changefreq}</changefreq>")
            lines.append(f"    <priority>{entry.priority}</priority>")
            lines.append("  </url>")
        
        lines.append("</urlset>")
        return "\n".join(lines)


@dataclass
class RobotsConfig:
    """Robots.txt configuration."""
    
    user_agents: dict[str, list[str]] = field(default_factory=dict)
    sitemap_url: str | None = None
    crawl_delay: int | None = None
    
    def allow(self, path: str, user_agent: str = "*") -> None:
        """Allow a path for user agent."""
        if user_agent not in self.user_agents:
            self.user_agents[user_agent] = []
        self.user_agents[user_agent].append(f"Allow: {path}")
    
    def disallow(self, path: str, user_agent: str = "*") -> None:
        """Disallow a path for user agent."""
        if user_agent not in self.user_agents:
            self.user_agents[user_agent] = []
        self.user_agents[user_agent].append(f"Disallow: {path}")
    
    def to_text(self) -> str:
        """Generate robots.txt content."""
        lines = []
        
        for user_agent, rules in self.user_agents.items():
            lines.append(f"User-agent: {user_agent}")
            if self.crawl_delay:
                lines.append(f"Crawl-delay: {self.crawl_delay}")
            for rule in rules:
                lines.append(rule)
            lines.append("")
        
        if self.sitemap_url:
            lines.append(f"Sitemap: {self.sitemap_url}")
        
        return "\n".join(lines)


@dataclass
class SEOIssue:
    """SEO issue found during analysis."""
    
    severity: str  # "error", "warning", "info"
    category: str
    message: str
    recommendation: str


@dataclass
class SEOScore:
    """SEO analysis score."""
    
    overall: int  # 0-100
    title: int
    description: int
    headings: int
    images: int
    links: int
    mobile: int
    speed: int
    issues: list[SEOIssue] = field(default_factory=list)


class SEOAnalyzer:
    """Analyze page content for SEO."""
    
    def __init__(self, config: SEOConfig | None = None):
        self.config = config
    
    def analyze_title(self, title: str) -> tuple[int, list[SEOIssue]]:
        """Analyze page title."""
        score = 100
        issues = []
        
        if not title:
            return 0, [SEOIssue(
                severity="error",
                category="title",
                message="Missing page title",
                recommendation="Add a descriptive title tag",
            )]
        
        length = len(title)
        if length < 30:
            score -= 20
            issues.append(SEOIssue(
                severity="warning",
                category="title",
                message=f"Title too short ({length} chars)",
                recommendation="Aim for 50-60 characters",
            ))
        elif length > 60:
            score -= 15
            issues.append(SEOIssue(
                severity="warning",
                category="title",
                message=f"Title too long ({length} chars)",
                recommendation="Keep under 60 characters to avoid truncation",
            ))
        
        return score, issues
    
    def analyze_description(self, description: str) -> tuple[int, list[SEOIssue]]:
        """Analyze meta description."""
        score = 100
        issues = []
        
        if not description:
            return 0, [SEOIssue(
                severity="error",
                category="description",
                message="Missing meta description",
                recommendation="Add a compelling meta description",
            )]
        
        length = len(description)
        if length < 120:
            score -= 20
            issues.append(SEOIssue(
                severity="warning",
                category="description",
                message=f"Description too short ({length} chars)",
                recommendation="Aim for 150-160 characters",
            ))
        elif length > 160:
            score -= 15
            issues.append(SEOIssue(
                severity="warning",
                category="description",
                message=f"Description too long ({length} chars)",
                recommendation="Keep under 160 characters to avoid truncation",
            ))
        
        return score, issues
    
    def analyze_headings(self, html: str) -> tuple[int, list[SEOIssue]]:
        """Analyze heading structure."""
        score = 100
        issues = []
        
        # Check for H1
        h1_matches = re.findall(r'<h1[^>]*>.*?</h1>', html, re.IGNORECASE | re.DOTALL)
        if not h1_matches:
            score -= 30
            issues.append(SEOIssue(
                severity="error",
                category="headings",
                message="Missing H1 heading",
                recommendation="Add exactly one H1 tag per page",
            ))
        elif len(h1_matches) > 1:
            score -= 15
            issues.append(SEOIssue(
                severity="warning",
                category="headings",
                message=f"Multiple H1 headings ({len(h1_matches)})",
                recommendation="Use only one H1 per page",
            ))
        
        return score, issues
    
    def analyze_images(self, html: str) -> tuple[int, list[SEOIssue]]:
        """Analyze image optimization."""
        score = 100
        issues = []
        
        # Find images
        img_matches = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
        
        for img in img_matches:
            if 'alt=' not in img.lower() or 'alt=""' in img.lower():
                score -= 10
                issues.append(SEOIssue(
                    severity="warning",
                    category="images",
                    message="Image missing alt text",
                    recommendation="Add descriptive alt text to all images",
                ))
                break  # Only report once
        
        return max(0, score), issues
    
    def analyze_links(self, html: str, base_url: str) -> tuple[int, list[SEOIssue]]:
        """Analyze link structure."""
        score = 100
        issues = []
        
        # Find links
        link_matches = re.findall(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>', html, re.IGNORECASE)
        
        external_count = 0
        internal_count = 0
        
        for href in link_matches:
            if href.startswith(('http://', 'https://')) and base_url not in href:
                external_count += 1
            elif not href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                internal_count += 1
        
        if internal_count < 3:
            score -= 15
            issues.append(SEOIssue(
                severity="info",
                category="links",
                message=f"Few internal links ({internal_count})",
                recommendation="Add more internal links to improve navigation",
            ))
        
        return score, issues
    
    def analyze(
        self,
        title: str,
        description: str,
        html: str,
        base_url: str = "",
    ) -> SEOScore:
        """Run full SEO analysis."""
        all_issues = []
        
        title_score, title_issues = self.analyze_title(title)
        all_issues.extend(title_issues)
        
        desc_score, desc_issues = self.analyze_description(description)
        all_issues.extend(desc_issues)
        
        heading_score, heading_issues = self.analyze_headings(html)
        all_issues.extend(heading_issues)
        
        img_score, img_issues = self.analyze_images(html)
        all_issues.extend(img_issues)
        
        link_score, link_issues = self.analyze_links(html, base_url)
        all_issues.extend(link_issues)
        
        # Calculate overall score
        overall = int((title_score + desc_score + heading_score + img_score + link_score) / 5)
        
        return SEOScore(
            overall=overall,
            title=title_score,
            description=desc_score,
            headings=heading_score,
            images=img_score,
            links=link_score,
            mobile=80,  # Placeholder - would need browser testing
            speed=80,   # Placeholder - would need performance testing
            issues=all_issues,
        )


def generate_meta_tags(
    config: SEOConfig,
    title: str | None = None,
    description: str | None = None,
    path: str = "/",
    image: str | None = None,
    og_type: str = "website",
) -> MetaTags:
    """Generate meta tags for a page."""
    full_title = title or config.default_title
    if title and config.site_name not in title:
        full_title = f"{title} | {config.site_name}"
    
    return MetaTags(
        title=full_title,
        description=description or config.default_description,
        canonical_url=urljoin(config.base_url, path),
        og_type=og_type,
        og_image=image or config.default_image,
        twitter_site=config.twitter_handle,
        keywords=config.keywords,
    )


def generate_structured_data(
    page_type: PageType,
    name: str,
    description: str,
    url: str,
    **extra: Any,
) -> StructuredData:
    """Generate structured data for a page."""
    data = {
        "name": name,
        "description": description,
        "url": url,
        **extra,
    }
    
    return StructuredData(type=page_type, data=data)


def generate_sitemap(
    base_url: str,
    pages: list[dict[str, Any]],
) -> Sitemap:
    """Generate a sitemap from a list of pages.
    
    Each page should have: path, lastmod (optional), priority (optional)
    """
    sitemap = Sitemap()
    
    for page in pages:
        sitemap.add(
            url=urljoin(base_url, page["path"]),
            lastmod=page.get("lastmod"),
            changefreq=page.get("changefreq", "weekly"),
            priority=page.get("priority", 0.5),
        )
    
    return sitemap


def generate_robots_txt(
    base_url: str,
    disallowed_paths: list[str] | None = None,
    allowed_paths: list[str] | None = None,
    sitemap: bool = True,
) -> RobotsConfig:
    """Generate robots.txt configuration."""
    config = RobotsConfig()
    
    # Default allow all
    config.allow("/")
    
    # Add disallowed paths
    for path in (disallowed_paths or []):
        config.disallow(path)
    
    # Add allowed paths (for paths within disallowed directories)
    for path in (allowed_paths or []):
        config.allow(path)
    
    # Common disallowed paths
    common_disallowed = ["/api/", "/admin/", "/_next/", "/private/"]
    for path in common_disallowed:
        config.disallow(path)
    
    if sitemap:
        config.sitemap_url = urljoin(base_url, "/sitemap.xml")
    
    return config
