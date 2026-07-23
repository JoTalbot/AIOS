from aios_core.api.monitoring import AlertManager
def test(): assert isinstance(AlertManager().get_active_alerts(), list)
