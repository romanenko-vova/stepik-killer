big = []
for word in input().split():
    x = int(word)
    if x > 500:
        big.append(x)
print(big)
print(len(big))
