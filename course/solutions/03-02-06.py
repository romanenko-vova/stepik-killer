n, m = map(int, input().split())
rows = []
for _ in range(n):
    rows.append([int(x) for x in input().split()])
print(*[max(row) for row in rows])
best = 0
for i in range(1, n):
    if sum(rows[i]) > sum(rows[best]):
        best = i
print(best + 1)
