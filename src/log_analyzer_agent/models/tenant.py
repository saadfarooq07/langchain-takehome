"""Tenant models for multi-tenancy support."""

from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


class Tenant(Base):
    """Tenant model for multi-tenant support."""
    
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Tenant settings (encrypted in the database)
    settings = Column(JSON, default=dict)
    
    # API keys for tenant-specific access
    api_key_hash = Column(String(255))
    api_key_prefix = Column(String(32))  # First 8 chars of API key for identification
    
    # Status and timestamps
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Subscription/plan information
    plan = Column(String(50), default="free")
    plan_expires_at = Column(DateTime(timezone=True))
    
    # Usage limits
    max_users = Column(Integer, default=5)
    max_monthly_logs = Column(Integer, default=10000)
    max_storage_gb = Column(Integer, default=1)
    
    def __repr__(self):
        return f"<Tenant {self.slug}>"


class TenantSettings(Base):
    """Encrypted settings for tenants."""
    
    __tablename__ = "tenant_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Encrypted settings
    key = Column(String(255), nullable=False)
    value = Column(Text)  # Will be encrypted
    is_encrypted = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", backref="encrypted_settings")
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_tenant_settings_tenant_key"),
    )