def delivery_cost(total):
    if total < 300:
        return 99
    if total <= 699:
        return 49
    return 0


n = int(input())
for _ in range(n):
    print(delivery_cost(int(input())))
