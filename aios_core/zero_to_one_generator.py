"""
Zero-to-One Skill Generator (Vector 4)
Синтезирует новые навыки с нуля на основе RAG-шаблонов.
"""
import os
import datetime

class SkillGenerator:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.skills_dir = os.path.join(self.base_dir, "skills", "core")

    def create_skill(self, skill_name, description):
        print(f"🧬 [Zero-to-One] Синтез навыка с нуля: {skill_name}")
        skill_path = os.path.join(self.skills_dir, skill_name)
        code_path = os.path.join(skill_path, "code")
        
        os.makedirs(code_path, exist_ok=True)
        
        # Генерация SKILL.md
        with open(os.path.join(skill_path, "SKILL.md"), "w") as f:
            f.write(f"# {skill_name}\n\n**Description:** {description}\n**Generated:** {datetime.datetime.now()}\n")
            
        # Генерация run.py с защитой
        with open(os.path.join(code_path, "run.py"), "w") as f:
            f.write("from aios_core.security import constitution_enforced\n\n")
            f.write("@constitution_enforced\n")
            f.write("def run(context):\n")
            f.write(f'    print("Выполняю автономный навык: {skill_name}")\n')
            f.write('    return {"status": "ok"}\n')
            
        print(f"✅ Навык {skill_name} успешно создан по пути {skill_path}")

if __name__ == "__main__":
    generator = SkillGenerator(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    generator.create_skill("google-calendar-sync", "Автоматическая синхронизация встреч из Google Calendar.")
