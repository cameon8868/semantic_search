from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import json
import numpy as np
import os
import uvicorn
import re

app = FastAPI()

print("=" * 50)
print("   📚 ЗАГРУЗКА ДАННЫХ...")
print("=" * 50)

# ============================================================
# ЗАГРУЗКА JSON
# ============================================================
def load_json_safe(filename):
    with open(filename, 'rb') as f:
        raw = f.read()
    
    clean = bytearray()
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch < 0x80:
            if ch >= 32 or ch == 10 or ch == 13:
                clean.append(ch)
            i += 1
        elif (ch == 0xD0 or ch == 0xD1) and i + 1 < len(raw):
            ch2 = raw[i + 1]
            if 0x80 <= ch2 <= 0xBF:
                clean.append(ch)
                clean.append(ch2)
                i += 2
            else:
                i += 2
        else:
            i += 1
    
    text = clean.decode('utf-8', errors='ignore')
    return json.loads(text)

if not os.path.exists('vectors.json'):
    print("❌ vectors.json не найден! Сначала запусти tfidf.exe")
    exit(1)

try:
    data = load_json_safe('vectors.json')
    print("✅ JSON загружен!")
except Exception as e:
    print(f"❌ Ошибка загрузки: {e}")
    exit(1)

# ============================================================
# ИЗВЛЕЧЕНИЕ ДАННЫХ
# ============================================================
doc_vectors = []
doc_texts = []
doc_full_texts = []

for doc in data['documents']:
    doc_vectors.append(np.array(doc['vector']))
    doc_texts.append(doc.get('text', ''))
    doc_full_texts.append(doc.get('full_text', doc.get('text', '')))

doc_vectors = np.array(doc_vectors)
vocab_size = doc_vectors.shape[1]
total_docs = len(doc_texts)

print(f"📊 Документов: {total_docs}")
print(f"📚 Размер словаря: {vocab_size}")

# ============================================================
# ЗАГРУЗКА СЛОВАРЯ
# ============================================================
vocabulary = data.get('vocabulary', {})

if vocabulary:
    word_to_idx = {word: int(idx) for word, idx in vocabulary.items()}
    print(f"✅ Загружен словарь: {len(word_to_idx)} слов")
    
    # Показываем первые 10 слов для диагностики
    print("📝 Первые 10 слов в словаре:")
    for i, (word, idx) in enumerate(list(word_to_idx.items())[:10]):
        print(f"   {i+1}. '{word}' → {idx}")
else:
    word_to_idx = {}
    print("⚠️ Словарь не найден!")

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def split_words(text: str):
    """Разбивает текст на слова (только буквы и цифры)"""
    words = re.findall(r'[a-zA-Zа-яА-Я0-9]+', text.lower())
    return words

def vectorize_query(query: str):
    """Превращает запрос в TF-IDF вектор"""
    vec = np.zeros(vocab_size)
    words = split_words(query)
    
    if not words:
        return vec
    
    # Считаем частоту слов в запросе
    word_counts = {}
    for w in words:
        word_counts[w] = word_counts.get(w, 0) + 1
    
    total_words = len(words)
    
    # Используем словарь
    matched_words = 0
    for word, count in word_counts.items():
        if word in word_to_idx:
            idx = word_to_idx[word]
            tf = count / total_words
            vec[idx] = tf
            matched_words += 1
    
    # Диагностика: выводим, сколько слов нашлось
    print(f"🔍 Запрос: '{query}' → найдено {matched_words}/{len(words)} слов в словаре")
    
    return vec

def cosine_similarity(a, b):
    """Косинусное сходство между двумя векторами"""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return np.dot(a, b) / (norm_a * norm_b)

def search(query: str, top_k=5):
    """Поиск по запросу"""
    q_vec = vectorize_query(query)
    
    # Диагностика: показываем норму вектора запроса
    q_norm = np.linalg.norm(q_vec)
    print(f"📊 Норма вектора запроса: {q_norm:.4f}")
    
    results = []
    for i, doc_vec in enumerate(doc_vectors):
        sim = cosine_similarity(q_vec, doc_vec)
        score = round(sim * 100, 2)
        results.append({
            "score": score,
            "index": i,
            "text": doc_texts[i],
            "full_text": doc_full_texts[i]
        })
    
    # Сортируем по убыванию сходства
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Показываем топ-3 скора для диагностики
    print(f"📊 Топ-3 скоры: {[r['score'] for r in results[:3]]}")
    
    return [
        {
            "score": r["score"],
            "text": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
            "full_text": r["full_text"]
        }
        for r in results[:top_k]
    ]

# ============================================================
# ВЕБ-ИНТЕРФЕЙС
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def index():
    with open('web.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.get("/search")
async def search_endpoint(q: str = Query(...)):
    if not q or len(q.strip()) < 1:
        return {"error": "Пустой запрос"}
    
    try:
        results = search(q, top_k=5)
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# ЗАПУСК
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("   🚀 ЗАПУСК СЕРВЕРА")
    print("=" * 50)
    print("📍 Откройте в браузере: http://127.0.0.1:8000")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=8000)