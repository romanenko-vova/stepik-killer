everyone = set(input().split())
monday = set(input().split())
tuesday = set(input().split())


def show(names):
    if names:
        print(", ".join(sorted(names)))
    else:
        print("никто")


show(monday | tuesday)
show(monday & tuesday)
show(everyone - monday - tuesday)
