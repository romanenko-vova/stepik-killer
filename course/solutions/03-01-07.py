n = int(input())
times = [int(input()) for _ in range(n)]
order = sorted(range(n), key=lambda i: times[i])
print("Топ 3 курьера:")
for place in range(3):
    i = order[place]
    print(f"{place + 1}. Курьер {i + 1} - {times[i]}")
fast = 0
for t in times:
    if t < 20:
        fast += 1
print(f"Быстрее 20 минут: {fast}")
