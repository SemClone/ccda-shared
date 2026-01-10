"""
Data Models for CCDA

Pydantic models for data validation and serialization across all components.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Enums

class Ecosystem(str, Enum):
    """Package ecosystem types"""
    NPM = "npm"
    PYPI = "PyPI"
    MAVEN = "Maven"
    GO = "Go"
    CARGO = "crates.io"
    RUBYGEMS = "RubyGems"
    PACKAGIST = "Packagist"
    NUGET = "NuGet"
    HEX = "Hex"
    PUB = "Pub"


class Severity(str, Enum):
    """Vulnerability severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class HealthGrade(str, Enum):
    """Package health grade"""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class RiskLevel(str, Enum):
    """Package risk level"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MediaSource(str, Enum):
    """Media item source"""
    RSS = "rss"
    HACKERNEWS = "hackernews"
    REDDIT = "reddit"
    BLUESKY = "bluesky"


# Vulnerability Models

class VulnerabilityReference(BaseModel):
    """External reference for a vulnerability"""
    type: str
    url: str


class VulnerabilityAffected(BaseModel):
    """Affected package version range"""
    package: Dict[str, str]
    ranges: Optional[List[Dict[str, Any]]] = None
    versions: Optional[List[str]] = None
    ecosystem_specific: Optional[Dict[str, Any]] = None
    database_specific: Optional[Dict[str, Any]] = None


class Vulnerability(BaseModel):
    """Vulnerability information"""
    id: str
    ecosystem: Optional[str] = None
    package_name: Optional[str] = None
    purl: Optional[str] = None
    summary: Optional[str] = None
    details: Optional[str] = None
    severity: Optional[Severity] = None
    cvss_score: Optional[float] = None
    epss_score: Optional[float] = None
    epss_percentile: Optional[float] = None
    published_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    aliases: Optional[List[str]] = None
    affected: Optional[List[VulnerabilityAffected]] = None
    references: Optional[List[VulnerabilityReference]] = None
    database_specific: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# Package Models

class HealthMetrics(BaseModel):
    """Package health metrics breakdown"""
    security_score: float = Field(ge=0, le=100)
    maintenance_score: float = Field(ge=0, le=100)
    community_score: float = Field(ge=0, le=100)
    quality_score: float = Field(ge=0, le=100)
    license_score: float = Field(ge=0, le=100)
    overall_score: float = Field(ge=0, le=100)


class ContributorInfo(BaseModel):
    """Package contributor information"""
    login: str
    contributions: int
    company: Optional[str] = None
    type: Optional[str] = None


class Package(BaseModel):
    """Package information and analysis"""
    purl: str
    ecosystem: str
    name: str
    version: Optional[str] = None
    health_score: Optional[float] = Field(None, ge=0, le=100)
    health_grade: Optional[HealthGrade] = None
    risk_level: Optional[RiskLevel] = None
    metadata: Optional[Dict[str, Any]] = None
    contributors: Optional[List[ContributorInfo]] = None
    analysis_results: Optional[Dict[str, Any]] = None
    last_analyzed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# Media Models

class PackageMention(BaseModel):
    """Package mentioned in media"""
    purl: str
    ecosystem: str
    name: str
    context: Optional[str] = None


class AIAnalysis(BaseModel):
    """AI analysis of media content"""
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    risk_indicators: Optional[List[str]] = None
    risk_score: Optional[float] = None
    key_points: Optional[List[str]] = None
    packages_detected: Optional[List[str]] = None


class MediaItem(BaseModel):
    """Media item (news, social media, etc.)"""
    id: str
    source: MediaSource
    title: str
    content: Optional[str] = None
    url: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    sentiment_score: Optional[float] = Field(None, ge=-1, le=1)
    risk_score: Optional[float] = Field(None, ge=0, le=100)
    package_mentions: Optional[List[PackageMention]] = None
    ai_analysis: Optional[AIAnalysis] = None
    created_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# Job Models

class JobConfig(BaseModel):
    """Job configuration"""
    enabled: bool = True
    schedule: str  # Cron expression
    timeout_seconds: Optional[int] = None
    retry_count: Optional[int] = 0
    parameters: Optional[Dict[str, Any]] = None


class Job(BaseModel):
    """Background job definition"""
    id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING
    config: JobConfig
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_error: Optional[str] = None
    run_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class JobExecution(BaseModel):
    """Job execution record"""
    job_id: str
    execution_id: str
    status: JobStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


# API Response Models

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: Optional[str] = None
    component: Optional[str] = None
    uptime_seconds: Optional[int] = None


class PaginatedResponse(BaseModel):
    """Paginated API response"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Analysis Models

class BinaryAnalysisResult(BaseModel):
    """Binary analysis result from binarysniffer"""
    has_binaries: bool
    binary_files: List[str]
    risk_score: float
    details: Optional[Dict[str, Any]] = None


class LicenseAnalysisResult(BaseModel):
    """License analysis result from osslili"""
    license: Optional[str] = None
    license_type: Optional[str] = None
    is_osi_approved: Optional[bool] = None
    is_permissive: Optional[bool] = None
    risk_score: float
    details: Optional[Dict[str, Any]] = None


class PackageAnalysisResult(BaseModel):
    """Complete package analysis result from ccda-cli"""
    purl: str
    health_score: float
    health_metrics: HealthMetrics
    health_grade: HealthGrade
    risk_level: RiskLevel
    vulnerabilities_count: int
    binary_analysis: Optional[BinaryAnalysisResult] = None
    license_analysis: Optional[LicenseAnalysisResult] = None
    metadata: Dict[str, Any]
    analyzed_at: datetime

    class Config:
        use_enum_values = True


# Search Models

class SearchQuery(BaseModel):
    """Search query parameters"""
    q: str
    ecosystem: Optional[str] = None
    severity: Optional[Severity] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    class Config:
        use_enum_values = True


class SearchResult(BaseModel):
    """Search result item"""
    type: str  # "vulnerability" or "package"
    id: str
    title: str
    description: Optional[str] = None
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
