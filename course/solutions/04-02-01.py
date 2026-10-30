def clean_name(s):
    return s.strip().capitalize()


names = [clean_name(part) for part in input().split(",")]
print(names)
