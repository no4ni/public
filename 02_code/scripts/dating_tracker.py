# СИСТЕМА ТРЕКИНГА ЗНАКОМСТВ (начало с 09.02.2026)
# Автоматический сбор данных для будущего анализа

import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatingEvent:
    """Структура для хранения данных о знакомстве"""
    id: str
    date: str
    platform: str
    match_timestamp: Optional[str] = None
    conversation_started: bool = False
    conversation_days: int = 0
    meeting_proposed: bool = False
    meeting_date: Optional[str] = None
    second_meeting: bool = False
    notes: str = ""
    outcome: str = "pending"  # pending, success, failed
    
class DatingTracker:
    def __init__(self):
        self.events = []
        self.load_existing()
    
    def add_match(self, platform="Tinder", notes=""):
        """Добавляет новый матч"""
        event_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        event = DatingEvent(
            id=event_id,
            date=datetime.now().strftime("%Y-%m-%d"),
            platform=platform,
            match_timestamp=datetime.now().isoformat(),
            notes=notes
        )
        self.events.append(event)
        self.save()
        print(f"✓ Добавлен матч #{len(self.events)} на {platform}")
        return event_id
    
    def update_event(self, event_id, **kwargs):
        """Обновляет событие"""
        for event in self.events:
            if event.id == event_id:
                for key, value in kwargs.items():
                    if hasattr(event, key):
                        setattr(event, key, value)
                self.save()
                print(f"✓ Обновлено событие {event_id}")
                return True
        return False
    
    def get_conversion_funnel(self):
        """Рассчитывает текущую воронку конверсии"""
        total = len(self.events)
        if total == 0:
            return None
            
        funnel = {
            "matches": total,
            "conversations": sum(1 for e in self.events if e.conversation_started),
            "meetings_proposed": sum(1 for e in self.events if e.meeting_proposed),
            "meetings_happened": sum(1 for e in self.events if e.meeting_date),
            "second_meetings": sum(1 for e in self.events if e.second_meeting),
        }
        
        # Рассчитываем проценты
        funnel["conversation_rate"] = (funnel["conversations"] / total * 100) if total > 0 else 0
        funnel["proposal_rate"] = (funnel["meetings_proposed"] / funnel["conversations"] * 100) if funnel["conversations"] > 0 else 0
        funnel["meeting_rate"] = (funnel["meetings_happened"] / funnel["meetings_proposed"] * 100) if funnel["meetings_proposed"] > 0 else 0
        funnel["second_meeting_rate"] = (funnel["second_meetings"] / funnel["meetings_happened"] * 100) if funnel["meetings_happened"] > 0 else 0
        
        return funnel
    
    def show_dashboard(self):
        """Показывает текущую статистику"""
        funnel = self.get_conversion_funnel()
        
        if not funnel:
            print("┌─────────────────────────────────────┐")
            print("│   ТРЕКЕР ЗНАКОМСТВ - ПУСТО          │")
            print("│   Добавьте первый матч             │")
            print("└─────────────────────────────────────┘")
            return
        
        print("\n" + "="*45)
        print("    ДАШБОРД ТРЕКЕРА ЗНАКОМСТВ")
        print("="*45)
        print(f"📊 Всего матчей: {funnel['matches']}")
        print(f"💬 Диалоги: {funnel['conversations']} ({funnel['conversation_rate']:.1f}%)")
        print(f"📅 Предложено встреч: {funnel['meetings_proposed']} ({funnel['proposal_rate']:.1f}%)")
        print(f"🤝 Состоялось встреч: {funnel['meetings_happened']} ({funnel['meeting_rate']:.1f}%)")
        print(f"🔁 Повторные встречи: {funnel['second_meetings']} ({funnel['second_meeting_rate']:.1f}%)")
        print("="*45)
        
        # Рекомендации
        print("\nРЕКОМЕНДАЦИИ:")
        if funnel['matches'] < 10:
            print("1. Увеличить активность: цель - 10+ матчей в месяц")
            print("2. Оптимизировать профиль в приложениях")
        elif funnel['conversation_rate'] < 50:
            print("1. Улучшить первые сообщения")
            print("2. Анализировать шаблоны откликов")
        elif funnel['meeting_rate'] < 30:
            print("1. Практиковать предложения встреч в течение 3-7 дней")
            print("2. Предлагать конкретные варианты встреч")
        
        print("\nДля добавления данных используйте команды:")
        print("  tracker.add_match(platform='Tinder')")
        print("  tracker.update_event('match_id', conversation_started=True)")
    
    def save(self):
        """Сохраняет данные в JSON"""
        data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "events": [vars(e) for e in self.events]
        }
        with open("dating_tracker.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_existing(self):
        """Загружает существующие данные"""
        try:
            with open("dating_tracker.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for event_data in data.get("events", []):
                    event = DatingEvent(**event_data)
                    self.events.append(event)
        except FileNotFoundError:
            pass

# Глобальный трекер
tracker = DatingTracker()

# Интерфейс командной строки
if __name__ == "__main__":
    print("🚀 ТРЕКЕР ЗНАКОМСТВ ЗАПУЩЕН")
    print("Начало сбора данных: 09.02.2026")
    print("="*45)
    
    while True:
        print("\nДоступные команды:")
        print("1. Новый матч")
        print("2. Обновить событие")
        print("3. Показать статистику")
        print("4. Выход")
        
        choice = input("\nВыберите действие (1-4): ").strip()
        
        if choice == "1":
            platform = input("Платформа (Tinder/Badoo/Другое): ").strip() or "Tinder"
            notes = input("Заметки (необязательно): ").strip()
            tracker.add_match(platform, notes)
            
        elif choice == "2":
            event_id = input("ID события: ").strip()
            print("Что обновляем?")
            print("1. Начался диалог")
            print("2. Предложил встречу")
            print("3. Встреча состоялась")
            print("4. Была повторная встреча")
            
            update_choice = input("Выбор (1-4): ").strip()
            
            if update_choice == "1":
                tracker.update_event(event_id, conversation_started=True)
            elif update_choice == "2":
                tracker.update_event(event_id, meeting_proposed=True)
            elif update_choice == "3":
                date = input("Дата встречи (ГГГГ-ММ-ДД): ").strip()
                tracker.update_event(event_id, meeting_date=date)
            elif update_choice == "4":
                tracker.update_event(event_id, second_meeting=True)
                
        elif choice == "3":
            tracker.show_dashboard()
            
        elif choice == "4":
            tracker.save()
            print("Данные сохранены. До свидания!")
            break
