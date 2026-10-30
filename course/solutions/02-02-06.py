s = input()
total = 0
for ch in s:
    if "0" <= ch <= "9":
        total += int(ch)
print(total)
