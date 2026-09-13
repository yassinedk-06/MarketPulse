import streamlit as st
import sqlite3
import pandas as pd
import json
from database import DB_NAME, init_db
import pipeline

st.set_page_config(page_title="MarketPulse", layout="wide")

init_db()

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
        # Si Gemini a mal formaté le JSON, on l'affiche sur l'interface
        st.error(f"⚠️ Erreur critique lors de la lecture du JSON : {e}")
    return None, None

def load_raw_stats():
    conn = sqlite3.connect(DB_NAME)
    try:
        count = pd.read_sql_query("SELECT COUNT(*) as count FROM raw_articles", conn).iloc[0]['count']
        recent = pd.read_sql_query("SELECT title, source FROM raw_articles ORDER BY id DESC LIMIT 10", conn)
    except Exception:
        count = 0
        recent = pd.DataFrame(columns=['title', 'source'])
    conn.close()
    return count, recent

def display_sentiment_alert(sentiment_text):
    sentiment = str(sentiment_text).strip().lower()
    if "positif" in sentiment:
        st.success("🟢 **Sentiment dominant : Positif**")
    elif "negatif" in sentiment or "négatif" in sentiment:
        st.error("🔴 **Sentiment dominant : Négatif**")
    else:
        st.warning("🟡 **Sentiment dominant : Neutre / Mixte**")

# --- Barre latérale avec gestion des erreurs ---
with st.sidebar:
    st.header("⚙️ Contrôle du Pipeline")
    if st.button("🚀 Lancer l'analyse en direct"):
        try:
            with st.spinner("1/3 Extraction RSS..."):
                articles = pipeline.fetch_rss()
                pipeline.save_articles(articles)
            
            with st.spinner("2/3 Nettoyage et Clustering..."):
                top_clusters = pipeline.clean_and_cluster()
                
            if not top_clusters:
                st.error("❌ Le pipeline n'a trouvé aucun article. Les flux RSS sont peut-être inaccessibles.")
            else:
                with st.spinner("3/3 Analyse par Gemini IA..."):
                    brief_json = pipeline.generate_market_brief(top_clusters)
                
                if brief_json:
                    pipeline.save_brief(brief_json)
                    st.success("✅ Analyse terminée ! La page se met à jour.")
                    st.rerun()
                else:
                    st.error("❌ Gemini n'a rien renvoyé. Le problème vient de la clé API ou du modèle.")
        except Exception as e:
            st.error(f"❌ Crash du système : {e}")

# --- UI Layout ---
st.title("📈 MarketPulse")
st.subheader("Live Financial News Interpretation Engine")

brief, timestamp = load_latest_brief()
total_articles, recent_df = load_raw_stats()

if brief:
    st.caption(f"Dernière mise à jour : {timestamp}")
    st.markdown("### 1. Brief du jour")
    col1, col2, col3 = st.columns(3)
    col1.info(f"**Ce qui bouge :**\n\n{brief.get('what_is_moving', '')}")
    col2.warning(f"**Pourquoi c'est important :**\n\n{brief.get('why_it_matters', '')}")
    col3.success(f"**A surveiller :**\n\n{brief.get('what_to_watch_next', '')}")
    
    st.divider()
    
    st.markdown("### 2. Note de marché (Signal Principal)")
    primary_data = brief.get('primary_signal', {})
    if isinstance(primary_data, dict):
        display_sentiment_alert(primary_data.get('sentiment', 'neutre'))
        st.write(primary_data.get('analysis', ''))
    else:
        st.write(primary_data)
        
    st.divider()
    
    st.markdown("### 3. Signaux Secondaires")
    secondary_signals = brief.get('secondary_signals', [])
    if secondary_signals and isinstance(secondary_signals[0], dict):
        for i, sig in enumerate(secondary_signals):
            st.markdown(f"**Signal {i+1}**")
            display_sentiment_alert(sig.get('sentiment', 'neutre'))
            st.write(sig.get('analysis', ''))
            st.write("---")
            
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
    with st.expander("Voir la mécanique sous-jacente (Proof section)"):
        st.metric(label="Articles ingérés et analysés (Total historique)", value=total_articles)
        st.dataframe(recent_df, use_container_width=True)
else:
    st.warning("Aucune donnée en base. Utilisez le bouton dans le menu à gauche pour lancer la première analyse en direct via l'API Gemini !")
