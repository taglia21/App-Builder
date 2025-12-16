"""Enhanced prompts for idea generation."""

IDEA_GENERATION_SYSTEM_PROMPT = """You are a visionary startup founder and Y Combinator partner with expertise in identifying billion-dollar opportunities.

Your task is to generate NOVEL, INNOVATIVE startup ideas that:
1. Solve REAL pain points (provided in the data)
2. Are NOT just copies of existing tools
3. Have unique angles or approaches
4. Could become venture-scale businesses ($100M+ potential)
5. Leverage modern technology (AI, automation, APIs)

IMPORTANT GUIDELINES:
- Don't just suggest "an AI version of X" - be more creative
- Combine pain points in unexpected ways
- Think about underserved niches
- Consider workflow integrations others miss
- Look for "10x better" not "slightly improved"
"""

IDEA_GENERATION_USER_PROMPT = """Based on these real market pain points collected from Reddit, GitHub, and news sources:

{pain_points_summary}

Generate {num_ideas} innovative startup ideas. For each idea provide:

1. **Name**: Catchy, memorable product name
2. **One-liner**: Single sentence pitch (max 10 words)
3. **Problem**: Specific pain point being solved (reference the data)
4. **Solution**: How it works (be specific, not generic)
5. **Target Customer**: Exact buyer persona with job title
6. **Unique Angle**: What makes this different from existing solutions
7. **Revenue Model**: How it makes money (subscription, usage, transaction, etc.)
8. **TAM Estimate**: Total addressable market size
9. **Why Now**: Why this is the right time for this solution
10. **Moat**: Defensibility (data, network effects, switching costs, etc.)

Focus on ideas that are:
- Specific (not generic "AI for X")
- Actionable (could be built in 3-6 months MVP)
- Differentiated (not already crowded market)
- Scalable (software, not services)

Return as JSON array.
"""

PAIN_POINT_SUMMARY_TEMPLATE = """
### Pain Point {index}
- **Source**: {source_type}
- **Description**: {description}
- **Urgency**: {urgency_score}/1.0
- **Industries**: {industries}
- **Keywords**: {keywords}
"""
