import json
import sys

class PromptGenerator:
    def __init__(self):
        self.templates = {
            'analysis': "Проанализируй следующий текст и выдели ключевые моменты:\n{text}",
            'summary': "Создай краткое содержание (3-5 пунктов):\n{text}",
            'creative': "Напиши креативный текст в стиле {style} на тему: {topic}",
            'technical': "Объясни техническую концепцию {concept} простыми словами"
        }
    
    def generate(self, template_type, **kwargs):
        if template_type in self.templates:
            return self.templates[template_type].format(**kwargs)
        return "Выберите тип: " + ", ".join(self.templates.keys())

if __name__ == "__main__":
    generator = PromptGenerator()
    print("Генератор промптов готов")
    print("Пример:", generator.generate('analysis', text="Тестовый текст"))
