import streamlit as st
import sqlite3
import pandas as pd
import json
from database import DB_NAME

st.set_page_config(page_title="MarketPulse", layout="wide")

def load_latest_brief():
    conn = sqlite3.connect(DB_NAME)
    try:
        c = conn.cursor()
        c.execute("SELECT json_content, timestamp FROM market_brief ORDER BY timestamp DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row[0]), row[1]
    except Exception as e:
        print("Erreur de chargement du brief:", e)
        pass
    return None, None

def load_raw_stats():
    conn = sqlite3.connect(DB_NAME)
    count = pd.read_sql_query("SELECT COUNT(*) as count FROM raw_articles", conn).iloc[0]['count']
    recent = pd.read_sql_query("SELECT title, source FROM raw_articles ORDER BY id DESC LIMIT 10", conn)
    conn.close()
    return count, recent

def display_sentiment_alert(sentiment_text):
    sentiment = str(sentiment_text).strip().lower()
    if "positif" in sentiment:
        st.success("🟢 **Sentiment dominant : Positif** (Marché haussier ou signaux rassurants)")
    elif "negatif" in sentiment or "négatif" in sentiment:
        st.error("🔴 **Sentiment dominant : Négatif** (Marché baissier, craintes ou risques élevés)")
    else:
        st.warning("🟡 **Sentiment dominant : Neutre / Mixte** (Attentisme ou signaux contradictoires)")

# --- UI Layout ---
st.title("📈 MarketPulse")
st.subheader("Live Financial News Interpretation Engine")

brief, timestamp = load_latest_brief()
total_articles, recent_df = load_raw_stats()

if brief:
    st.caption(f"Dernière mise à jour (via le pipeline Python) : {timestamp}")
    
    st.markdown("### 1. Brief du jour")
    col1, col2, col3 = st.columns(3)
    col1.info(f"**Ce qui bouge :**\n\n{brief.get('what_is_moving', '')}")
    col2.warning(f"**Pourquoi c'est important :**\n\n{brief.get('why_it_matters', '')}")
    col3.success(f"**A surveiller :**\n\n{brief.get('what_to_watch_next', '')}")
    
    st.divider()
    
    st.markdown("### 2. Note de marché (Signal Principal)")
    # Gestion du nouveau format avec dictionnaire (analysis + sentiment)
    primary_data = brief.get('primary_signal', {})
    if isinstance(primary_data, dict):
        display_sentiment_alert(primary_data.get('sentiment', 'neutre'))
        st.write(primary_data.get('analysis', ''))
    else:
        # Rétrocompatibilité si un vieux brief est chargé
        st.write(primary_data) 
    
    st.divider()
    
    st.markdown("### 3. Signaux Secondaires")
    secondary_signals = brief.get('secondary_signals', [])
    
    # Gestion du nouveau format en liste de dictionnaires
    if secondary_signals and isinstance(secondary_signals[0], dict):
        for i, sig in enumerate(secondary_signals):
            st.markdown(f"**Signal {i+1}**")
            display_sentiment_alert(sig.get('sentiment', 'neutre'))
            st.write(sig.get('analysis', ''))
            st.write("---")
    else:
        # Rétrocompatibilité
        for sig in secondary_signals:
            st.write(f"- {sig}")
            
    st.divider()
    
    st.markdown("### 4. Interprétation par profil")
    tab1, tab2, tab3 = st.tabs(["📊 Trader", "🏦 Investisseur Long-terme", "🚀 Recruteur Tech"])
    with tab1:
        st.write(brief['profiles'].get('trader', ''))
    with tab2:
        st.write(brief['profiles'].get('investor', ''))
    with tab3:
        st.write(brief['profiles'].get('recruiter', ''))
        
    st.divider()
    
    st.markdown("### 5. Couche de vérification & Pipeline")
    with st.expander("Voir la mécanique sous-jacente (Proof section)"):
        st.metric(label="Articles ingérés et analysés (Total historique)", value=total_articles)
        st.write("Flux RSS → SQLite → Nettoyage (Regex/Pandas) → Déduplication floue (TheFuzz) → Analyse sémantique par Gemini")
        st.write("**Échantillon des derniers articles captés (Preuve de vie du flux) :**")
        st.dataframe(recent_df, use_container_width=True)
else:
    st.warning("Aucun brief trouvé en base de données. Veuillez exécuter `python pipeline.py` pour générer le premier rapport depuis les flux RSS.")