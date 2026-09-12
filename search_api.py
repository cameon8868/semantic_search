from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import json
import numpy as np
import os
import uvicorn
import re
from sentence_transformers import SentenceTransformer, util

app = FastAPI()

print("=" * 50)
print("   📚 ЗАГРУЗКА ДАННЫХ...")
print("=" * 50)



# ============================================================
# ЗАГРУЗКА JSON (без изменений)
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
# ИЗВЛЕЧЕНИЕ ДАННЫХ (без изменений)
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
# ЗАГРУЗКА СЛОВАРЯ (без изменений)
# ============================================================
vocabulary = data.get('vocabulary', {})

if vocabulary:
    word_to_idx = {word: int(idx) for word, idx in vocabulary.items()}
    print(f"✅ Загружен словарь: {len(word_to_idx)} слов")
else:
    word_to_idx = {}
    print("⚠️ Словарь не найден!")

# ============================================================
# 🆕 ЗАГРУЗКА SBERT
# ============================================================
print("\n" + "=" * 50)
print("   🧠 ЗАГРУЗКА SBERT-МОДЕЛИ...")
print("=" * 50)

SBERT_MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'

try:
    sbert_model = SentenceTransformer(SBERT_MODEL_NAME)
    print(f"✅ Модель загружена: {SBERT_MODEL_NAME}")
    print(f"📐 Размерность эмбеддинга: {sbert_model.get_sentence_embedding_dimension()}")
except Exception as e:
    print(f"❌ Ошибка загрузки SBERT: {e}")
    sbert_model = None

# Генерация эмбеддингов для всех документов (один раз при старте)
sbert_embeddings = None
if sbert_model is not None:
    print("\n🔄 Генерация эмбеддингов для документов...")
    try:
        sbert_embeddings = sbert_model.encode(
            doc_full_texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2-нормализация → косинус = скалярное произведение
        )
        print(f"✅ Эмбеддинги готовы: {sbert_embeddings.shape}")
    except Exception as e:
        print(f"❌ Ошибка генерации эмбеддингов: {e}")
        sbert_embeddings = None

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (без изменений)
# ============================================================
def split_words(text: str):
    words = re.findall(r'[a-zA-Zа-яА-Я0-9]+', text.lower())
    return words

def vectorize_query(query: str):
    vec = np.zeros(vocab_size)
    words = split_words(query)
    
    if not words:
        return vec
    
    word_counts = {}
    for w in words:
        word_counts[w] = word_counts.get(w, 0) + 1
    
    total_words = len(words)
    
    for word, count in word_counts.items():
        if word in word_to_idx:
            idx = word_to_idx[word]
            tf = count / total_words
            vec[idx] = tf
    
    return vec

def cosine_similarity(a, b):
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return np.dot(a, b) / (norm_a * norm_b)

# ============================================================
# ПОИСК: TF-IDF (существующий)
# ============================================================
def search_tfidf(query: str, top_k=5):
    q_vec = vectorize_query(query)
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
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return [
        {
            "score": r["score"],
            "text": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
            "full_text": r["full_text"]
        }
        for r in results[:top_k]
    ]

# ============================================================
# 🆕 ПОИСК: SBERT (семантический)
# ============================================================
def search_sbert(query: str, top_k=5):
    if sbert_model is None or sbert_embeddings is None:
        return [{"score": 0, "text": "SBERT недоступен", "full_text": ""}]
    
    # Кодируем запрос (с нормализацией, как и документы)
    query_emb = sbert_model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    
    # Косинус = скалярное произведение нормализованных векторов
    scores = np.dot(sbert_embeddings, query_emb)
    
    # Топ-K индексов
    top_idx = np.argsort(scores)[::-1][:top_k]
    
    results = []
    for i in top_idx:
        results.append({
            "score": round(float(scores[i]) * 100, 2),
            "text": doc_texts[i][:200] + "..." if len(doc_texts[i]) > 200 else doc_texts[i],
            "full_text": doc_full_texts[i]
        })
    return results

# ============================================================
# 🆕 ПОИСК: ГИБРИДНЫЙ (TF-IDF + SBERT через Reciprocal Rank Fusion)
# ============================================================
def search_hybrid(query: str, top_k=5, k_rrf=60):
    """
    Reciprocal Rank Fusion:
    RRF(d) = Σ 1 / (k + rank(d))
    где rank(d) — позиция документа в выдаче соответствующего метода.
    k_rrf — сглаживающая константа (классически 60).
    """
    # Получаем расширенные списки (больше, чем top_k, чтобы RRF работал корректно)
    tfidf_results = search_tfidf(query, top_k=len(doc_texts))
    sbert_results = search_sbert(query, top_k=len(doc_texts))
    
    # Собираем RRF-скоры по индексу документа
    # (в результатах нет индекса, поэтому восстановим его по тексту)
    text_to_idx = {doc_texts[i]: i for i in range(len(doc_texts))}
    
    rrf_scores = {}
    
    for rank, r in enumerate(tfidf_results):
        idx = text_to_idx.get(r['text'].replace('...', ''), None)
        if idx is None:
            # fallback: ищем по началу текста
            for i, t in enumerate(doc_texts):
                if t.startswith(r['text'][:100]):
                    idx = i
                    break
        if idx is not None:
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (k_rrf + rank + 1)
    
    for rank, r in enumerate(sbert_results):
        idx = text_to_idx.get(r['text'].replace('...', ''), None)
        if idx is None:
            for i, t in enumerate(doc_texts):
                if t.startswith(r['text'][:100]):
                    idx = i
                    break
        if idx is not None:
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (k_rrf + rank + 1)
    
    # Сортируем по убыванию RRF-скора
    sorted_idx = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)[:top_k]
    
    # Нормализуем скоры в проценты для отображения
    max_score = rrf_scores[sorted_idx[0]] if sorted_idx else 1.0
    
    results = []
    for idx in sorted_idx:
        results.append({
            "score": round(rrf_scores[idx] / max_score * 100, 2),
            "text": doc_texts[idx][:200] + "..." if len(doc_texts[idx]) > 200 else doc_texts[idx],
            "full_text": doc_full_texts[idx]
        })
    return results

# ============================================================
# ВЕБ-ИНТЕРФЕЙС
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def index():
    with open('web.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.get("/search")
async def search_endpoint(
    q: str = Query(...),
    mode: str = Query("tfidf")  # 🆕 tfidf | sbert | hybrid
):
    if not q or len(q.strip()) < 1:
        return {"error": "Пустой запрос"}
    
    try:
        if mode == "sbert":
            results = search_sbert(q, top_k=5)
        elif mode == "hybrid":
            results = search_hybrid(q, top_k=5)
        else:
            results = search_tfidf(q, top_k=5)
        
        return {"results": results, "mode": mode}
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
    print("📌 Режимы поиска: TF-IDF | SBERT | Гибрид")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=8000)