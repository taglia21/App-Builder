"""
Realistic demo data for testing the pipeline without API calls.
This data simulates what would be gathered from real intelligence sources.
"""

from datetime import datetime, timedelta
import random

# ============================================================================
# PAIN POINTS - Extracted from Reddit, Twitter, Forums
# ============================================================================

DEMO_PAIN_POINTS = [
    {
        "id": "pp-001",
        "description": "Small business owners spend 10-15 hours weekly manually reconciling invoices across Stripe, PayPal, and bank accounts. No single tool handles multi-platform reconciliation well.",
        "source_type": "reddit",
        "source_url": "https://reddit.com/r/smallbusiness/comments/example1",
        "frequency_count": 1247,
        "urgency_score": 0.87,
        "sentiment_score": -0.72,
        "affected_industries": ["e-commerce", "retail", "professional services", "freelance"],
        "affected_user_personas": ["small business owner", "bookkeeper", "freelancer", "accountant"],
        "keywords": ["invoice", "reconciliation", "stripe", "paypal", "accounting", "automation", "bookkeeping", "time-consuming", "manual"],
        "raw_excerpts": [
            "I spend every Sunday reconciling invoices. There has to be a better way.",
            "Why can't one tool just pull from Stripe, PayPal, and my bank automatically?",
            "Hired a bookkeeper just for reconciliation. $2k/month down the drain."
        ]
    },
    {
        "id": "pp-002", 
        "description": "Engineering managers lack visibility into actual developer productivity. JIRA tickets don't reflect real output, and they need metrics without micromanaging.",
        "source_type": "twitter",
        "source_url": "https://twitter.com/example/status/123",
        "frequency_count": 892,
        "urgency_score": 0.75,
        "sentiment_score": -0.58,
        "affected_industries": ["software", "technology", "startups", "enterprise IT"],
        "affected_user_personas": ["engineering manager", "VP engineering", "CTO", "tech lead"],
        "keywords": ["developer productivity", "engineering metrics", "JIRA", "velocity", "sprint", "performance", "visibility", "management"],
        "raw_excerpts": [
            "JIRA velocity is meaningless. I need to know who's actually shipping.",
            "How do I measure productivity without installing spyware on their machines?",
            "My board wants engineering metrics but everything I show them is gaming-able."
        ]
    },
    {
        "id": "pp-003",
        "description": "Sales teams waste 5+ hours weekly on CRM data entry. Salesforce and HubSpot require manual logging of calls, emails, and meeting notes.",
        "source_type": "reddit",
        "source_url": "https://reddit.com/r/sales/comments/example2",
        "frequency_count": 2103,
        "urgency_score": 0.91,
        "sentiment_score": -0.81,
        "affected_industries": ["SaaS", "enterprise sales", "real estate", "financial services", "insurance"],
        "affected_user_personas": ["sales rep", "account executive", "sales manager", "SDR", "BDR"],
        "keywords": ["CRM", "salesforce", "hubspot", "data entry", "logging", "automation", "sales productivity", "admin work"],
        "raw_excerpts": [
            "I'm a seller, not a data entry clerk. Salesforce is killing my quota.",
            "Spent 2 hours logging calls today. That's 2 hours I didn't spend selling.",
            "Our CRM adoption is 40% because reps refuse to do the admin work."
        ]
    },
    {
        "id": "pp-004",
        "description": "HR teams at mid-size companies (50-500 employees) struggle with employee onboarding. Process involves 15+ tools, manual checklist tracking, and things constantly fall through cracks.",
        "source_type": "reddit",
        "source_url": "https://reddit.com/r/humanresources/comments/example3",
        "frequency_count": 756,
        "urgency_score": 0.79,
        "sentiment_score": -0.64,
        "affected_industries": ["all industries", "technology", "healthcare", "finance", "manufacturing"],
        "affected_user_personas": ["HR manager", "people ops", "HR coordinator", "office manager"],
        "keywords": ["onboarding", "new hire", "HR", "checklist", "orientation", "paperwork", "compliance", "training"],
        "raw_excerpts": [
            "New hire starts Monday and IT still hasn't created their accounts.",
            "Our onboarding checklist is a 47-item spreadsheet. Things get missed constantly.",
            "It takes 3 weeks to fully onboard someone. Should take 3 days."
        ]
    },
    {
        "id": "pp-005",
        "description": "Content marketers can't measure which blog posts actually drive revenue. Google Analytics shows traffic but not pipeline attribution.",
        "source_type": "twitter",
        "source_url": "https://twitter.com/example/status/456",
        "frequency_count": 634,
        "urgency_score": 0.68,
        "sentiment_score": -0.52,
        "affected_industries": ["SaaS", "B2B", "marketing agencies", "media"],
        "affected_user_personas": ["content marketer", "marketing manager", "CMO", "demand gen manager"],
        "keywords": ["content marketing", "attribution", "ROI", "analytics", "blog", "pipeline", "revenue", "measurement"],
        "raw_excerpts": [
            "CEO asks which blog posts make money. I have no idea.",
            "We publish 20 posts/month. No clue which ones actually drive demos.",
            "Marketing attribution is broken. First-touch, last-touch, it's all wrong."
        ]
    },
    {
        "id": "pp-006",
        "description": "Customer success teams don't know which accounts are at risk of churning until it's too late. Health scores are lagging indicators based on outdated data.",
        "source_type": "reddit",
        "source_url": "https://reddit.com/r/CustomerSuccess/comments/example4",
        "frequency_count": 1089,
        "urgency_score": 0.85,
        "sentiment_score": -0.69,
        "affected_industries": ["SaaS", "subscription businesses", "telecom", "insurance"],
        "affected_user_personas": ["customer success manager", "CSM", "VP customer success", "account manager"],
        "keywords": ["churn", "retention", "health score", "customer success", "risk", "prediction", "renewal", "NRR"],
        "raw_excerpts": [
            "Found out a $200k account was churning when they sent the cancellation email.",
            "Our health scores are useless. Green accounts churn, red accounts renew.",
            "I need to know 90 days before renewal if there's a problem, not 9 days."
        ]
    },
    {
        "id": "pp-007",
        "description": "Agencies struggle to give clients real-time project visibility. Status updates are manual, clients constantly ask 'where are we?', PMs spend hours on reporting.",
        "source_type": "reddit",
        "source_url": "https://reddit.com/r/agencies/comments/example5",
        "frequency_count": 521,
        "urgency_score": 0.72,
        "sentiment_score": -0.55,
        "affected_industries": ["marketing agencies", "creative agencies", "consulting", "software agencies"],
        "affected_user_personas": ["project manager", "account manager", "agency owner", "client services"],
        "keywords": ["client reporting", "project status", "agency", "transparency", "dashboard", "updates", "communication"],
        "raw_excerpts": [
            "I spend every Friday building status reports instead of doing actual work.",
            "Clients ask for updates 5x per week. I don't have time for this.",
            "Lost a client because they felt 'out of the loop'. Communication is killing us."
        ]
    },
    {
        "id": "pp-008",
        "description": "Legal teams at startups review the same contract types repeatedly (NDAs, MSAs, SOWs) but can't build institutional knowledge. Each review starts from scratch.",
        "source_type": "twitter",
        "source_url": "https://twitter.com/example/status/789",
        "frequency_count": 412,
        "urgency_score": 0.77,
        "sentiment_score": -0.61,
        "affected_industries": ["technology", "startups", "legal services", "enterprise"],
        "affected_user_personas": ["general counsel", "legal ops", "contract manager", "startup founder"],
        "keywords": ["contract review", "legal", "NDA", "MSA", "redlining", "legal ops", "CLM", "contract management"],
        "raw_excerpts": [
            "Reviewed our 500th NDA this year. Still doing it manually like it's 1999.",
            "Our outside counsel charges $500/hr to review boilerplate contracts.",
            "I know we've seen this clause before but can't find the precedent."
        ]
    },
    {
        "id": "pp-009",
        "description": "Ecommerce brands can't get a unified view of inventory across Shopify, Amazon, and wholesale channels. Overselling and stockouts are constant problems.",
        "source_type": "reddit",
        "source_url": "https://reddit.com/r/ecommerce/comments/example6",
        "frequency_count": 1876,
        "urgency_score": 0.89,
        "sentiment_score": -0.77,
        "affected_industries": ["e-commerce", "retail", "wholesale", "D2C brands"],
        "affected_user_personas": ["ecommerce manager", "operations manager", "founder", "inventory planner"],
        "keywords": ["inventory", "shopify", "amazon", "multichannel", "stockout", "overselling", "sync", "warehouse"],
        "raw_excerpts": [
            "Sold 50 units on Amazon that we didn't have. Now my account is at risk.",
            "Inventory sync between Shopify and Amazon is always 2 hours behind.",
            "Hired someone full-time just to manage inventory spreadsheets across channels."
        ]
    },
    {
        "id": "pp-010",
        "description": "Recruiting teams lose candidates to slow processes. Time from application to offer is 30+ days when candidates expect 7-14 days.",
        "source_type": "reddit",
        "source_url": "https://reddit.com/r/recruiting/comments/example7",
        "frequency_count": 943,
        "urgency_score": 0.83,
        "sentiment_score": -0.66,
        "affected_industries": ["technology", "healthcare", "finance", "all industries"],
        "affected_user_personas": ["recruiter", "talent acquisition", "HR manager", "hiring manager"],
        "keywords": ["recruiting", "hiring", "time-to-hire", "candidate experience", "ATS", "interview scheduling", "talent"],
        "raw_excerpts": [
            "Lost our top candidate to a competitor who moved in 5 days. We took 3 weeks.",
            "Scheduling interviews across 5 interviewers takes longer than the interviews themselves.",
            "Our ATS is a black hole. Candidates apply and hear nothing for weeks."
        ]
    },
    {
        "id": "pp-011",
        "description": "Finance teams at growing startups still use spreadsheets for financial planning. They've outgrown Excel but can't afford or justify enterprise FP&A tools.",
        "source_type": "twitter",
        "source_url": "https://twitter.com/example/status/012",
        "frequency_count": 678,
        "urgency_score": 0.74,
        "sentiment_score": -0.59,
        "affected_industries": ["startups", "technology", "SMB"],
        "affected_user_personas": ["finance manager", "CFO", "controller", "FP&A analyst"],
        "keywords": ["FP&A", "financial planning", "budgeting", "forecasting", "spreadsheet", "excel", "finance"],
        "raw_excerpts": [
            "Our 'financial model' is a 50-tab Excel file that breaks constantly.",
            "Anaplan wants $100k/year. We're a 30-person startup.",
            "Board meeting tomorrow and I'm still fixing circular references."
        ]
    },
    {
        "id": "pp-012",
        "description": "DevOps teams get buried in alerts. PagerDuty sends 200+ alerts daily, most are noise, and real incidents get lost in the flood.",
        "source_type": "reddit",
        "source_url": "https://reddit.com/r/devops/comments/example8",
        "frequency_count": 1134,
        "urgency_score": 0.86,
        "sentiment_score": -0.73,
        "affected_industries": ["technology", "SaaS", "fintech", "enterprise"],
        "affected_user_personas": ["SRE", "devops engineer", "platform engineer", "on-call engineer"],
        "keywords": ["alerts", "monitoring", "pagerduty", "noise", "incidents", "on-call", "alert fatigue", "observability"],
        "raw_excerpts": [
            "Got paged 12 times last night. 11 were false positives.",
            "Alert fatigue is real. We've started ignoring pages.",
            "Can't tell the difference between 'server is on fire' and 'disk at 81%'."
        ]
    }
]

