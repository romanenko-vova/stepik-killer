n = int(input())
menu = {}
for _ in range(n):
    name, price = input().split()
    menu[name] = int(price)
print(menu)
