from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.review import create_dataset_review_case
from app.database import Base
from app.engine.executor import executor
from app.models import ActionType, ExecutionRecord, Payment, PaymentStatus, PolicyDecisionEnum, PolicyDecisionRecord, RecoveryCase, ImportedDatasetRow
from app.simulation.database_evaluation import evaluate_database_payments


def make_db():
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_dataset_review_case_does_not_use_removed_ml_model_attribute():
    db = make_db()
    try:
        for i, recoverable in enumerate([True, False, True, False], start=1):
            db.add(ImportedDatasetRow(
                id=f'row-review-{i}', batch_id='review-batch', row_number=i,
                payment_id=f'review-pay-{i}', amount=1000 + i,
                failure_reason='timeout_network' if recoverable else 'card_expired',
                retry_count=0, is_recoverable=recoverable,
            ))
        db.commit()
        result = create_dataset_review_case(None, db)
        assert result['scenario'] == 'UPLOADED_DATASET'
        assert result['execution_id'].startswith('dataset_execution_')
    finally:
        db.close()


def test_database_evaluation_returns_stable_policy_keys():
    db = make_db()
    try:
        for i, recoverable in enumerate([True, False, True, False], start=1):
            db.add(ImportedDatasetRow(
                id=f'row-{i}', batch_id='batch-1', row_number=i,
                payment_id=f'pay-{i}', amount=1000 + i,
                failure_reason='timeout_network' if recoverable else 'card_expired',
                retry_count=0, is_recoverable=recoverable,
            ))
        db.commit()
        result = evaluate_database_payments(db, limit=100, batch_id='batch-1')
        assert set(result['policy_decisions']) == {'ALLOW', 'BLOCK', 'STOP', 'HUMAN_REVIEW'}
        assert sum(result['policy_decisions'].values()) == 4
    finally:
        db.close()


def test_human_approval_reuses_existing_execution_record():
    db = make_db()
    try:
        payment = Payment(id='payment-1', amount=1000, status=PaymentStatus.FAILED, retry_count=0)
        case = RecoveryCase(id='case-1', payment_id=payment.id, revenue_at_risk=1000, recommended_action=ActionType.RETRY, ai_confidence=0.9)
        policy = PolicyDecisionRecord(id='policy-1', recovery_case_id=case.id, decision=PolicyDecisionEnum.HUMAN_REVIEW, policy_version='test')
        execution = ExecutionRecord(
            id='execution-1', policy_decision_id=policy.id, action=ActionType.RETRY,
            status='PENDING_HUMAN_REVIEW', idempotency_key='review:batch-1:row-1:RETRY',
            result_details={'actual_is_recoverable': True},
        )
        db.add_all([payment, case, policy, execution])
        db.commit()

        result = executor.execute(
            db,
            {
                'case_id': case.id, 'payment_id': payment.id, 'amount': payment.amount,
                'retry_count': payment.retry_count, 'recommended_action': 'RETRY',
                'ai_confidence': case.ai_confidence, 'is_recoverable': True,
                '_execution_id': execution.id, '_human_approved': True,
            },
            'human_approved', 'RETRY', policy.id,
        )

        assert result['status'] == 'RECOVERED'
        assert result['idempotency_key'] == execution.idempotency_key
        assert db.query(ExecutionRecord).count() == 1
    finally:
        db.close()
