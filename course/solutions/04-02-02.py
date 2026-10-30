def discount(total, status):
    if status == "silver":
        return total - total * 5 // 100
    if status == "gold":
        return total - total * 10 // 100
    return total


line = input()
while line != "конец":
    name, status, total = line.split()
    print(f"{name}: {discount(int(total), status)}")
    line = input()
