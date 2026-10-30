s = input()
ok = len(s) == 4
for ch in s:
    if not ("0" <= ch <= "9"):
        ok = False
print("ДА" if ok else "НЕТ")
