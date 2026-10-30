prices = [int(x) for x in input().split()]
prices.sort()
print(*prices)
print(sum(prices[:3]))
