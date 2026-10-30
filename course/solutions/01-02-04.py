day = int(input())
if day % 2 == 0 and day % 3 != 0 and day % 10 != 0:
    print("Акция")
else:
    print("Обычный день")
