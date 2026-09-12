import wikipediaapi
import os
import time

os.makedirs('wikipedia_docs', exist_ok=True)

wiki_wiki = wikipediaapi.Wikipedia(
    language='ru',
    user_agent='SemanticSearchBot (myemail@example.com)'
)

topics = [
    "Нейронная сеть",
    "Искусственный интеллект",
    "Машинное обучение",
    "Глубокое обучение",
    "Информационная безопасность",
    "Криптография",
    "Физика",
    "Математика",
    "Программирование",
    "Алгоритм",
    "База данных",
    "Компьютерная сеть",
    "Квантовый компьютер",
    "Термодинамика",
    "Гравитация",
    "Дифференциальное уравнение",
    "Астрономия",
    "Биология",
    "Химия",
    "История",
    "Философия",
    "Экономика",
    "Психология"
]

article_count = 0

for topic in topics:
    print(f"🔍 Получаем статью: {topic}")
    
    try:
        page = wiki_wiki.page(topic)
        
        if page.exists() and len(page.text) > 100:
            safe_title = "".join(c for c in page.title if c.isalnum() or c in (' ', '-', '_'))
            filename = f"wikipedia_docs/{article_count:04d}_{safe_title[:50]}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(page.text)
            
            article_count += 1
            print(f"  [{article_count}] Сохранена: {page.title} ({len(page.text)} символов)")
        else:
            print(f"  Статья не найдена или слишком короткая")
            
    except Exception as e:
        print(f"  Ошибка: {e}")
    
    time.sleep(0.3) 

print(f"\nГОТОВО! Сохранено {article_count} статей")
print(f"Папка: wikipedia_docs/")
