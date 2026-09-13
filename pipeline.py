import feedparser
import pandas as pd
import sqlite3
import os
import json
from google import genai
from google.genai import types
from thefuzz import fuzz
from dotenv import load_dotenv
from database import DB_NAME, save_articles, save_brief

load_dotenv()

# Initialisation du nouveau client Gemini
api_key = os.getenv("GEMINI_API_KEY")

RSS_FEEDS = {
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "CNBC": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
}

def fetch_rss():
    articles = []
    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.get("published", ""),
                "source": source
            })
    return articles

def clean_and_cluster():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM raw_articles ORDER BY id DESC LIMIT 100", conn)
    conn.close()

    if df.empty:
        return []

    df['clean_title'] = df['title'].str.lower().str.replace(r'[^\w\s]', '', regex=True)
    df = df.drop_duplicates(subset=['clean_title'])

    clusters = []
    processed = set()
    
    for i, row1 in df.iterrows():
        if i in processed:
            continue
        current_cluster = [row1['title']]
        processed.add(i)
        
        for j, row2 in df.iterrows():
            if j not in processed:
                score = fuzz.ratio(row1['clean_title'], row2['clean_title'])
                if score > 75:
                    current_cluster.append(row2['title'])
                    processed.add(j)
        clusters.append(current_cluster)
    
    clusters.sort(key=len, reverse=True)
    return clusters[:5]

def generate_market_brief(clusters):
    if not clusters:
        return None
        
    if not api_key:
        print("❌ ERREUR CRITIQUE : Clé API introuvable. Vérifie ton fichier .env")
        return None

    client = genai.Client(api_key=api_key)

    prompt = f"""
    Tu es un Analyste Financier Senior et un Expert en Ingénierie de Données.
    Voici les principaux clusters de gros titres actuels extraits en temps réel de flux RSS :
    {json.dumps(clusters, indent=2)}
    
    Génère un résumé structuré au format JSON en respectant scrupuleusement cette structure :
    
    {{
        "what_is_moving": "Analyse de 3 à 4 phrases expliquant précisément quels secteurs ou indices bougent.",
        "why_it_matters": "Un paragraphe approfondi expliquant les conséquences macro-économiques.",
        "what_to_watch_next": "Explication détaillée des prochains indicateurs à surveiller.",
        "primary_signal": {{
            "analysis": "Une note de marché complète et détaillée (au moins 3 paragraphes). Nomme les entreprises, décris la dynamique et le contexte économique.",
            "sentiment": "Doit être exactement un de ces trois mots : positif, neutre, negatif"
        }},
        "secondary_signals": [
            {{
                "analysis": "Un paragraphe détaillé expliquant le premier signal secondaire et les entreprises impliquées.",
                "sentiment": "Doit être exactement un de ces trois mots : positif, neutre, negatif"
            }},
            {{
                "analysis": "Un paragraphe détaillé expliquant le second signal secondaire.",
                "sentiment": "Doit être exactement un de ces trois mots : positif, neutre, negatif"
            }}
        ],
        "profiles": {{
            "trader": "Stratégie détaillée pour un trader actif (volatilité, risque).",
            "investor": "Analyse fondamentale pour un investisseur long-terme.",
            "recruiter": "Argumentaire expliquant comment ce pipeline de données prouve les compétences techniques du candidat."
        }}
    }}
    
    Ne renvoie strictement RIEN d'autre que le JSON valide.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash', # <-- MISE À JOUR ICI
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return response.text
    except Exception as e:
        print("Erreur Gemini:", e)
        return None
    
def run_pipeline():
    print("1. Extraction RSS...")
    articles = fetch_rss()
    save_articles(articles)
    
    print("2. Nettoyage et Clustering...")
    top_clusters = clean_and_cluster()
    
    print("3. Analyse par Gemini...")
    brief_json = generate_market_brief(top_clusters)
    
    if brief_json:
        save_brief(brief_json)
        print("✅ Pipeline terminé. Brief sauvegardé.")

if __name__ == "__main__":
    run_pipeline()