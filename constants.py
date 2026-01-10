"""
Constants for CCDA

Centralized constants used across all components (worker, API, dashboard).
"""

# Environment Variable Names
ENV_SPACES_KEY = "SPACES_KEY"
ENV_SPACES_SECRET = "SPACES_SECRET"
ENV_SPACES_REGION = "SPACES_REGION"
ENV_SPACES_BUCKET = "SPACES_BUCKET"
ENV_GITHUB_TOKEN = "GITHUB_TOKEN"
ENV_BLUESKY_USERNAME = "BLUESKY_USERNAME"
ENV_BLUESKY_PASSWORD = "BLUESKY_PASSWORD"
ENV_API_URL = "API_URL"
ENV_CACHE_TTL = "CACHE_TTL"
ENV_DUCKDB_PATH = "DUCKDB_PATH"

# Default Values
DEFAULT_SPACES_REGION = "sfo3"
DEFAULT_SPACES_BUCKET = "ccda-data"
DEFAULT_CACHE_TTL = 300  # 5 minutes
DEFAULT_API_PORT = 8000
DEFAULT_DASHBOARD_PORT = 5000
DEFAULT_WORKER_PORT = 8080

# Spaces File Paths
SPACES_PATH_DUCKDB = "data/ccda.duckdb"
SPACES_PATH_DEMO_STATUS = "demo/status.json"
SPACES_PATH_WORKER_STATUS = "worker/status.json"
SPACES_PATH_JOBS_QUEUE = "queue/jobs.json"
SPACES_PATH_JOBS_EXECUTIONS = "queue/executions/"
SPACES_PATH_WORKER_ERRORS = "worker/errors.json"
SPACES_PATH_MEDIA = "media/"
SPACES_PATH_PACKAGES = "packages/"
SPACES_PATH_VULNERABILITIES = "vulnerabilities/"
SPACES_PATH_ANALYSIS = "analysis/"

# Database Tables
TABLE_VULNERABILITIES = "vulnerabilities"
TABLE_PACKAGES = "packages"
TABLE_MEDIA = "media"
TABLE_JOBS = "jobs"

# API Endpoints (relative paths)
API_PATH_HEALTH = "/health"
API_PATH_STATUS = "/status"
API_PATH_PACKAGES = "/packages"
API_PATH_VULNERABILITIES = "/vulnerabilities"
API_PATH_MEDIA = "/media"
API_PATH_QUEUE = "/queue"
API_PATH_SEARCH = "/search"

# Job Types
JOB_TYPE_SYNC_OSV = "sync_osv"
JOB_TYPE_SYNC_GHSA = "sync_ghsa"
JOB_TYPE_SYNC_NVD = "sync_nvd"
JOB_TYPE_SYNC_EPSS = "sync_epss"
JOB_TYPE_SYNC_MEDIA_RSS = "sync_media_rss"
JOB_TYPE_SYNC_MEDIA_HACKERNEWS = "sync_media_hackernews"
JOB_TYPE_SYNC_MEDIA_REDDIT = "sync_media_reddit"
JOB_TYPE_SYNC_MEDIA_BLUESKY = "sync_media_bluesky"
JOB_TYPE_ANALYZE_PACKAGE = "analyze_package"
JOB_TYPE_AI_ANALYSIS = "ai_analysis"
JOB_TYPE_SCAN_BINARY = "scan_binary"
JOB_TYPE_SCAN_LICENSE = "scan_license"
JOB_TYPE_ANALYZE_CONTRIBUTORS = "analyze_contributors"

# Job Schedules (cron expressions)
SCHEDULE_EVERY_MINUTE = "* * * * *"
SCHEDULE_EVERY_5_MINUTES = "*/5 * * * *"
SCHEDULE_EVERY_15_MINUTES = "*/15 * * * *"
SCHEDULE_EVERY_30_MINUTES = "*/30 * * * *"
SCHEDULE_EVERY_HOUR = "0 * * * *"
SCHEDULE_EVERY_6_HOURS = "0 */6 * * *"
SCHEDULE_EVERY_12_HOURS = "0 */12 * * *"
SCHEDULE_DAILY = "0 0 * * *"
SCHEDULE_WEEKLY = "0 0 * * 0"

# Health Score Weights (must sum to 1.0)
HEALTH_WEIGHT_SECURITY = 0.30      # 30% - Vulnerabilities, security metrics
HEALTH_WEIGHT_MAINTENANCE = 0.25   # 25% - Recent commits, activity
HEALTH_WEIGHT_COMMUNITY = 0.20     # 20% - Contributors, stars, forks
HEALTH_WEIGHT_QUALITY = 0.15       # 15% - Code quality, tests
HEALTH_WEIGHT_LICENSE = 0.10       # 10% - License compliance

# Health Grade Thresholds
HEALTH_GRADE_A_MIN = 90.0
HEALTH_GRADE_B_MIN = 75.0
HEALTH_GRADE_C_MIN = 60.0
HEALTH_GRADE_D_MIN = 40.0
# Below 40.0 is Grade F

