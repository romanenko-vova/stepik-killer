names = []
prices = []
line = input()
while line != "конец":
    name, price = line.split()
    names.append(name)
    prices.append(int(price))
    line = input()
i = prices.index(max(prices))
print(names[i], prices[i])
others = names[:i] + names[i + 1:]
print(others)
