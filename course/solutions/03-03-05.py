points = {}
line = input()
while line != "конец":
    name, value = line.split()
    points[name] = points.get(name, 0) + int(value)
    line = input()
for name in sorted(points):
    print(f"{name}: {points[name]}")
