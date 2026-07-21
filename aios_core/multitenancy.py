"""Multi-Tenancy Support for AIOS"""

from typing import Dict, Any


class Tenant:
    def __init__(self, tenant_id: str, name: str):
        self.tenant_id = tenant_id
        self.name = name
        self.config: Dict[str, Any] = {}
        self.usage = {"tasks": 0, "memory": 0}

    def set_config(self, key: str, value: Any):
        self.config[key] = value

    def record_usage(self, tasks: int = 0, memory: int = 0):
        self.usage["tasks"] += tasks
        self.usage["memory"] += memory


class MultiTenantManager:
    """Manages multiple tenants in one AIOS instance."""

    def __init__(self):
        self.tenants: Dict[str, Tenant] = {}

    def create_tenant(self, tenant_id: str, name: str) -> Tenant:
        tenant = Tenant(tenant_id, name)
        self.tenants[tenant_id] = tenant
        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant:
        return self.tenants.get(tenant_id)

    def stats(self) -> dict:
        return {
            "tenants": len(self.tenants),
            "total_tasks": sum(t.usage["tasks"] for t in self.tenants.values())
        }


multi_tenant = MultiTenantManager()