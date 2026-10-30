yesterday = set(input().split())
today = set(input().split())
common = sorted(yesterday & today)
if common:
    print(", ".join(common))
else:
    print("никто")
