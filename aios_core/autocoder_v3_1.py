from .autocoder_v3 import AutocoderV3, AutoPRCreator
class AutocoderV3_1(AutocoderV3):
    def run_task(self, task_description: str, file_path: str, instruction: str, create_pr: bool = False, auto_merge: bool = False):
        return super().run_task(task_description, file_path, instruction, create_pr=create_pr)
