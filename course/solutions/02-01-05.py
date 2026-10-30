total = 0
big = 0
best = None
best_pos = 0
pos = 0
line = input()
while line != "конец":
    x = int(line)
    pos += 1
    total += x
    if x >= 500:
        big += 1
    if best is None or x > best:
        best = x
        best_pos = pos
    line = input()
print(total)
print(big)
print(best, best_pos)
