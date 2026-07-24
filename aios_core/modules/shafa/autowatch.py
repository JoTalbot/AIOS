from aios_core.modules.rozetka.autowatch import RozetkaAutoWatch

class ShafaAutoWatch(RozetkaAutoWatch):
    """AutoWatch for Shafa.ua.""" 
    def run_cycle(self, queries=None, collect=True):
        report = super().run_cycle(queries=queries, collect=collect)
        report["platform"] = "shafa"
        return report
