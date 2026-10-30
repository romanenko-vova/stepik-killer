"""
Эталонные решения задач каталога и дополнительные вводы для новых тестов.

Ключ — cat_key задачи (модуль-тема-задача, как в db/catalog.json).
scripts/check_catalog.py гоняет каждый эталон на всех тестах задачи; новые тесты
получают ожидаемый вывод только от эталона, который прошёл все старые.
"""

REFS: dict[str, str] = {}
EXTRA: dict[str, list[str]] = {}


def ref(key: str, code: str, extra: list[str] | None = None):
    REFS[key] = code.strip("\n")
    if extra:
        EXTRA[key] = extra


# ---------- Модуль 1. Переменные и условия ----------

ref("01-01-01", """
print(f"Привет, {input()}! Добро пожаловать в Романенко Учит.")
""", ["Ли", "Анна-Мария"])

ref("01-01-02", """
a = int(input())
b = int(input())
print(f"{a} + {b} = {a + b}")
print(f"{a} * {b} = {a * b}")
print(f"{a} - {b} = {a - b}")
print(f"{a} / {b} = {a / b}")
""", ["7\n2", "-6\n3", "0\n5"])

ref("01-01-03", """
lts = float(input())
dev = float(input())
if lts > dev:
    print("LTS новее")
elif dev > lts:
    print("DEV новее")
else:
    print("одинаковые")
""", ["1.5\n1.4", "0.1\n0.2", "3\n3.0"])

ref("01-01-04", """
r = int(input())
if r < 25:
    print("LOW")
elif r <= 74:
    print("MEDIUM")
else:
    print("HIGH")
""")

ref("01-01-05", """
a = int(input())
b = int(input())
c = int(input())
m = max(a, b, c)
if [a, b, c].count(m) > 1:
    print("TIE")
elif a == m:
    print("A")
elif b == m:
    print("B")
else:
    print("C")
""", ["5\n5\n5", "1\n7\n7", "-1\n-2\n-3"])

ref("01-01-06", """
lvl = input()
ok = False
if lvl == "user":
    ok = int(input()) % 3 == 2
elif lvl == "admin":
    a = int(input())
    b = int(input())
    ok = a + b > 100 or a * b < 300
print("Доступ разрешен" if ok else "В доступе отказано")
""")

ref("01-02-01", """
n = int(input())
print("YES" if 0 <= n <= 255 and n % 2 == 0 else "NO")
""", ["0", "255", "256", "-2", "254"])

ref("01-02-02", """
s = input()
print("ALERT" if "взлом" in s or "ддос" in s or "атака" in s else "CLEAR")
""", ["атакаддос", "просто текст", "ддосер"])

ref("01-02-03", """
v = int(input())
if v < 60:
    print(f"Прибавьте {60 - v} км/ч до минимально разрешенной скорости")
elif v > 120:
    print(f"Сбросьте {v - 120} км/ч до максимально разрешенной скорости")
else:
    print("Скорость в норме")
print("Счастливого пути")
""", ["0", "121", "59", "90"])

ref("01-02-04", """
n = int(input())
last = n % 10
print("Подходит" if n % 2 == 0 and last % 3 != 0 and n % 10 != 0 else "Не подходит")
""", ["16", "28", "32", "7", "100"])

ref("01-02-05", """
print(int(input()) % 10)
""", ["5", "1234567890", "909"])

ref("01-02-06", """
s = input().strip()
d = [int(c) for c in s]
total = sum(x * w for x, w in zip(d[:5], [2, 1, 2, 1, 2]))
if total >= 10:
    total += sum(int(c) for c in str(total))
control = (10 - total % 10) % 10
print("ACCESS" if control == d[5] else "DENY")
""", ["000000", "111111", "999999", "246800"])

ref("01-02-07", """
n = int(input())
if n % 100 in (11, 12, 13, 14):
    w = "питонистов"
elif n % 10 == 1:
    w = "питонист"
elif n % 10 in (2, 3, 4):
    w = "питониста"
else:
    w = "питонистов"
print(n, w)
""")

ref("01-02-08", """
m = int(input())
print(f"{m // 60}:{m % 60:02d}")
""")

ref("01-02-09", """
n = int(input())
t = 8 * 60
for i in range(1, n + 1):
    t += 40
    if i != n:
        if i % 5 == 0:
            t += 20
        elif i % 2 == 1:
            t += 10
        else:
            t += 15
t %= 24 * 60
print(f"{t // 60}:{t % 60:02d}")
""")

