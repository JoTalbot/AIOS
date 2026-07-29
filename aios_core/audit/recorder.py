from sqlalchemy.ext.asyncio import AsyncSession


class AuditRecorder:
    def __init__(self, db: AsyncSession = None):
        self.db = db

    async def record(self, user_id: str, action: str, resource_type: str | None = None,
                     resource_id: str | None = None, details: dict | None = None,
                     ip_address: str | None = None, user_agent: str | None = None):
        if not self.db:
            print(f"[Audit] {user_id} -> {action} on {resource_type}:{resource_id}")
            return
        try:
            from aios_core.models.audit_log import AuditLog
            log = AuditLog(
                user_id=user_id, action=action,
                resource_type=resource_type, resource_id=resource_id,
                details=details or {}, ip_address=ip_address, user_agent=user_agent
            )
            self.db.add(log)
            await self.db.commit()
        except Exception as e:
            print(f"[Audit] Error: {e}")

    async def get_logs(self, user_id: str | None = None, action: str | None = None, limit: int = 100):
        if not self.db:
            return []
        from sqlalchemy import select

        from aios_core.models.audit_log import AuditLog
        q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        if user_id:
            q = q.where(AuditLog.user_id == user_id)
        if action:
            q = q.where(AuditLog.action == action)
        result = await self.db.execute(q)
        return result.scalars().all()

recorder = AuditRecorder()
