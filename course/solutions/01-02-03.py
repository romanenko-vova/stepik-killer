speed = int(input())
if speed < 10:
    print(f"Прибавь {10 - speed} км/ч")
elif speed > 25:
    print(f"Сбрось {speed - 25} км/ч")
else:
    print("Скорость в норме")
