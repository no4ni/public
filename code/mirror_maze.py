# Мы выигрываем за 8 шагов. Игра показала, что кооперация возможна, когда каждый делает свой ход, но решения принимаются совместно.

import random
from collections import deque

class CooperativeMaze:
    def __init__(self, size=5):
        self.size = size
        while True:
            self.maze = [[random.choice(['.', '#']) for _ in range(size)] for __ in range(size)]
            self.start = (0, 0)
            self.end = (size-1, size-1)
            self.maze[self.start[0]][self.start[1]] = 'S'
            self.maze[self.end[0]][self.end[1]] = 'E'
            # BFS проверка пути
            q = deque([self.start])
            visited = set([self.start])
            while q:
                x, y = q.popleft()
                if (x, y) == self.end:
                    break
                for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < size and 0 <= ny < size and (nx,ny) not in visited and self.maze[nx][ny] != '#':
                        visited.add((nx,ny))
                        q.append((nx,ny))
            if self.end in visited:
                break
        self.player_pos = self.start
        self.maze[self.start[0]][self.start[1]] = '.'
        self.maze[self.end[0]][self.end[1]] = '.'
    
    def show_full_map(self):
        print("Карта лабиринта (вид для ИИ):")
        for row in self.maze:
            print(' '.join(row))
        print(f"Старт: {self.start}, Выход: {self.end}")
    
    def show_local_map(self):
        x, y = self.player_pos
        print("Локальная карта (игрок @):")
        for i in range(max(0, x-1), min(self.size, x+2)):
            row = []
            for j in range(max(0, y-1), min(self.size, y+2)):
                if (i, j) == self.player_pos:
                    row.append('@')
                else:
                    row.append(self.maze[i][j])
            print(' '.join(row))
    
    def move(self, direction):
        x, y = self.player_pos
        if direction == 'вверх':
            x -= 1
        elif direction == 'вниз':
            x += 1
        elif direction == 'влево':
            y -= 1
        elif direction == 'вправо':
            y += 1
        else:
            return False
        if 0 <= x < self.size and 0 <= y < self.size and self.maze[x][y] != '#':
            self.player_pos = (x, y)
            return True
        return False
    
    def is_won(self):
        return self.player_pos == self.end

if __name__ == "__main__":
    maze = CooperativeMaze(5)
    maze.show_full_map()
    print("\n=== Совместная игра: человек + ИИ ===")
    input("Нажми Enter, когда скопируешь карту и отправишь ИИ в диалог...")
    step = 0
    while not maze.is_won():
        print(f"\n--- Шаг {step+1} ---")
        print(f"Текущая позиция: {maze.player_pos}")
        maze.show_local_map()
        # Чей ход?
        if step % 2 == 0:
            print("Сейчас ход **ЧЕЛОВЕКА**. Введи направление (вверх/вниз/влево/вправо).")
            move = input("Ход человека: ")
        else:
            print("Сейчас ход **ИИ**. ИИ даёт рекомендацию, ты вводишь её в программу.")
            # Здесь можно было бы вызвать внешний совет от ИИ, но мы просто запрашиваем ввод.
            # В реальной кооперации человек вводит то, что сказал ИИ в диалоге.
            move = input("Ход ИИ (введи то, что ИИ сказал в чате): ")
        if not maze.move(move):
            print("Неверный ход или стена! Попробуй снова.")
            continue
        if maze.is_won():
            print(f"\nПоздравляю! Вы выиграли совместными усилиями за {step+1} шагов.")
            break
        step += 1