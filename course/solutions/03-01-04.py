words = input().split()
best = words[0]
for word in words:
    if len(word) > len(best):
        best = word
print(best, len(best))
