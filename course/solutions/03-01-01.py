orders = []
line = input()
while line != "конец":
    orders.append(int(line))
    line = input()
print(orders)
print(f"Итого: {sum(orders)}")
