import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.colors as mcolors

print("=" * 50)
print("   🎨 ВИЗУАЛИЗАЦИЯ ВЕКТОРОВ ДОКУМЕНТОВ")
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

try:
    data = load_json_safe('vectors.json')
    print("✅ JSON загружен!")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    exit()

print(f"📊 Документов: {data['metadata']['total_documents']}")
print(f"📚 Словарь: {data['metadata']['vocabulary_size']}")

# ============================================================
# ИЗВЛЕЧЕНИЕ ВЕКТОРОВ И МЕТАДАННЫХ
# ============================================================
vectors = []
texts = []
ids = []

for doc in data['documents']:
    if 'vector' in doc:
        vec = doc['vector'][:3]
        vectors.append(vec)
        texts.append(doc.get('text', '')[:30])
        ids.append(doc.get('id', 0))

if not vectors:
    print("❌ Нет векторов!")
    exit()

vectors = np.array(vectors)
print(f"✅ Загружено {len(vectors)} векторов")

# ============================================================
# 3D ВИЗУАЛИЗАЦИЯ (ПРОФЕССИОНАЛЬНАЯ)
# ============================================================
fig = plt.figure(figsize=(14, 11))
ax = fig.add_subplot(111, projection='3d')

# --- 1. Цветовая схема ---
# Используем градиент от синего к красному через фиолетовый
norm = plt.Normalize(vmin=vectors[:, 0].min(), vmax=vectors[:, 0].max())
colors = plt.cm.plasma(norm(vectors[:, 0]))

# --- 2. Рисуем точки ---
scatter = ax.scatter(
    vectors[:, 0], 
    vectors[:, 1], 
    vectors[:, 2],
    c=colors,
    s=80,                    # Размер точек
    alpha=0.8,               # Прозрачность
    edgecolors='white',      # Белая обводка
    linewidth=0.5,           # Толщина обводки
    cmap='plasma',
    depthshade=True          # Тени для объёма
)

# --- 3. Рисуем линии от точек к плоскости ---
for i in range(len(vectors)):
    ax.plot(
        [vectors[i, 0], vectors[i, 0]],
        [vectors[i, 1], vectors[i, 1]],
        [0, vectors[i, 2]],
        color='gray',
        alpha=0.15,
        linewidth=0.5
    )

# --- 4. Подписи для ТОП-10 точек ---
# Находим точки с наибольшим разбросом
distances = np.linalg.norm(vectors, axis=1)
top_indices = np.argsort(distances)[-10:][::-1]

for i in top_indices:
    ax.text(
        vectors[i, 0], 
        vectors[i, 1], 
        vectors[i, 2] + 0.02,
        f'{ids[i]}',
        fontsize=8,
        fontweight='bold',
        color='black',
        alpha=0.8,
        ha='center',
        va='bottom'
    )

# --- 5. Настройка осей ---
ax.set_xlabel('Компонента 1', fontsize=13, fontweight='bold', labelpad=12)
ax.set_ylabel('Компонента 2', fontsize=13, fontweight='bold', labelpad=12)
ax.set_zlabel('Компонента 3', fontsize=13, fontweight='bold', labelpad=12)

ax.set_title(
    '🧠 Векторное представление документов\n(первые 3 компоненты TF-IDF)',
    fontsize=16,
    fontweight='bold',
    pad=25
)

# --- 6. Стиль сетки ---
ax.grid(True, alpha=0.25, linestyle='--', linewidth=0.7)
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

# --- 7. Цветовая шкаба ---
cbar = plt.colorbar(scatter, ax=ax, shrink=0.6, pad=0.12)
cbar.set_label('Значение компоненты 1', fontsize=11, fontweight='bold')
cbar.ax.tick_params(labelsize=9)

# --- 8. Легенда ---
ax.text2D(
    0.02, 0.98,
    f'Документов: {len(vectors)}\nРазмерность: {len(vectors[0])}',
    transform=ax.transAxes,
    fontsize=10,
    verticalalignment='top',
    bbox=dict(boxstyle='round', facecolor='white', alpha=0.85, edgecolor='gray')
)

# --- 9. Интерактивный вид ---
ax.view_init(elev=25, azim=45)  # Угол обзора

plt.tight_layout()
plt.show()

print("✅ Визуализация завершена!")