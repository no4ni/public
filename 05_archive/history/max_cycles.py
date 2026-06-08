from bs4 import BeautifulSoup

with open('E:\AGI\history\Петро.txt', 'r', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, 'html.parser')
target_class = 'ef46fbc6'

# Найти все родительские div с классом ef46fbc6
parent_divs = soup.find_all('div', class_=target_class)

for i, parent in enumerate(parent_divs):
    # Непосредственные дети
    direct_children = parent.find_all(recursive=False)
    # Фильтр только <div>
    level_2_divs = [c for c in direct_children if c.name == 'div']
    count = len(level_2_divs)
    
    print(f"Div #{i}: {count} вложенных div")