# ---------- Модуль 2. Циклы ----------

ref("02-01-01", """
n = int(input())
i = 1
while i <= n:
    print(i)
    i += 1
""", ["1", "5", "10"])

ref("02-01-02", """
n = int(input())
while n >= 1:
    print(n)
    n -= 1
print("Пуск!")
""", ["1", "3", "10"])

ref("02-01-03", """
s = 0
x = int(input())
while x != 0:
    s += x
    x = int(input())
print(s)
""", ["0", "5\n0", "-5\n5\n0", "100\n0\n7"])

ref("02-01-04", """
n = 0
while input() != "стоп":
    n += 1
print(n)
""", ["стоп\nа", "x\ny\nz\nw\nстоп"])

ref("02-01-05", """
xs = []
while True:
    s = input()
    if s == "конец":
        break
    xs.append(int(s))
print(sum(xs) / len(xs))
print(sum(1 for x in xs if x >= 400))
m = max(xs)
print(m, xs.index(m) + 1)
""", ["400\nконец", "100\n500\n300\nконец", "450\n350\nконец"])

ref("02-01-06", """
n = int(input())
ok = n > 1
d = 2
while d * d <= n:
    if n % d == 0:
        ok = False
    d += 1
print("Да" if ok else "Нет")
""")

ref("02-01-07", """
pin = input()
tries = 0
while tries < 3:
    try:
        s = input()
    except EOFError:
        break
    if len(s) != 4:
        continue
    tries += 1
    if s == pin:
        print("Добро пожаловать!")
        break
else:
    print("Ничего страшного, все ваши деньги забрал Греф!")
""")

ref("02-01-08", """
cmds = []
while True:
    s = input()
    if s == ".":
        break
    cmds.append(s)
if any("exit" in c for c in cmds):
    print("СБОЙ ПРИ ЧТЕНИИ КОМАНД")
elif len(cmds) % 2 == 0:
    print("СКРИПТ УДАЧНЫЙ")
elif len(cmds) % 7 == 2:
    print("СКРИПТ НЕУДАЧНЫЙ")
else:
    print("ПИШИ ПО НОВОЙ")
""", [".", "a\n.", "exit\n.", "\n".join(f"c{i}" for i in range(16)) + "\n."])

ref("02-02-01", """
for i in range(int(input())):
    print(i)
""", ["1", "3", "10"])

ref("02-02-02", """
n = int(input())
for i in range(n, -1, -1):
    print(i, end=" ")
""", ["0", "1", "3"])

ref("02-02-03", """
a = int(input())
b = int(input())
step = 1 if a <= b else -1
for i in range(a, b + step, step):
    print(i, end=";")
""", ["3\n3", "-2\n2", "0\n-3"])

ref("02-02-04", """
s = input()
total = sum(int(c) for c in s)
print("ДА" if total % len(s) == 0 else "НЕТ")
""")

ref("02-02-05", """
s = input()
print("ДА" if len(s) == 4 and s.isdigit() else "НЕТ")
""")

ref("02-02-06", """
total = 0
for ch in input():
    if ch.isdigit():
        total += int(ch)
print(total)
""", ["abc", "1111", "a9b8c7"])

ref("02-02-07", """
s = input()
control = int(input())
digits = [int(c) for c in s if c.isdigit()]
print("ДА" if sum(digits) * len(digits) == control else "НЕТ")
""", ["abc\n0", "12\n6", "5\n5", "99\n36", "99\n18"])

ref("02-02-08", """
s = input()
for ch in "олег":
    print(f"Букв '{ch}' в сообщении: {s.count(ch)}")
""", ["ОЛЕГ", "гггг", "лето"])

ref("02-02-09", """
a = int(input())
op = input()
b = int(input())
print(a + b if op == "+" else a * b)
""", ["0\n*\n100", "-3\n+\n3", "7\n*\n7"])

ref("02-02-10", """
result = int(input())
while True:
    op = input()
    if op == "=":
        break
    x = int(input())
    if op == "+":
        result += x
    elif op == "-":
        result -= x
    elif op == "*":
        result *= x
    else:
        result //= x
print(result)
""", ["5\n=", "2\n*\n3\n*\n4\n=", "100\n-\n1\n/\n9\n=", "7\n/\n2\n="])

# ---------- Модуль 3. Коллекции ----------

