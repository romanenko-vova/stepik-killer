ips = set()
line = input()
while line != "конец":
    ip, url, code = line.split(" | ")
    if "env" in url.lower():
        ips.add(ip)
    line = input()
if ips:
    print(";".join(sorted(ips)))
else:
    print("Чисто")
