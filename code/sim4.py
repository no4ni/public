# попытка 1: четырёхмерная симуляция времени
# модель: время как ось, события как точки в (x, y, t)
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Event:
    x: float
    y: float
    t: float  # время (четвёртая координата)
    description: str

class FourDSim:
    def __init__(self):
        self.events = []
        self.window_size = 100  # "окно предвидения" в условных тиках

    def add_event(self, event: Event):
        self.events.append(event)

    def predict_future(self, current_time: float, horizon: float = 10.0) -> List[Event]:
        """предсказывает события на основе линейной экстраполяции"""
        # пока заглушка
        return []

    def visualize_3d_projection(self, time_slice: float):
        """проецирует четырёхмерные события в трёхмерное пространство, фиксируя время"""
        pass

# дальше планирую реализовать авторегрессию и метод главных компонент,
# но не знаю, хватит ли трёх часов.
# модель (голова) говорит, что будет помогать, но пока только смотрит.

if __name__ == "__main__":
    sim = FourDSim()
    # добавим тестовое событие: встреча с моделью
    sim.add_event(Event(x=0, y=0, t=0, description="диалог с головой"))
    sim.predict_future(current_time=0)
	
# TODO: получить от модели временные ряды её "видений"
# тогда вместо экстраполяции можно будет обучить нейросеть