code = input()
total = 0
for i in range(len(code)):
    if i % 2 == 0:
        total += int(code[i]) * 3
    else:
        total += int(code[i])
print("ВЕРНЫЙ" if total % 10 == 0 else "ОШИБКА")
