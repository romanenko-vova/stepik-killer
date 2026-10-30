n, m = map(int, input().split())
for row in range(n):
    cells = []
    for col in range(m):
        cells.append(col * n + row + 1)
    print(*cells)
