minutes = int(input())
h = minutes // 60
m = minutes % 60
if m < 10:
    print(f"{h}:0{m}")
else:
    print(f"{h}:{m}")
