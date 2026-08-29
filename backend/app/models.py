from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
import enum
from .database import Base

class PaymentStatus(str, enum.Enum):
    PENDING='pending'; SUCCESS='success'; FAILED='failed'

class PolicyDecisionEnum(str, enum.Enum):
    ALLOW='allow'; BLOCK='block'; HUMAN_REVIEW='human_review'; STOP='stop'

class ActionType(str, enum.Enum):
    RETRY='RETRY'; PAYMENT_LINK='PAYMENT_LINK'; HUMAN_ESCALATION='HUMAN_ESCALATION'; STOP='STOP'; WAIT='WAIT'

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(String, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_method = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RecoveryCase(Base):
    __tablename__ = 'recovery_cases'
    id = Column(String, primary_key=True, index=True)
    payment_id = Column(String, ForeignKey('payments.id'), index=True)
    revenue_at_risk = Column(Float, nullable=False)
    recommended_action = Column(Enum(ActionType), nullable=True)
    ai_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PolicyDecisionRecord(Base):
    __tablename__ = 'policy_decisions'
    id = Column(String, primary_key=True, index=True)
    recovery_case_id = Column(String, ForeignKey('recovery_cases.id'), index=True)
    decision = Column(Enum(PolicyDecisionEnum), nullable=False)
    policy_version = Column(String, default='v1.2')
    rules_triggered = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ExecutionRecord(Base):
    __tablename__ = 'executions'
    id = Column(String, primary_key=True, index=True)
    policy_decision_id = Column(String, ForeignKey('policy_decisions.id'), index=True)
    action = Column(Enum(ActionType), nullable=False)
    status = Column(String, nullable=False)
    idempotency_key = Column(String, unique=True, index=True)
    result_details = Column(JSON, nullable=True)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_decision = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(String, primary_key=True, index=True)
    event_id = Column(String, index=True)
    payment_id = Column(String, index=True)
    action = Column(String, nullable=True)
    outcome = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class SimulationRun(Base):
    __tablename__ = 'simulation_runs'
    id = Column(String, primary_key=True, index=True)
    dataset_size = Column(Integer, nullable=False)
    baseline_recovered = Column(Float, nullable=False)
    recoverai_recovered = Column(Float, nullable=False)
    unsafe_actions_blocked = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ImportedDatasetRow(Base):
    __tablename__ = 'imported_dataset_rows'
    id = Column(String, primary_key=True, index=True)
    batch_id = Column(String, index=True, nullable=False)
    row_number = Column(Integer, nullable=False)
    payment_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    failure_reason = Column(String, nullable=False)
    retry_count = Column(Integer, nullable=False, default=0)
    is_recoverable = Column(Boolean, nullable=False, default=False)
    # Optional ML behaviour features are stored as JSON so the database schema
    # remains backward-compatible while supporting richer training data.
    features = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
