password = input()
attempts = 0
while attempts < 3:
    guess = input()
    if len(guess) != 4:
        continue
    attempts += 1
    if guess == password:
        print("Вход выполнен")
        break
else:
    print("Пароль заблокирован")
