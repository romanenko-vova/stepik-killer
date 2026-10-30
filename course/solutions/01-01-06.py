role = input()
if role == "клиент":
    points = int(input())
    ok = points >= 100
elif role == "курьер":
    deliveries = int(input())
    rating = int(input())
    ok = deliveries >= 5 or rating == 5
else:
    ok = False
print("Вход выполнен" if ok else "Доступ закрыт")
