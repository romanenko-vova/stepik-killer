hour = int(input())
minute = int(input())
cook = int(input())
road = int(input())
total = hour * 60 + minute + cook + road
total = total % 1440
h = total // 60
m = total % 60
if m < 10:
    print(f"{h}:0{m}")
else:
    print(f"{h}:{m}")
