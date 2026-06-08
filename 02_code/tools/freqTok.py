from collections import Counter

def read_digits(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        text = f.read()
    digits = [ch for ch in text if ch.isdigit()]
    return ''.join(digits)

def get_ngrams(seq, n):
    return [seq[i:i+n] for i in range(len(seq)-n+1)]

def main():
    filename = 'токены цифр.txt'
    digits = read_digits(filename)
    total_digits = len(digits)
    print(f"Всего цифр: {total_digits}\n")

    # Монограммы (отдельные цифры)
    mono_counter = Counter(digits)
    print("--- 1-граммы (цифры) ---")
    print(f"Уникальных: {len(mono_counter)} из 10 возможных")
    # Проверим, все ли цифры есть
    missing = set(str(i) for i in range(10)) - set(mono_counter.keys())
    if missing:
        print(f"Отсутствуют: {sorted(missing)}")
    else:
        print("Присутствуют все цифры.")
    print("\nЧастоты:")
    for digit in sorted(mono_counter.keys()):
        print(f"{digit}: {mono_counter[digit]}")
    print()

    for n in [2, 3, 4, 5]:
        ngrams = get_ngrams(digits, n)
        counter = Counter(ngrams)
        unique = len(counter)
        possible = 10**n
        print(f"--- {n}-граммы ---")
        print(f"Всего {n}-грамм: {len(ngrams)}")
        print(f"Уникальных: {unique} из {possible} возможных")
        missing_count = possible - unique
        if missing_count > 0:
            print(f"Отсутствует комбинаций: {missing_count}")
            if n <= 3:
                all_possible = set(str(i).zfill(n) for i in range(possible))
                missing_list = sorted(all_possible - set(counter.keys()))
                print(f"Список отсутствующих: {missing_list}")
            else:
                print("Список слишком большой.")
        else:
            print("Присутствуют все возможные комбинации.")
        print("\nТоп-10 самых частых:")
        for ngram, count in counter.most_common(10):
            print(f"{ngram}: {count}")
        print()

if __name__ == '__main__':
    main()