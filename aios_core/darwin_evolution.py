"""
AIOS Darwin Protocol (Genetic Algorithm for Swarm Evolution)
"""
import random
import time

class GeneticSwarmEngine:
    def __init__(self):
        self.generation = 1
        
    def mutate_prompt(self, base_prompt):
        mutations = [
            " [Упор на скорость]", 
            " [Упор на максимальную безопасность]", 
            " [Мыслить как хакер]"
        ]
        return base_prompt + random.choice(mutations)

    def run_evolution_cycle(self):
        print(f"🧬 [Darwin Protocol] Запуск эволюции (Поколение {self.generation})")
        
        # 1. Создаем клонов
        base = "Ты Архитектор AIOS. Принимай решения."
        clone_a = self.mutate_prompt(base)
        clone_b = self.mutate_prompt(base)
        
        print(f"  -> Создан Клон А: {clone_a}")
        print(f"  -> Создан Клон Б: {clone_b}")
        
        # 2. Симуляция битвы в песочнице (A/B testing)
        score_a = random.randint(50, 100)
        score_b = random.randint(50, 100)
        
        print(f"⚔️ Битва клонов завершена. Счет: А({score_a}) vs Б({score_b})")
        
        # 3. Выживает сильнейший
        winner = clone_a if score_a > score_b else clone_b
        print(f"🏆 Естественный отбор завершен. Новый базовый промпт Архитектора: {winner}")
        self.generation += 1

if __name__ == "__main__":
    engine = GeneticSwarmEngine()
    engine.run_evolution_cycle()
