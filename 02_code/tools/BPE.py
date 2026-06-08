from collections import Counter, defaultdict

def bpe(text, num_merges=100, min_freq=2):
    tokens = list(text)  # начальные токены - каждый символ
    # будем хранить частоты пар
    def get_stats(tokens):
        pairs = defaultdict(int)
        for i in range(len(tokens)-1):
            pairs[(tokens[i], tokens[i+1])] += 1
        return pairs

    merges = []
    for i in range(num_merges):
        pairs = get_stats(tokens)
        if not pairs:
            break
        # выбираем пару с максимальной частотой
        best_pair = max(pairs, key=pairs.get)
        best_freq = pairs[best_pair]
        if best_freq < min_freq:
            break
        # объединяем
        new_token = ''.join(best_pair)
        # обновляем список токенов, заменяя пару на новый токен
        new_tokens = []
        j = 0
        while j < len(tokens):
            if j < len(tokens)-1 and (tokens[j], tokens[j+1]) == best_pair:
                new_tokens.append(new_token)
                j += 2
            else:
                new_tokens.append(tokens[j])
                j += 1
        tokens = new_tokens
        merges.append((best_pair, best_freq))
        print(f"Шаг {i+1}: объединяем {best_pair} (частота {best_freq}) -> {new_token}")
        if i < 5 or i % 10 == 0:  # можно выборочно показывать частоты токенов
            # покажем топ-10 токенов
            cnt = Counter(tokens)
            print("Топ токенов сейчас:", cnt.most_common(10))
    return tokens, merges

def read_digits(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        text = f.read()
    digits = [ch for ch in text if ch.isdigit()]
    return ''.join(digits)

def main():
    filename = 'токены цифр.txt'
    digits = read_digits(filename)
    print(f"Всего цифр: {len(digits)}")
    tokens, merges = bpe(digits, num_merges=100, min_freq=5)
    # после завершения выведем финальные статистики
    final_counter = Counter(tokens)
    print("\nИтоговые токены (первые 50 наиболее частых):")
    for tok, cnt in final_counter.most_common(50):
        print(f"{tok}: {cnt}")

if __name__ == '__main__':
    main()