s = input()
total = 0
for ch in s:
    total += int(ch)
if total % len(s) == 0:
    print("ДА")
else:
    print("НЕТ")
