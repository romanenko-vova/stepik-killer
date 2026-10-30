n = int(input())
times = []
for _ in range(n):
    times.append(int(input()))
print(times.index(min(times)) + 1)
