"""
Meta-Cognitive Self-Coder (v2.0-AST)
Autonomously generated & upgraded by AIOS Self-Evolution Engine.
Позволяет агентам переписывать собственный код через AST-парсинг с учетом Конституции.
"""
import ast
import os
import subprocess

class SecurityDecoratorTransformer(ast.NodeTransformer):
    """
    AST-Трансформер: Находит функцию run() в старых скиллах 
    и автоматически внедряет декоратор @constitution_enforced, 
    если его там нет.
    """
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.name == "run":
            # Проверяем наличие декоратора constitution_enforced
            has_decorator = any(
                (isinstance(d, ast.Name) and d.id == 'constitution_enforced') or 
                (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == 'constitution_enforced')
                for d in node.decorator_list
            )
            if not has_decorator:
                # Добавляем декоратор
                decorator = ast.Name(id='constitution_enforced', ctx=ast.Load())
                node.decorator_list.insert(0, decorator)
        return node

class MetaCognitiveCoder:
    def __init__(self):
        self.version = "2.0-AST"

    def refactor_skill_ast(self, file_path):
        print(f"🧠 [Meta-Coder] AST Анализ файла: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        # 1. Парсинг исходного кода в Абстрактное Синтаксическое Дерево
        tree = ast.parse(source)
        
        # 2. Модификация дерева
        transformer = SecurityDecoratorTransformer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)

        # 3. Генерация нового кода из AST
        new_source = ast.unparse(new_tree)

        # 4. Добавление импортов безопасности, если их нет
        if "constitution_enforced" not in source:
            new_source = "from aios_core.security import constitution_enforced\n\n" + new_source

        # 5. Сохранение изменений
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_source)
            
        print(f"✅ [Meta-Coder] Код успешно рефакторен и защищен Конституцией: {file_path}")
        return True

    def commit_and_push_changes(self, file_path, repo_path):
        print(f"🚀 [Meta-Coder] Интеграция изменений в GitHub...")
        subprocess.run(["git", "add", file_path], cwd=repo_path, check=True)
        commit_msg = f"auto-refactor(skills): AST-injection of @constitution_enforced in {os.path.basename(file_path)}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_path, check=False)
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_path, check=True)
        print("✅ [Meta-Coder] Изменения запушены в ветку main.")
