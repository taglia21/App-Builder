"""
Data processing pipeline for extracting insights from raw data.
"""

import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Tuple
from uuid import uuid4

import numpy as np
from loguru import logger
from sklearn.cluster import DBSCAN, KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from textblob import TextBlob

from ..models import (
    CompetitionDensity,
    CompetitorAnalysis,
    EmergingIndustry,
    OpportunityCategory,
    PainPoint,
    SourceType,
)


class DataProcessor:
    """Process raw data into structured intelligence."""

    def __init__(self):
        """Initialize the processor."""
        self.vectorizer = TfidfVectorizer(
            max_features=1000, stop_words="english", ngram_range=(1, 2)
        )

    def process_pain_points(self, raw_data: List[Dict[str, Any]]) -> List[PainPoint]:
        """Extract and structure pain points from raw data."""
        logger.info("Processing pain points from raw data")

        pain_points = []

        for data_point in raw_data:
            source_type = data_point.get("source_type", "")

            # Extract text content
            texts = self._extract_texts(data_point)

            # Analyze each text for pain points
            for text in texts:
                if self._is_pain_point(text):
                    pain_point = self._create_pain_point(text, data_point)
                    if pain_point:
                        pain_points.append(pain_point)

        # Cluster similar pain points
        pain_points = self._cluster_pain_points(pain_points)

        logger.info(f"Extracted {len(pain_points)} pain points")
        return pain_points

    def _extract_texts(self, data_point: Dict[str, Any]) -> List[str]:
        """Extract text content from various data point structures."""
        texts = []

        # Title
        if "title" in data_point:
            texts.append(data_point["title"])

        # Content
        if "content" in data_point:
            texts.append(data_point["content"])

        # Description
        if "description" in data_point:
            texts.append(data_point["description"])

        # Snippet
        if "snippet" in data_point:
            texts.append(data_point["snippet"])

        # Comments
        if "comments" in data_point:
            if isinstance(data_point["comments"], list):
                texts.extend(data_point["comments"])

        # Top comments
        if "top_comments" in data_point:
            if isinstance(data_point["top_comments"], list):
                texts.extend(data_point["top_comments"])

        return [t for t in texts if t and len(t) > 20]

    def _is_pain_point(self, text: str) -> bool:
        """Determine if text describes a pain point."""
        pain_indicators = [
            r"\bi wish\b",
            r"\bwhy (isn't|isnt|aren't|arent)\b",
            r"\bfrustrat(ed|ing)\b",
            r"\bproblem with\b",
            r"\bhate that\b",
            r"\bannoying\b",
            r"\bneed (a|an) (tool|solution|way)\b",
            r"\blooking for\b",
            r"\bstruggl(e|ing)\b",
            r"\bdifficult to\b",
            r"\bhard to\b",
            r"\bcan'?t find\b",
            r"\bdoesn'?t exist\b",
            r"\bshould be easier\b",
            r"\bwaste(s|ing) time\b",
            r"\btakes? (too )?(long|much time)\b",
        ]

        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in pain_indicators)

    def _create_pain_point(
        self, text: str, data_point: Dict[str, Any]
    ) -> PainPoint | None:
        """Create a PainPoint object from text and metadata."""
        try:
            # Sentiment analysis
            blob = TextBlob(text)
            sentiment = blob.sentiment.polarity

            # Calculate urgency score based on sentiment and keywords
            urgency_keywords = [
                "critical",
                "urgent",
                "immediately",
                "asap",
                "blocker",
                "emergency",
            ]
            urgency_score = 0.5  # Base score
            for keyword in urgency_keywords:
                if keyword in text.lower():
                    urgency_score += 0.1
            urgency_score = min(urgency_score, 1.0)

            # Extract keywords
            keywords = self._extract_keywords(text)

            # Determine affected industries (simplified)
            industries = self._identify_industries(text)

            pain_point = PainPoint(
                id=uuid4(),
                description=text[:500],  # Limit length
                source_type=SourceType(data_point.get("source_type", "reddit")),
                source_url=data_point.get("source_url", ""),
                frequency_count=1,
                urgency_score=urgency_score,
                sentiment_score=sentiment,
                affected_industries=industries,
                affected_user_personas=[],
                keywords=keywords,
                raw_excerpts=[text[:200]],
            )

            return pain_point

        except Exception as e:
            logger.debug(f"Error creating pain point: {e}")
            return None

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction using word frequency
        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        common_words = {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "from",
            "have",
            "not",
            "are",
            "was",
            "but",
        }
        words = [w for w in words if w not in common_words]

        word_freq = Counter(words)
        return [word for word, _ in word_freq.most_common(max_keywords)]

    def _identify_industries(self, text: str) -> List[str]:
        """Identify industries mentioned in text."""
        industry_keywords = {
            "software": ["software", "saas", "app", "platform"],
            "healthcare": ["healthcare", "medical", "health", "hospital"],
            "finance": ["finance", "banking", "fintech", "payment"],
            "education": ["education", "learning", "school", "university"],
            "ecommerce": ["ecommerce", "retail", "shopping", "store"],
            "marketing": ["marketing", "advertising", "seo", "content"],
            "sales": ["sales", "crm", "pipeline", "lead"],
            "hr": ["hr", "recruiting", "hiring", "employee"],
            "real_estate": ["real estate", "property", "housing"],
            "logistics": ["logistics", "shipping", "supply chain", "warehouse"],
        }

        text_lower = text.lower()
        industries = []

        for industry, keywords in industry_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                industries.append(industry)

        return industries

    def _cluster_pain_points(self, pain_points: List[PainPoint]) -> List[PainPoint]:
        """Cluster similar pain points and merge them."""
        if len(pain_points) < 2:
            return pain_points

        # Extract descriptions for clustering
        descriptions = [pp.description for pp in pain_points]

        try:
            # TF-IDF vectorization
            vectors = self.vectorizer.fit_transform(descriptions)

            # DBSCAN clustering
            clustering = DBSCAN(eps=0.3, min_samples=2, metric="cosine")
            labels = clustering.fit_predict(vectors.toarray())

            # Merge pain points in the same cluster
            clusters = {}
            for idx, label in enumerate(labels):
                if label == -1:  # Noise point
                    continue

                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(pain_points[idx])

            # Merge clustered pain points
            merged_pain_points = []

            # Add unclustered points
            for idx, label in enumerate(labels):
                if label == -1:
                    merged_pain_points.append(pain_points[idx])

            # Add merged clusters
            for label, cluster_points in clusters.items():
                # Take the first point as the representative
                merged = cluster_points[0]
                merged.frequency_count = len(cluster_points)

                # Merge keywords
                all_keywords = set()
                for pp in cluster_points:
                    all_keywords.update(pp.keywords)
                merged.keywords = list(all_keywords)[:20]

                # Merge industries
                all_industries = set()
                for pp in cluster_points:
                    all_industries.update(pp.affected_industries)
                merged.affected_industries = list(all_industries)

                merged_pain_points.append(merged)

            return merged_pain_points

        except Exception as e:
            logger.warning(f"Error clustering pain points: {e}")
            return pain_points

    def extract_emerging_industries(
        self, raw_data: List[Dict[str, Any]]
    ) -> List[EmergingIndustry]:
        """Extract emerging industry information."""
        logger.info("Extracting emerging industries")

        # Count industry mentions
        industry_mentions = Counter()
        industry_signals = {}

        for data_point in raw_data:
            texts = self._extract_texts(data_point)
            for text in texts:
                industries = self._identify_industries(text)
                for industry in industries:
                    industry_mentions[industry] += 1

                    if industry not in industry_signals:
                        industry_signals[industry] = {
                            "signals": [],
                            "key_players": set(),
                            "tech_trends": set(),
                        }

                    # Extract growth signals
                    if any(
                        word in text.lower()
                        for word in ["growing", "emerging", "trending", "funding"]
                    ):
                        industry_signals[industry]["signals"].append(text[:100])

        # Create EmergingIndustry objects
        emerging = []
        for industry, count in industry_mentions.most_common(10):
            if count < 5:  # Minimum mentions
                continue

            signals = industry_signals[industry]
            opportunity_score = min(count / 100.0, 1.0)

            emerging.append(
                EmergingIndustry(
                    id=uuid4(),
                    industry_name=industry,
                    growth_signals=signals["signals"][:10],
                    funding_activity="Active",
                    key_players=list(signals["key_players"])[:10],
                    technology_stack_trends=list(signals["tech_trends"])[:10],
                    opportunity_score=opportunity_score,
                )
            )

        logger.info(f"Identified {len(emerging)} emerging industries")
        return emerging

    def create_opportunity_categories(
        self, pain_points: List[PainPoint], emerging_industries: List[EmergingIndustry]
    ) -> List[OpportunityCategory]:
        """Create opportunity categories from pain points and industries."""
        logger.info("Creating opportunity categories")

        # Group pain points by industry
        industry_pain_points = {}

        for pp in pain_points:
            for industry in pp.affected_industries:
                if industry not in industry_pain_points:
                    industry_pain_points[industry] = []
                industry_pain_points[industry].append(pp.id)

        # Create categories
        categories = []

        for industry, pp_ids in industry_pain_points.items():
            if len(pp_ids) < 3:  # Minimum pain points
                continue

            # Calculate automation potential (average of pain points)
            relevant_pps = [pp for pp in pain_points if pp.id in pp_ids]
            avg_urgency = (
                sum(pp.urgency_score for pp in relevant_pps) / len(relevant_pps)
                if relevant_pps
                else 0.5
            )

            category = OpportunityCategory(
                category_name=industry,
                subcategories=[],
                pain_point_ids=pp_ids,
                market_size_estimate="To be determined",
                competition_density=CompetitionDensity.MEDIUM,
                automation_potential=avg_urgency,
            )

            categories.append(category)

        logger.info(f"Created {len(categories)} opportunity categories")
        return categories
