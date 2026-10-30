def decode(s):
    result = ""
    for i in range(0, len(s), 2):
        result += s[i] * int(s[i + 1])
    return result


print(decode(input()))
