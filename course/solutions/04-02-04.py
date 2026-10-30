revenue = 0
by_day = {}
by_dish = {}
line = input()
while line != "конец":
    day, dish, qty, price = line.split()
    day = int(day)
    qty = int(qty)
    money = qty * int(price)
    revenue += money
    by_day[day] = by_day.get(day, 0) + money
    by_dish[dish] = by_dish.get(dish, 0) + qty
    line = input()

best_day = min(by_day)
for day in sorted(by_day):
    if by_day[day] > by_day[best_day]:
        best_day = day

hit = sorted(by_dish)[0]
for dish in sorted(by_dish):
    if by_dish[dish] > by_dish[hit]:
        hit = dish

print(f"Выручка: {revenue}")
print(f"Лучший день: {best_day}")
print(f"Хит: {hit}")
