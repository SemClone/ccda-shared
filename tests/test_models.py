"""
Tests for shared data models
"""
import pytest
from datetime import datetime
from shared.models import (
    Vulnerability,
    Package,
    MediaItem,
    Job,
    HealthMetrics,
    Severity,
    HealthGrade,
    RiskLevel,
    JobStatus,
    MediaSource,
)


class TestVulnerability:
    """Test Vulnerability model"""

    def test_create_vulnerability(self):
        """Test creating a basic vulnerability"""
        vuln = Vulnerability(
            id="GHSA-1234-5678-9012",
            ecosystem="npm",
            package_name="example-package",
            summary="Test vulnerability",
            severity=Severity.HIGH,
            cvss_score=7.5,
        )
        assert vuln.id == "GHSA-1234-5678-9012"
        assert vuln.ecosystem == "npm"
        assert vuln.severity == Severity.HIGH
        assert vuln.cvss_score == 7.5

    def test_vulnerability_with_epss(self):
        """Test vulnerability with EPSS scoring"""
        vuln = Vulnerability(
            id="CVE-2024-1234",
            epss_score=0.85,
            epss_percentile=0.95,
        )
        assert vuln.epss_score == 0.85
        assert vuln.epss_percentile == 0.95


class TestPackage:
    """Test Package model"""

    def test_create_package(self):
        """Test creating a basic package"""
        pkg = Package(
            purl="pkg:npm/lodash@4.17.21",
            ecosystem="npm",
            name="lodash",
            version="4.17.21",
            health_score=85.5,
            health_grade=HealthGrade.B,
            risk_level=RiskLevel.LOW,
        )
        assert pkg.purl == "pkg:npm/lodash@4.17.21"
        assert pkg.ecosystem == "npm"
        assert pkg.health_score == 85.5
        assert pkg.health_grade == HealthGrade.B
        assert pkg.risk_level == RiskLevel.LOW

    def test_package_health_score_validation(self):
        """Test health score validation (should be 0-100)"""
        with pytest.raises(ValueError):
            Package(
                purl="pkg:npm/test",
                ecosystem="npm",
                name="test",
                health_score=150,  # Invalid: > 100
            )


class TestHealthMetrics:
    """Test HealthMetrics model"""

    def test_create_health_metrics(self):
        """Test creating health metrics"""
        metrics = HealthMetrics(
            security_score=90.0,
            maintenance_score=85.0,
            community_score=75.0,
            quality_score=80.0,
            license_score=95.0,
            overall_score=85.0,
        )
        assert metrics.security_score == 90.0
        assert metrics.overall_score == 85.0

    def test_health_metrics_validation(self):
        """Test health metrics score validation"""
        with pytest.raises(ValueError):
            HealthMetrics(
                security_score=110.0,  # Invalid: > 100
                maintenance_score=85.0,
                community_score=75.0,
                quality_score=80.0,
                license_score=95.0,
                overall_score=85.0,
            )


class TestMediaItem:
    """Test MediaItem model"""

    def test_create_media_item(self):
        """Test creating a media item"""
        media = MediaItem(
            id="hn-12345",
            source=MediaSource.HACKERNEWS,
            title="Security vulnerability in popular package",
            url="https://news.ycombinator.com/item?id=12345",
            sentiment_score=-0.5,
            risk_score=75.0,
        )
        assert media.id == "hn-12345"
        assert media.source == MediaSource.HACKERNEWS
        assert media.sentiment_score == -0.5
        assert media.risk_score == 75.0

    def test_media_sentiment_score_validation(self):
        """Test sentiment score validation (-1 to 1)"""
        with pytest.raises(ValueError):
            MediaItem(
                id="test",
                source=MediaSource.RSS,
                title="Test",
                url="https://example.com",
                sentiment_score=2.0,  # Invalid: > 1
            )


class TestJob:
    """Test Job model"""

    def test_create_job(self):
        """Test creating a job"""
        from shared.models import JobConfig

        job = Job(
            id="job-1",
            job_type="sync_osv",
            status=JobStatus.PENDING,
            config=JobConfig(
                enabled=True,
                schedule="0 */6 * * *",  # Every 6 hours
            ),
        )
        assert job.id == "job-1"
        assert job.job_type == "sync_osv"
        assert job.status == JobStatus.PENDING
        assert job.config.enabled is True
        assert job.config.schedule == "0 */6 * * *"

    def test_job_execution_count(self):
        """Test job run count tracking"""
        from shared.models import JobConfig

        job = Job(
            id="job-2",
            job_type="analyze_package",
            status=JobStatus.COMPLETED,
            config=JobConfig(enabled=True, schedule="* * * * *"),
            run_count=10,
        )
        assert job.run_count == 10


class TestEnums:
    """Test enum values"""

    def test_severity_enum(self):
        """Test Severity enum"""
        assert Severity.CRITICAL.value == "CRITICAL"
        assert Severity.HIGH.value == "HIGH"
        assert Severity.MEDIUM.value == "MEDIUM"

    def test_health_grade_enum(self):
        """Test HealthGrade enum"""
        assert HealthGrade.A.value == "A"
        assert HealthGrade.B.value == "B"
        assert HealthGrade.F.value == "F"

    def test_risk_level_enum(self):
        """Test RiskLevel enum"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MODERATE.value == "moderate"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_job_status_enum(self):
        """Test JobStatus enum"""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
