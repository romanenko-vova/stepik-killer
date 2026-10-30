s = input()
letters = 0
digits = 0
ok = 4 <= len(s) <= 8
for ch in s:
    if "A" <= ch <= "Z":
        letters += 1
    elif "0" <= ch <= "9":
        digits += 1
    else:
        ok = False
if letters == 0 or digits == 0:
    ok = False
print("ВЕРНО" if ok else "НЕВЕРНО")