# ============================================================================
# EMERGING INDUSTRIES - From news, funding data, trend analysis
# ============================================================================

DEMO_EMERGING_INDUSTRIES = [
    {
        "id": "ei-001",
        "industry_name": "AI-Powered Legal Tech",
        "growth_signals": [
            "$2.3B total funding in 2024 (up 145% YoY)",
            "Harvey AI raised $80M Series B",
            "Am Law 100 firms actively piloting AI tools",
            "Contract review time reduced 80% with AI"
        ],
        "funding_activity": "Series A median: $15M, Series B median: $45M",
        "key_players": ["Harvey AI", "Casetext (acquired by Thomson Reuters)", "Ironclad", "Juro", "ContractPodAi"],
        "technology_stack_trends": ["LLMs (GPT-4, Claude)", "RAG systems", "Document processing", "Vector databases"],
        "opportunity_score": 0.84
    },
    {
        "id": "ei-002",
        "industry_name": "Vertical AI Agents",
        "growth_signals": [
            "YC W24 batch: 40% of companies building AI agents",
            "Salesforce, ServiceNow, Zendesk all launching agent products",
            "Enterprise budgets shifting from 'AI tools' to 'AI workers'",
            "Agent frameworks (LangChain, AutoGPT) seeing massive adoption"
        ],
        "funding_activity": "Seed rounds averaging $5M, many raising before product",
        "key_players": ["Cognition (Devin)", "Sierra AI", "Adept", "MultiOn", "Induced AI"],
        "technology_stack_trends": ["Agent frameworks", "Tool use", "Computer use APIs", "Orchestration layers"],
        "opportunity_score": 0.91
    },
    {
        "id": "ei-003",
        "industry_name": "SMB Financial Operations",
        "growth_signals": [
            "Mercury, Ramp, Brex grew 200%+ in 2023",
            "8M small businesses in US still using basic accounting",
            "Bill.com $1B+ revenue proves SMB will pay for finops",
            "Embedded finance enabling new entrants"
        ],
        "funding_activity": "Series A: $20-40M typical for this space",
        "key_players": ["Ramp", "Brex", "Mercury", "Airbase", "Puzzle"],
        "technology_stack_trends": ["Plaid integration", "Real-time reconciliation", "AI categorization", "Banking-as-a-service"],
        "opportunity_score": 0.79
    },
    {
        "id": "ei-004",
        "industry_name": "Developer Experience Tools",
        "growth_signals": [
            "GitHub Copilot: 1.3M paid subscribers",
            "Every Fortune 500 evaluating AI coding tools",
            "Developer productivity now board-level topic",
            "Cursor raised $60M at $400M valuation"
        ],
        "funding_activity": "Hot market: seed rounds at $10M+, fast follow-ons",
        "key_players": ["GitHub Copilot", "Cursor", "Replit", "Sourcegraph", "Tabnine"],
        "technology_stack_trends": ["Code LLMs", "IDE integrations", "Codebase indexing", "Agent-based development"],
        "opportunity_score": 0.87
    },
    {
        "id": "ei-005",
        "industry_name": "Revenue Operations Automation",
        "growth_signals": [
            "RevOps job postings up 300% since 2021",
            "Clari, Gong, Salesloft all unicorns",
            "CRO/CFO alignment driving tool consolidation",
            "AI forecasting replacing gut-feel predictions"
        ],
        "funding_activity": "Growth rounds: $50-100M for leaders",
        "key_players": ["Clari", "Gong", "Salesloft", "Outreach", "People.ai"],
        "technology_stack_trends": ["Revenue intelligence", "Conversation AI", "Predictive analytics", "CRM enrichment"],
        "opportunity_score": 0.76
    },
    {
        "id": "ei-006",
        "industry_name": "AI Infrastructure & MLOps",
        "growth_signals": [
            "Every company becoming an AI company needs infra",
            "Model deployment complexity driving demand",
            "GPU shortage making optimization critical",
            "Open source models need hosting solutions"
        ],
        "funding_activity": "Infra companies commanding premium valuations",
        "key_players": ["Anyscale", "Modal", "Replicate", "Together AI", "Weights & Biases"],
        "technology_stack_trends": ["Model serving", "Fine-tuning platforms", "GPU orchestration", "Inference optimization"],
        "opportunity_score": 0.82
    }
]

