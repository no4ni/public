with open(r"E:\AGI\От Возникновения к Проектированию.txt", "rb") as f:
    raw = f.read()
decoded = raw.decode("utf-8", errors="replace")
print(decoded[:1000])