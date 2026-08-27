from sqlalchemy.exc import IntegrityError
from ..models import ExecutionRecord


class IdempotencyManager:
    @staticmethod
    def make_key(case: dict, action: str) -> str:
        """Same logical case/action must always map to the same execution key."""
        case_id = case.get("case_id") or case.get("payment_id") or "unknown"
        attempt = int(case.get("retry_count", 0) or 0) if action == "RETRY" else 0
        return f"recover:{case_id}:{action}:{attempt}"

    @staticmethod
    def check_and_record(db, idempotency_key: str, action: str, policy_decision_id: str = ""):
        existing = db.query(ExecutionRecord).filter(ExecutionRecord.idempotency_key == idempotency_key).first()
        if existing:
            return existing
        new_record = ExecutionRecord(
            id=f'exec_{idempotency_key.replace(":", "_")}',
            policy_decision_id=policy_decision_id,
            action=action,
            status='PENDING',
            idempotency_key=idempotency_key,
        )
        db.add(new_record)
        try:
            db.commit()
            db.refresh(new_record)
            return new_record
        except IntegrityError:
            db.rollback()
            return db.query(ExecutionRecord).filter(ExecutionRecord.idempotency_key == idempotency_key).first()


idempotency_manager = IdempotencyManager()
