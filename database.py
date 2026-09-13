import sqlite3
import pandas as pd

DB_NAME = "marketpulse.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Table des articles bruts
    c.execute('''
        CREATE TABLE IF NOT EXISTS raw_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            link TEXT,
            published TEXT,
            source TEXT
        )
    ''')
    # Table du brief généré
    c.execute('''
        CREATE TABLE IF NOT EXISTS market_brief (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            json_content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_articles(articles):
    if not articles:
        return
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Transformation de la liste de dictionnaires en liste de tuples pour SQLite
    data = [(a['title'], a['link'], a['published'], a['source']) for a in articles]
    
    # INSERT OR IGNORE permet d'insérer les nouveaux et d'ignorer les doublons sans planter
    c.executemany('''
        INSERT OR IGNORE INTO raw_articles (title, link, published, source)
        VALUES (?, ?, ?, ?)
    ''', data)
    
    conn.commit()
    conn.close()

def save_brief(json_str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO market_brief (json_content) VALUES (?)", (json_str,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de données initialisée.")