ref("03-01-01", """
xs = []
while True:
    s = input()
    if s == "конец":
        break
    xs.append(int(s))
print(xs)
print(f"Итого: {round(sum(xs) / 1024, 2)} КБ")
""", ["1024\nконец", "512\n512\n512\nконец", "100\nконец"])

ref("03-01-02", """
n = int(input())
xs = []
while len(xs) < n:
    s = input()
    if s == "конец":
        break
    x = int(s)
    if x > 200:
        xs.append(x)
print(xs)
print(f"Итого: {round(sum(xs) / 1024, 2)} КБ")
""", ["1\n100\n300", "2\n100\nконец", "2\n201\n202"])

ref("03-01-03", """
n = int(input())
ts = [float(input()) for _ in range(n)]
print(ts.index(min(ts)) + 1)
""", ["1\n5.5", "3\n2\n1\n1", "4\n9.99\n10\n9.98\n11"])

ref("03-01-04", """
n = int(input())
ts = [float(input()) for _ in range(n)]
order = sorted(range(n), key=lambda i: (ts[i], i))
print("Топ 3 бегуна:")
for place, i in enumerate(order[:3], 1):
    print(f"{place}. Спортсмен {i + 1} - {ts[i]}")
print(f"Среднее время: {sum(ts) / n:.1f}")
print(f"Количество спортсменов, которые пробежали быстрее 10с: {sum(1 for t in ts if t < 10)}")
""", ["3\n9\n9\n9", "5\n10\n9.5\n10.5\n8\n12"])

ref("03-01-05", """
words = input().split()
best = max(words, key=len)
print(best, len(best))
""", ["а бб ввв", "кот", "мир программистов"])

ref("03-01-06", """
items = []
while True:
    s = input()
    if s == "конец":
        break
    name, price = s.split()
    items.append((name, int(price)))
best = max(items, key=lambda x: x[1])
print(best[0], best[1])
rest = [name for name, _ in items]
rest.remove(best[0])
print(rest)
""", ["a 1\nb 2\nконец", "x 10\ny 10\nконец"])

ref("03-01-07", """
words = input().split()
ok = len(words) % 2 == 0 and all("о" in w.lower() for w in words)
print("Идеальная" if ok else "Не идеальная")
""")

STRIP_32 = '.,—-"«»'

ref("03-02-01", f"""
words = [w.strip('{STRIP_32}').lower() for w in input().split()]
words = [w for w in words if w]
m = max(len(w) for w in words)
print(", ".join(w for w in words if len(w) == m))
""", ["Кот, пёс.", "Мама мыла раму.", "«Привет», сказал он."])

ref("03-02-02", f"""
words = input().split()
lens = [len(w.strip('{STRIP_32}')) for w in words]
m = max(lens)
left = [w for w, n in zip(words, lens) if n != m]
print(" ".join(left).rstrip(".") + ".")
""", ["Кот ел рыбу.", "Мы пишем код"])

ref("03-02-03", """
a = set(input().split())
b = set(input().split())
common = sorted(a & b)
print(", ".join(common) if common else "никто")
""", ["Аня\nАня", "А Б В\nГ Д", "Ян Ия Ян\nИя"])

ref("03-02-04", """
everyone = input().split()
pizza = set(input().split())
plain = set(input().split())
def show(names):
    return ", ".join(sorted(names)) if names else "никто"
print(show(pizza | plain))
print(show(pizza & plain))
print(show(set(everyone) - pizza - plain))
""", ["Петя Вася\nПетя\nПетя", "Я Ты Он\nОн\nТы", "А Б В Г\nА\nБ"])

ref("03-02-05", """
ips = set()
while True:
    s = input()
    if s == "конец файла":
        break
    ip, url, _code = [p.strip() for p in s.split("|")]
    if "env" in url.lower():
        ips.add(ip)
print(";".join(sorted(ips)) if ips else "Всё чисто")
""", [
    "1.1.1.1 | /ENV | 200\n1.1.1.1 | /a.env | 404\nконец файла",
    "8.8.8.8 | /home | 200\nконец файла",
    "5.5.5.5 | /environment | 200\n3.3.3.3 | /x | 200\nконец файла",
])

ref("03-02-06", """
n, m = map(int, input().split())
print(*[max(map(int, input().split())) for _ in range(n)])
""", ["1 1\n5", "1 3\n-1 -2 -3", "3 2\n1 2\n3 4\n5 6"])

