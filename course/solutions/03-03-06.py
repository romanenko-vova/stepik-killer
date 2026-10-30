sold = {}
line = input()
while line != "конец":
    name, qty = line.split()
    sold[name] = sold.get(name, 0) + int(qty)
    line = input()
best = None
for name in sorted(sold):
    if best is None or sold[name] > sold[best]:
        best = name
print(best)
