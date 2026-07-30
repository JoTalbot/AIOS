from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TemplateEvolution:
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.threshold = 0.15

    async def analyze(self, template_id: str) -> dict:
        if not self.db:
            return {"status": "no_db"}
        from aios_core.models.template_variant import TemplateVariant

        result = await self.db.execute(
            select(TemplateVariant).where(TemplateVariant.template_id == template_id, TemplateVariant.is_active)
        )
        variants = result.scalars().all()
        if not variants:
            return {"status": "no_variants"}
        winner = max(variants, key=lambda v: v.conversion_rate)
        return {
            "winner_id": winner.id,
            "rate": winner.conversion_rate,
            "promote": winner.conversion_rate >= self.threshold,
        }

    async def promote(self, template_id: str, variant_id: int) -> dict:
        if not self.db:
            return {"status": "no_db"}
        from aios_core.models.template import Template
        from aios_core.models.template_variant import TemplateVariant

        variant = await self.db.get(TemplateVariant, variant_id)
        template = await self.db.get(Template, template_id)
        if not variant or not template:
            return {"status": "not_found"}
        template.content = variant.content
        template.version += 1
        template.updated_at = datetime.now(timezone.utc)
        variant.is_active = False
        await self.db.commit()
        return {"status": "promoted", "new_version": template.version}


template_evolution = TemplateEvolution()