ref("03-02-07", """
n, m = map(int, input().split())
for r in range(n):
    print(*[c * n + r + 1 for c in range(m)])
""", ["1 1", "1 4", "3 1"])

ref("03-03-01", """
print([name[0] + "." for name in input().split(",")])
""", ["Zed", "Ann,Bob,Cid,Dan,Eve"])

ref("03-03-02", """
print([m for m in input().split() if m.endswith("@gmail.com")])
""", ["a@gmail.com", "gmail.com x@gmail.co", "b@gmail.com.ru c@gmail.com"])

ref("03-03-03", """
keys = input().split()
values = [int(x) for x in input().split()]
print(dict(zip(keys, values)))
""", ["x\n1", "k v\n0 -5", "a b c\n3 2 1", "one two\n10 20"])

ref("03-03-04", """
keys = input().split(";")
nums = [int(x) for x in input().split(",")]
d = {}
for k, v in zip(keys, nums):
    d[k] = v
if len(nums) > len(keys):
    d[keys[-1]] += sum(nums[len(keys):])
print(d)
""", ["a\n1", "a;b\n1", "p;q;r\n1,1,1,1,1"])

ref("03-03-05", """
d = {}
for ch in input().lower():
    d[ch] = d.get(ch, 0) + 1
print(d)
""", ["aA", "!!", "Да да"])

ref("03-03-06", """
people = {'Вова':{'age':58, 'money':30000, 'gender':'м'}, 'Саша':{'age':24, 'money':50000,'gender':'ж'}, 'Коля':{'age':13, 'money':10000,'gender':'м'}, 'Аня':{'age':42, 'money':100000,'gender':'ж'}}
ages = [p['age'] for p in people.values()]
print(f"Средний возраст: {sum(ages) / 4} года")
print(f"Всего денег: {sum(p['money'] for p in people.values())} рублей")
left = sum((65 if p['gender'] == 'м' else 60) - p['age'] for p in people.values())
print(f"Осталось работать: {left} лет")
""")

ref("03-03-07", """
n = int(input())
prices = {}
for _ in range(n):
    name, price = input().split()
    prices[name] = int(price)
print(sum(prices[x] for x in input().split() if x in prices))
""", ["1\na 10\na a a", "2\nx 1\ny 2\nz", "3\na 1\nb 2\nc 3\nc b a"])

ref("03-03-08", """
n = int(input())
prices = {}
for _ in range(n):
    name, price = input().split()
    prices[name] = int(price)
buys = [x for x in input().split() if x in prices]
counts = {x: buys.count(x) for x in set(buys)}
print("Общее позиций:", len(buys))
print("Сумма:", sum(prices[x] for x in buys))
print("Уникальных:", len(counts))
print("Чаще всего:", min(counts, key=lambda x: (-counts[x], x)))
print("Самая дорогая:", min(counts, key=lambda x: (-prices[x], x)))
""", ["1\na 5\na", "3\nx 3\ny 2\nz 1\nz y y"])

# ---------- Модуль 4. Функции ----------

ref("04-01-01", """
def greet(name):
    return f"Привет, {name}!"
print(greet(input()))
""", ["Аня", "Bob", "Мария Ивановна", "X"])

ref("04-01-02", """
def longest_word(sentence):
    words = [w.strip('.,—-"«»:?!') for w in sentence.split()]
    return max(words, key=len)
print(longest_word(input()))
""", ["Да!", "Кто здесь?", "«Ура», — крикнул он."])

ref("04-01-03", """
def repeat_char(ch, n):
    return ch * n
print(repeat_char(input(), int(input())))
""", ["z\n3", "*\n10", "я\n2"])

ref("04-01-04", """
def decode_string(s):
    return "".join(s[i] * int(s[i + 1]) for i in range(0, len(s), 2))
print(decode_string(input()))
""", ["a9", "q1", "a1b1c1"])

ref("04-01-05", """
def encode_string(s):
    out = []
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append(f"{s[i]}{j - i}")
        i = j
    return "".join(out)
print(encode_string(input()))
""", ["a", "abc", "aaaaaaaaab"])

ref("04-01-06", """
def check_card_number(card):
    total = 0
    for i, c in enumerate(card):
        x = int(c)
        if i % 2 == 0:
            x *= 2
            if x > 9:
                x -= 9
        total += x
    return total % 10 == 0
print(check_card_number(input().strip()))
""", ["0000000000000000", "5555555555554444", "1111111111111111"])
