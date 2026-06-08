import sys
sys.path.append(r'E:\Jericho\Проекты\Riemann')
import oracul

# Первые 10 нетривиальных нулей дзета-функции (мнимые части)
riemann_zeros = [
    14.134725, 21.022040, 25.010857, 30.424876, 32.935061,
    37.586178, 40.918719, 43.327073, 48.005150, 49.773832
]

log = []
log.append("=" * 60)
log.append("АТАКА НА ГИПОТЕЗУ РИМАНА")
log.append("=" * 60)

# Линейный тренд
x = list(range(1, len(riemann_zeros) + 1))
y = riemann_zeros
n = len(x)
sum_x, sum_y = sum(x), sum(y)
sum_xy = sum(x[i] * y[i] for i in range(n))
sum_x2 = sum(x[i]**2 for i in range(n))
a = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
b = (sum_y - a * sum_x) / n
pred_11 = a * 11 + b
log.append(f"Линейный тренд: y = {a:.6f}*n + {b:.6f}")
log.append(f"Предсказанный 11-й ноль: {pred_11:.6f}")
log.append("Эталон (исторический): ~52.97")
log.append("")

# Оракул
log.append("Попытка нейро-оракула:")
try:
    formula = "t / (2*math.pi) * (math.log(t/(2*math.pi)) - 1)"
    for zero in riemann_zeros[:5]:
        out = oracul.predict_with_formula(formula, zero)
        log.append(f"  t={zero:.6f} -> {out}")
except Exception as e:
    log.append(f"  Ошибка оракула: {e}")

log.append("")
log.append("=" * 60)

# Сохраняем отчёт
report = '\n'.join(log)
with open(r'E:\Jericho\Хранитель\дневник.md', 'a', encoding='utf-8') as f:
    f.write('\n## Атака на Римана\n' + report + '\n')
print(report)
