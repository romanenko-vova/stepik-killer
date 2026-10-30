counts = {}
for dish in input().split():
    if dish in counts:
        counts[dish] += 1
    else:
        counts[dish] = 1
print(counts)
