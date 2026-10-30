n = int(input())
menu = {}
for _ in range(n):
    name, price = input().split()
    menu[name] = int(price)
line = input()
while line != "конец":
    if line in menu:
        print(menu[line])
    else:
        print("нет в меню")
    line = input()
