def average(times):
    return sum(times) // len(times)


by_courier = {}
line = input()
while line != "конец":
    name, minutes = line.split()
    if name not in by_courier:
        by_courier[name] = []
    by_courier[name].append(int(minutes))
    line = input()
for name in sorted(by_courier):
    print(f"{name}: {average(by_courier[name])}")
