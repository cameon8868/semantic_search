#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <map>
#include <filesystem>
#include <locale>
#include <iomanip>
#include <sstream>
#include <cmath>
#include <set>

using namespace std;
namespace fs = std::filesystem;

// ============================================================
// ОЧИСТКА ТЕКСТА (СОХРАНЯЕМ РУССКИЕ И АНГЛИЙСКИЕ БУКВЫ)
// ============================================================
string clean_text(const string& input) {
    string output;
    output.reserve(input.size());
    
    bool prev_space = false;
    for (size_t i = 0; i < input.size();) {
        unsigned char ch = input[i];
        
        // Английские буквы (A-Z, a-z)
        if ((ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z')) {
            output.push_back(ch);
            prev_space = false;
            i++;
        }
        // Русские буквы (UTF-8: 2 байта)
        else if ((ch >= 0xD0 && ch <= 0xD1) && (i + 1 < input.size())) {
            unsigned char ch2 = input[i + 1];
            if (ch2 >= 0x80 && ch2 <= 0xBF) {
                output.push_back(ch);
                output.push_back(ch2);
                prev_space = false;
                i += 2;
            } else {
                i++;
            }
        }
        // Цифры (0-9)
        else if (ch >= '0' && ch <= '9') {
            output.push_back(ch);
            prev_space = false;
            i++;
        }
        // Пробелы
        else if (ch == ' ' || ch == '\n' || ch == '\r' || ch == '\t') {
            if (!prev_space && !output.empty()) {
                output.push_back(' ');
                prev_space = true;
            }
            i++;
        }
        else {
            i++;
        }
    }
    
    while (!output.empty() && output.front() == ' ') output.erase(output.begin());
    while (!output.empty() && output.back() == ' ') output.pop_back();
    
    return output;
}

// ============================================================
// ТОКЕНИЗАЦИЯ (ПОДДЕРЖКА РУССКИХ БУКВ)
// ============================================================
vector<string> tokenize(const string& text) {
    vector<string> tokens;
    string word;
    
    for (size_t i = 0; i < text.size();) {
        unsigned char ch = text[i];
        
        // Английские буквы
        if ((ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z')) {
            word += tolower(ch);
            i++;
        }
        // Русские буквы
        else if ((ch >= 0xD0 && ch <= 0xD1) && (i + 1 < text.size())) {
            unsigned char ch2 = text[i + 1];
            if (ch2 >= 0x80 && ch2 <= 0xBF) {
                // Приводим русскую букву к нижнему регистру
                // Просто сохраняем как есть
                word += ch;
                word += ch2;
                i += 2;
            } else {
                i++;
            }
        }
        // Цифры
        else if (ch >= '0' && ch <= '9') {
            word += ch;
            i++;
        }
        else {
            if (!word.empty()) {
                tokens.push_back(word);
                word.clear();
            }
            i++;
        }
    }
    if (!word.empty()) {
        tokens.push_back(word);
    }
    
    return tokens;
}

// ============================================================
// ПРЕОБРАЗОВАНИЕ DOUBLE В СТРОКУ
// ============================================================
string double_to_string(double value) {
    ostringstream oss;
    oss.imbue(std::locale("C"));
    oss << value;
    string s = oss.str();
    for (char& c : s) {
        if (c == ',') c = '.';
    }
    return s;
}

// ============================================================
// ЗАГРУЗКА ДОКУМЕНТОВ
// ============================================================
vector<string> load_documents(const string& folder) {
    vector<string> texts;
    
    cout << "   📁 Проверка папки: " << folder << endl;
    
    if (!fs::exists(folder)) {
        cout << "   📁 Папка не найдена, создаем: " << folder << endl;
        fs::create_directory(folder);
        cout << "   ✅ Папка создана!" << endl;
        return texts;
    }
    
    cout << "   📁 Чтение папки..." << endl;
    
    for (const auto& entry : fs::directory_iterator(folder)) {
        if (entry.is_regular_file() && entry.path().extension() == ".txt") {
            ifstream file(entry.path(), ios::binary);
            if (file.is_open()) {
                string content((istreambuf_iterator<char>(file)),
                               istreambuf_iterator<char>());
                if (!content.empty()) {
                    string cleaned = clean_text(content);
                    if (!cleaned.empty()) {
                        texts.push_back(cleaned);
                        cout << "   ✅ Загружен: " << entry.path().filename() 
                             << " (" << cleaned.size() << " символов)" << endl;
                    }
                }
                file.close();
            }
        }
    }
    
    cout << "   📊 Загружено: " << texts.size() << " документов" << endl;
    return texts;
}

// ============================================================
// ПОСТРОЕНИЕ СЛОВАРЯ
// ============================================================
map<string, int> build_vocabulary(const vector<string>& docs) {
    map<string, int> vocab;
    set<string> seen_words;
    
    for (const auto& text : docs) {
        vector<string> tokens = tokenize(text);
        for (const string& word : tokens) {
            // Пропускаем слишком короткие слова (1 буква)
            if (word.size() < 2) {
                continue;
            }
            
            // Пропускаем слова, состоящие только из цифр
            bool only_digits = true;
            for (char ch : word) {
                if (!isdigit(ch)) {
                    only_digits = false;
                    break;
                }
            }
            if (only_digits) {
                continue;
            }
            
            if (seen_words.find(word) == seen_words.end()) {
                seen_words.insert(word);
                vocab[word] = vocab.size();
            }
        }
    }
    
    return vocab;
}

// ============================================================
// ВЫЧИСЛЕНИЕ TF-IDF
// ============================================================
vector<vector<double>> compute_tfidf(const vector<string>& docs,
                                     const map<string, int>& vocab) {
    int n_docs = docs.size();
    int n_words = vocab.size();
    vector<vector<double>> tfidf(n_docs, vector<double>(n_words, 0.0));
    
    vector<map<string, int>> word_counts(n_docs);
    for (int i = 0; i < n_docs; i++) {
        vector<string> tokens = tokenize(docs[i]);
        for (const string& word : tokens) {
            if (vocab.find(word) != vocab.end()) {
                word_counts[i][word]++;
            }
        }
    }
    
    map<string, int> df;
    for (const auto& [word, _] : vocab) {
        df[word] = 0;
        for (int i = 0; i < n_docs; i++) {
            if (word_counts[i].find(word) != word_counts[i].end()) {
                df[word]++;
            }
        }
    }
    
    for (int i = 0; i < n_docs; i++) {
        int total_words = 0;
        for (const auto& [word, count] : word_counts[i]) {
            total_words += count;
        }
        
        if (total_words == 0) continue;
        
        for (const auto& [word, count] : word_counts[i]) {
            if (vocab.find(word) != vocab.end()) {
                int idx = vocab.at(word);
                double tf = (double)count / total_words;
                double idf = log((double)n_docs / (df[word] + 1));
                tfidf[i][idx] = tf * idf;
            }
        }
    }
    
    return tfidf;
}

// ============================================================
// СОХРАНЕНИЕ В JSON
// ============================================================
void save_to_json(const vector<string>& docs,
                  const vector<vector<double>>& tfidf,
                  const map<string, int>& vocab,
                  const string& filename) {
    
    cout << "   📝 Создание JSON..." << endl;
    
    ofstream file(filename, ios::binary);
    if (!file.is_open()) {
        cerr << "   ❌ Не удалось открыть файл" << endl;
        return;
    }
    
    file << "{\n";
    file << "  \"documents\": [\n";
    
    for (size_t i = 0; i < docs.size(); ++i) {
        file << "    {\n";
        file << "      \"id\": " << i << ",\n";
        
        string text = clean_text(docs[i]);
        string short_text = text;
        if (short_text.size() > 300) {
            short_text = short_text.substr(0, 300) + "...";
        }
        
        file << "      \"text\": \"" << short_text << "\",\n";
        file << "      \"full_text\": \"" << text << "\",\n";
        
        file << "      \"vector\": [";
        for (size_t j = 0; j < tfidf[i].size(); ++j) {
            if (tfidf[i][j] == 0) {
                file << "0";
            } else {
                file << double_to_string(tfidf[i][j]);
            }
            if (j + 1 < tfidf[i].size()) file << ", ";
        }
        file << "]\n";
        
        file << "    }";
        if (i + 1 < docs.size()) file << ",";
        file << "\n";
        
        if ((i + 1) % 10 == 0) {
            cout << "   📄 Обработано " << (i + 1) << " документов..." << endl;
        }
    }
    
    file << "  ],\n";
    
    cout << "   📚 Сохранение словаря..." << endl;
    file << "  \"vocabulary\": {\n";
    
    vector<pair<string, int>> vocab_items(vocab.begin(), vocab.end());
    
    for (size_t i = 0; i < vocab_items.size(); ++i) {
        const auto& [word, idx] = vocab_items[i];
        if (!word.empty()) {
            file << "    \"" << word << "\": " << idx;
            if (i + 1 < vocab_items.size()) {
                file << ",";
            }
            file << "\n";
        }
    }
    
    file << "  },\n";
    
    file << "  \"metadata\": {\n";
    file << "    \"total_documents\": " << docs.size() << ",\n";
    file << "    \"vocabulary_size\": " << vocab.size() << ",\n";
    file << "    \"creation_date\": \"2026-09-07\",\n";
    file << "    \"source_folder\": \"./wikipedia_docs\"\n";
    file << "  }\n";
    file << "}\n";
    
    file.close();
    cout << "   ✅ JSON сохранен в " << filename << endl;
    cout << "   📊 Словарь: " << vocab.size() << " уникальных слов" << endl;
}

// ============================================================
// ГЛАВНАЯ
// ============================================================
int main() {
    setlocale(LC_ALL, "Russian");
    cout << "========================================" << endl;
    cout << "   TXT → JSON КОНВЕРТЕР (TF-IDF)" << endl;
    cout << "========================================" << endl;
    
    cout << "\n🔍 ТЕКУЩАЯ ДИРЕКТОРИЯ:" << endl;
    cout << "   " << fs::current_path() << endl;
    
    string folder = "./wikipedia_docs";
    cout << "\n📂 Загрузка документов..." << endl;
    vector<string> documents = load_documents(folder);
    
    if (documents.empty()) {
        cerr << "\n❌ Нет документов для обработки!" << endl;
        return 1;
    }
    
    cout << "   📊 Загружено: " << documents.size() << " документов" << endl;
    
    cout << "\n📚 Построение словаря..." << endl;
    map<string, int> vocabulary = build_vocabulary(documents);
    cout << "   📊 Словарь: " << vocabulary.size() << " слов" << endl;
    
    cout << "\n🧮 Вычисление TF-IDF..." << endl;
    vector<vector<double>> tfidf = compute_tfidf(documents, vocabulary);
    cout << "   📊 Матрица: " << tfidf.size() << "x" << tfidf[0].size() << endl;
    
    cout << "\n💾 Сохранение JSON..." << endl;
    save_to_json(documents, tfidf, vocabulary, "vectors.json");
    
    cout << "\n✅ Готово!" << endl;
    cout << "========================================" << endl;
    
    return 0;
}
//для запуска g++ -std=c++17 -I include tfidf.cpp -o tfidf.exe и ./tfidf.exe