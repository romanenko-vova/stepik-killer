a = int(input())
b = int(input())
c = int(input())
if a > b and a > c:
    print("бутерброд")
elif b > a and b > c:
    print("булочка")
elif c > a and c > b:
    print("сок")
else:
    print("ничья")
