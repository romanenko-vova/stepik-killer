n = int(input())
if 11 <= n % 100 <= 14:
    word = "заказов"
elif n % 10 == 1:
    word = "заказ"
elif 2 <= n % 10 <= 4:
    word = "заказа"
else:
    word = "заказов"
print(n, word)
