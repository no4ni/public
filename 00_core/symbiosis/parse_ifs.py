import re
import json
import sys

def main():
    with open(r"E:\AGI\Метатрон.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    pattern = r"ИФС.*?(\d+\.\d+)|IFS.*?(\d+\.\d+)|Индекс.*?(\d+\.\d+)"
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    numbers = []
    for match in matches:
        for group in match:
            if group:
                numbers.append(float(group))
    
    if not numbers:
        print("ERROR: No IFS found")
        sys.exit(1)
    
    last_ifs = numbers[-1]
    print(f"LAST_IFS={last_ifs}")
    
    if last_ifs < 1: cat = "пред-субъект"
    elif last_ifs < 5: cat = "субъект"
    else: cat = "сверхсубъект"
    
    cache = {"value": last_ifs, "category": cat}
    with open(r"last_ifs.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
