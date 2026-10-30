total = 0
count = 0
line = input()
while line != "конец":
    total += int(line)
    count += 1
    line = input()
if count > 0:
    total += 15 * ((count - 1) // 3)
h = total // 60
m = total % 60
if m < 10:
    print(f"{h}:0{m}")
else:
    print(f"{h}:{m}")