# Risk Level Thresholds
RISK_CRITICAL_MAX = 40.0  # Below 40 health score = critical risk
RISK_HIGH_MAX = 60.0      # 40-59 health score = high risk
RISK_MODERATE_MAX = 75.0  # 60-74 health score = moderate risk
# Above 75.0 = low risk

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Cache TTLs (seconds)
CACHE_TTL_HEALTH = 300           # 5 minutes
CACHE_TTL_VULNERABILITIES = 3600  # 1 hour
CACHE_TTL_PACKAGES = 1800         # 30 minutes
CACHE_TTL_MEDIA = 900             # 15 minutes
CACHE_TTL_SEARCH = 600            # 10 minutes

# API Rate Limits (requests per minute)
RATE_LIMIT_DEFAULT = 60
RATE_LIMIT_SEARCH = 20
RATE_LIMIT_ANALYSIS = 10

# External API URLs
OSV_API_URL = "https://api.osv.dev/v1"
NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
EPSS_API_URL = "https://api.first.org/data/v1/epss"
GITHUB_API_URL = "https://api.github.com"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# Media Sources
MEDIA_SOURCES_RSS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.securityweek.com/feed",
    "https://threatpost.com/feed/",
]

HACKERNEWS_API_URL = "https://hacker-news.firebaseio.com/v0"
REDDIT_API_URL = "https://www.reddit.com"
BLUESKY_API_URL = "https://bsky.social/xrpc"

# Sentiment Score Ranges
SENTIMENT_VERY_NEGATIVE = -1.0
SENTIMENT_NEGATIVE = -0.5
SENTIMENT_NEUTRAL = 0.0
SENTIMENT_POSITIVE = 0.5
SENTIMENT_VERY_POSITIVE = 1.0

# Risk Score Thresholds for Media
MEDIA_RISK_HIGH = 80.0
MEDIA_RISK_MODERATE = 50.0
MEDIA_RISK_LOW = 20.0

# Timeout Values (seconds)
TIMEOUT_HTTP_REQUEST = 30
TIMEOUT_GITHUB_API = 60
TIMEOUT_OSV_API = 120
TIMEOUT_JOB_DEFAULT = 3600  # 1 hour
TIMEOUT_JOB_SYNC = 7200     # 2 hours
TIMEOUT_JOB_ANALYSIS = 1800  # 30 minutes

# Retry Configuration
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 2
RETRY_INITIAL_DELAY = 1  # seconds

# Logging
LOG_LEVEL_DEFAULT = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Version
CCDA_VERSION = "3.0.0"
API_VERSION = "v1"

# Component Names
COMPONENT_WORKER = "worker"
COMPONENT_API = "api"
COMPONENT_DASHBOARD = "dashboard"

# Status Values
STATUS_HEALTHY = "healthy"
STATUS_UNHEALTHY = "unhealthy"
STATUS_DEGRADED = "degraded"

# Ecosystems (matching packageurl-python spec)
ECOSYSTEM_NPM = "npm"
ECOSYSTEM_PYPI = "pypi"
ECOSYSTEM_MAVEN = "maven"
ECOSYSTEM_GO = "golang"
ECOSYSTEM_CARGO = "cargo"
ECOSYSTEM_RUBYGEMS = "gem"
ECOSYSTEM_PACKAGIST = "composer"
ECOSYSTEM_NUGET = "nuget"
ECOSYSTEM_HEX = "hex"
ECOSYSTEM_PUB = "pub"

SUPPORTED_ECOSYSTEMS = [
    ECOSYSTEM_NPM,
    ECOSYSTEM_PYPI,
    ECOSYSTEM_MAVEN,
    ECOSYSTEM_GO,
    ECOSYSTEM_CARGO,
    ECOSYSTEM_RUBYGEMS,
    ECOSYSTEM_PACKAGIST,
    ECOSYSTEM_NUGET,
    ECOSYSTEM_HEX,
    ECOSYSTEM_PUB,
]

# PURL Prefixes
PURL_PREFIX = "pkg:"

# Database File Sizes (for monitoring)
DUCKDB_MAX_SIZE_GB = 10
DUCKDB_WARNING_SIZE_GB = 8

# Worker Configuration
WORKER_HEARTBEAT_INTERVAL = 60  # seconds
WORKER_QUEUE_CHECK_INTERVAL = 300  # seconds (5 minutes)
WORKER_MAX_CONCURRENT_JOBS = 1  # Limit to 1 concurrent job to prevent connection exhaustion
WORKER_SHUTDOWN_GRACE_PERIOD = 30  # seconds

# Dashboard Configuration
DASHBOARD_REFRESH_INTERVAL = 30  # seconds
DASHBOARD_MAX_RECENT_ITEMS = 50

# Metrics
METRIC_VULNERABILITY_COUNT = "vulnerability_count"
METRIC_PACKAGE_COUNT = "package_count"
METRIC_MEDIA_COUNT = "media_count"
METRIC_JOB_COUNT = "job_count"
METRIC_API_REQUESTS = "api_requests"
METRIC_API_ERRORS = "api_errors"
METRIC_WORKER_UPTIME = "worker_uptime"
