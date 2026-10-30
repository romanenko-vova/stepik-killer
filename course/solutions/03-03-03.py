n = int(input())
menu = {}
for _ in range(n):
    name, price = input().split()
    menu[name] = int(price)
total = 0
for item in input().split():
    if item in menu:
        total += menu[item]
print(total)
