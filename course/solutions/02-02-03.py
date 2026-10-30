a = int(input())
b = int(input())
if a <= b:
    numbers = range(a, b + 1)
else:
    numbers = range(a, b - 1, -1)
print(*numbers, sep=";")
