import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, BigInteger, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    installation_id: Mapped[int] = mapped_column(Integer, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="repository", cascade="all, delete-orphan")


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repo_id", "pr_number", name="uq_repo_pr"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    repo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"), index=True)
    pr_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str] = mapped_column(String(255))
    head_sha: Mapped[str] = mapped_column(String(40))
    base_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    head_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(50), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    repository: Mapped["Repository"] = relationship(back_populates="pull_requests")
    reviews: Mapped[list["Review"]] = relationship(back_populates="pull_request", cascade="all, delete-orphan")
    senior_comments: Mapped[list["SeniorComment"]] = relationship(back_populates="pull_request", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    pr_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    trigger_type: Mapped[str] = mapped_column(String(50), default="pr_opened")
    github_comment_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    agents_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_issues: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    info_count: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pull_request: Mapped["PullRequest"] = relationship(back_populates="reviews")
    issues: Mapped[list["Issue"]] = relationship(back_populates="review", cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        Index("idx_issues_severity", "severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reviews.id"), index=True)
    agent_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(100))
    file_path: Mapped[str] = mapped_column(Text)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    review: Mapped["Review"] = relationship(back_populates="issues")


class SeniorComment(Base):
    __tablename__ = "senior_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    pr_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    github_comment_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reviewer_login: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pull_request: Mapped["PullRequest"] = relationship(back_populates="senior_comments")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_read", "is_read", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    extra_data: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
