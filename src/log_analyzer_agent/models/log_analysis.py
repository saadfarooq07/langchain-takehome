"""Log analysis models with tenant isolation."""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Integer, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class LogAnalysis(Base):
    """Log analysis results with tenant isolation."""
    
    __tablename__ = "log_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    # Analysis metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    log_source = Column(String(255))  # e.g., "nginx", "application", "system"
    
    # Analysis results (stored as JSONB for efficient querying)
    issues_found = Column(JSONB, default=list)
    recommendations = Column(JSONB, default=list)
    summary = Column(Text)
    
    # Statistics
    total_lines_analyzed = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    
    # Performance metrics
    analysis_duration_ms = Column(Integer)
    model_used = Column(String(100))
    
    # Status
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    tenant = relationship("Tenant")
    user = relationship("User")
    log_entries = relationship("LogEntry", back_populates="analysis", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_log_analyses_tenant_created", "tenant_id", "created_at"),
        Index("ix_log_analyses_tenant_status", "tenant_id", "status"),
    )
    
    def __repr__(self):
        return f"<LogAnalysis {self.id} for tenant {self.tenant_id}>"


class LogEntry(Base):
    """Individual log entries with tenant isolation."""
    
    __tablename__ = "log_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("log_analyses.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Log data
    timestamp = Column(DateTime(timezone=True))
    level = Column(String(20))  # ERROR, WARNING, INFO, DEBUG
    message = Column(Text, nullable=False)
    
    # Parsed data
    parsed_data = Column(JSONB, default=dict)
    
    # Classification
    is_error = Column(Boolean, default=False)
    is_anomaly = Column(Boolean, default=False)
    tags = Column(JSON, default=list)
    
    # Line reference
    line_number = Column(Integer)
    raw_content = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    analysis = relationship("LogAnalysis", back_populates="log_entries")
    tenant = relationship("Tenant")
    
    __table_args__ = (
        Index("ix_log_entries_tenant_timestamp", "tenant_id", "timestamp"),
        Index("ix_log_entries_tenant_level", "tenant_id", "level"),
        Index("ix_log_entries_analysis_line", "analysis_id", "line_number"),
    )
    
    def __repr__(self):
        return f"<LogEntry {self.id} - {self.level}>"