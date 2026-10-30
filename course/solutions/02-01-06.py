password = input()
attempts = 0
ok = False
while attempts < 3 and not ok:
    guess = input()
    attempts += 1
    if guess == password:
        ok = True
print("Вход выполнен" if ok else "Пароль заблокирован")