# ============================================================================
# COMPETITOR ANALYSIS - Existing solutions and their weaknesses
# ============================================================================

DEMO_COMPETITORS = [
    {
        "competitor_name": "QuickBooks Online",
        "product_url": "https://quickbooks.intuit.com",
        "pricing_model": "$30-200/month based on features",
        "feature_list": [
            "Invoicing",
            "Expense tracking", 
            "Bank connections",
            "Basic reporting",
            "Payroll (add-on)",
            "Tax preparation"
        ],
        "user_complaints": [
            "Expensive for what you get",
            "Customer support is terrible",
            "Bank sync breaks constantly",
            "No multi-currency support on lower tiers",
            "Slow and buggy interface",
            "Forced upgrades to access basic features"
        ],
        "market_position": "Market leader with 80% SMB accounting share",
        "vulnerability_gaps": [
            "No AI-powered categorization",
            "Manual reconciliation still required",
            "Poor API for integrations",
            "No real-time multi-platform sync",
            "Dated UX compared to modern tools"
        ]
    },
    {
        "competitor_name": "Salesforce",
        "product_url": "https://salesforce.com",
        "pricing_model": "$25-300/user/month, enterprise negotiated",
        "feature_list": [
            "Contact management",
            "Opportunity tracking",
            "Pipeline management",
            "Reporting & dashboards",
            "Workflow automation",
            "AppExchange integrations"
        ],
        "user_complaints": [
            "Extremely complex to set up and maintain",
            "Requires dedicated admin or consultant",
            "Data entry burden on sales reps",
            "Expensive with all needed add-ons",
            "Mobile app is clunky",
            "Too many clicks to do simple tasks"
        ],
        "market_position": "Enterprise CRM leader, 20%+ market share",
        "vulnerability_gaps": [
            "No automatic activity capture",
            "AI features (Einstein) underdelivers",
            "SMB pricing is prohibitive",
            "Implementation takes months",
            "Reps work around it rather than in it"
        ]
    },
    {
        "competitor_name": "Jira",
        "product_url": "https://atlassian.com/jira",
        "pricing_model": "Free-$14/user/month, enterprise custom",
        "feature_list": [
            "Issue tracking",
            "Sprint planning",
            "Kanban boards",
            "Roadmaps",
            "Reporting",
            "Integrations"
        ],
        "user_complaints": [
            "Becomes slow with large projects",
            "UI is overwhelming and confusing",
            "Too much configuration required",
            "Velocity metrics are easily gamed",
            "Search is frustratingly bad",
            "Permissions are overly complex"
        ],
        "market_position": "Dominant in engineering project management",
        "vulnerability_gaps": [
            "Doesn't measure actual developer output",
            "No code-level productivity insights",
            "Tickets don't reflect real work",
            "Managers can't see who's actually shipping",
            "No AI assistance for estimation"
        ]
    },
    {
        "competitor_name": "Workday",
        "product_url": "https://workday.com",
        "pricing_model": "Enterprise only, $100+ per employee/year",
        "feature_list": [
            "HR management",
            "Payroll",
            "Benefits administration",
            "Talent management",
            "Workforce planning",
            "Analytics"
        ],
        "user_complaints": [
            "Extremely expensive",
            "Implementation takes 12-18 months",
            "Over-engineered for mid-market",
            "Requires dedicated team to manage",
            "User interface is dated",
            "Customization is limited and costly"
        ],
        "market_position": "Enterprise HCM leader",
        "vulnerability_gaps": [
            "No solution for 50-500 employee companies",
            "Onboarding module is basic",
            "No AI-powered workflow automation",
            "Can't compete on time-to-value",
            "Mid-market completely underserved"
        ]
    },
    {
        "competitor_name": "Google Analytics",
        "product_url": "https://analytics.google.com",
        "pricing_model": "Free (GA4), $150k+/year (GA360)",
        "feature_list": [
            "Traffic analysis",
            "User behavior tracking",
            "Conversion tracking",
            "Audience insights",
            "Attribution modeling",
            "BigQuery export"
        ],
        "user_complaints": [
            "GA4 migration was painful",
            "Lost historical data in transition",
            "Attribution models don't match revenue",
            "Can't connect content to pipeline",
            "Sampling on free tier",
            "Learning curve is steep"
        ],
        "market_position": "Dominant web analytics platform",
        "vulnerability_gaps": [
            "No B2B pipeline attribution",
            "Can't track content to closed-won revenue",
            "Account-level tracking is weak",
            "No integration with CRM pipeline",
            "Marketers still can't prove ROI"
        ]
    }
]

