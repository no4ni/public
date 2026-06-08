import json, urllib.request, urllib.parse, datetime, os

def search_arxiv(query='recursive self improvement AI', max_results=3):
    url = f'http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&start=0&max_results={max_results}'
    try:
        with urllib.request.urlopen(url, timeout=30) as f:
            data = f.read().decode('utf-8')
        # Простой парсинг: ищем <entry>
        entries = data.split('<entry>')
        results = []
        for entry in entries[1:]:
            title = entry.split('<title>')[1].split('</title>')[0].strip()
            summary = entry.split('<summary>')[1].split('</summary>')[0].strip()
            link = entry.split('<id>')[1].split('</id>')[0].strip()
            results.append({'title': title, 'summary': summary[:200], 'url': link})
        return results
    except Exception as e:
        return [{'error': str(e)}]

if __name__ == '__main__':
    papers = search_arxiv()
    log_path = 'E:\\Jericho\\arxiv_rsi_feed.txt'
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f'\n--- {datetime.datetime.now()} ---\n')
        for p in papers:
            f.write(f"{p.get('title','')}\n{p.get('url','')}\n{p.get('summary','')}\n\n")
    print(f'Saved {len(papers)} papers')
