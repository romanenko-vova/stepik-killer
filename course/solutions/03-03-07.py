n = int(input())
menu = {}
for _ in range(n):
    name, price = input().split()
    menu[name] = int(price)

bought = [item for item in input().split() if item in menu]
counts = {}
for item in bought:
    counts[item] = counts.get(item, 0) + 1

print(f"Позиций: {len(bought)}")
print(f"Сумма: {sum(menu[item] for item in bought)}")
print(f"Разных: {len(counts)}")

names = sorted(counts)
frequent = names[0]
expensive = names[0]
for name in names:
    if counts[name] > counts[frequent]:
        frequent = name
    if menu[name] > menu[expensive]:
        expensive = name
print(f"Чаще всего: {frequent}")
print(f"Самое дорогое: {expensive}")