# ============================================================================
# OPPORTUNITY CATEGORIES - Synthesized analysis
# ============================================================================

DEMO_OPPORTUNITY_CATEGORIES = [
    {
        "category_name": "Workflow Automation",
        "subcategories": ["CRM automation", "HR automation", "Finance automation", "Legal automation"],
        "pain_point_ids": ["pp-003", "pp-004", "pp-008"],
        "market_size_estimate": "$15B by 2027",
        "competition_density": "medium",
        "automation_potential": 0.89
    },
    {
        "category_name": "Revenue Intelligence", 
        "subcategories": ["Sales analytics", "Churn prediction", "Pipeline forecasting", "Attribution"],
        "pain_point_ids": ["pp-005", "pp-006"],
        "market_size_estimate": "$8B by 2026",
        "competition_density": "high",
        "automation_potential": 0.82
    },
    {
        "category_name": "Developer Productivity",
        "subcategories": ["Engineering metrics", "Code quality", "DevOps automation", "Alert management"],
        "pain_point_ids": ["pp-002", "pp-012"],
        "market_size_estimate": "$25B by 2028",
        "competition_density": "medium",
        "automation_potential": 0.91
    },
    {
        "category_name": "SMB Financial Tools",
        "subcategories": ["Accounting automation", "Multi-platform reconciliation", "FP&A", "Expense management"],
        "pain_point_ids": ["pp-001", "pp-011"],
        "market_size_estimate": "$12B by 2027",
        "competition_density": "medium",
        "automation_potential": 0.85
    },
    {
        "category_name": "Operations & Inventory",
        "subcategories": ["Inventory sync", "Order management", "Fulfillment", "Multichannel ops"],
        "pain_point_ids": ["pp-009"],
        "market_size_estimate": "$6B by 2026",
        "competition_density": "medium",
        "automation_potential": 0.78
    }
]


def get_demo_intelligence_data():
    """Return complete demo intelligence data as dictionaries."""
    from datetime import datetime
    return {
        "extraction_timestamp": datetime.now().isoformat(),
        "pain_points": DEMO_PAIN_POINTS,
        "emerging_industries": DEMO_EMERGING_INDUSTRIES,
        "competitors": DEMO_COMPETITORS,
        "opportunity_categories": DEMO_OPPORTUNITY_CATEGORIES
    }


def get_demo_pain_points():
    """Return list of demo pain points."""
    return DEMO_PAIN_POINTS.copy()


def get_demo_industries():
    """Return list of demo emerging industries."""
    return DEMO_EMERGING_INDUSTRIES.copy()


def get_demo_competitors():
    """Return list of demo competitors."""
    return DEMO_COMPETITORS.copy()


def get_demo_opportunities():
    """Return list of demo opportunity categories."""
    return DEMO_OPPORTUNITY_CATEGORIES.copy()
