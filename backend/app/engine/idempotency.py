from ..models import ExecutionRecord
class IdempotencyManager:
    @staticmethod
    def check_and_record(db, idempotency_key: str, action: str):
        existing = db.query(ExecutionRecord).filter(ExecutionRecord.idempotency_key == idempotency_key).first()
        if existing: return existing
        new_record = ExecutionRecord(id=f'exec_{idempotency_key}', policy_decision_id='', action=action, status='PENDING', idempotency_key=idempotency_key)
        db.add(new_record); db.commit(); db.refresh(new_record)
        return new_record
idempotency_manager = IdempotencyManager()
