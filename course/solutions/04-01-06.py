def check_card(number):
    total = 0
    for i in range(16):
        d = int(number[i])
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


print(check_card(input()))
