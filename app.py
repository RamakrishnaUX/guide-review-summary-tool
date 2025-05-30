import streamlit as st
import pandas as pd
import re
from difflib import SequenceMatcher

st.title("Guide Review Summary Tool")
st.markdown("Upload a CSV of tour reviews, and get a summary of guide mentions, review counts, and highlights.")

# Sidebar controls
threshold = st.sidebar.slider("Spelling match threshold", 0.5, 1.0, 0.8, step=0.05)
min_words = st.sidebar.number_input("Minimum words per review", min_value=1, max_value=20, value=5)

# File uploader
uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
if not uploaded_file:
    st.info("Please upload a CSV file to get started.")
    st.stop()

# Read CSV
try:
    df = pd.read_csv(uploaded_file)
except Exception:
    st.error("Failed to read CSV. Make sure it's a valid comma-separated file.")
    st.stop()

# 1. Identify review column
rev_col = next((c for c in df.columns if 'review' in c.lower()), df.columns[0])

# 2. Filter substantive reviews
df['text'] = df[rev_col].astype(str)
df_sub = df[df['text'].apply(lambda x: len(x.split()) > min_words)].copy()

# 3. Extract guide names via regex
def extract_name(text):
    patterns = [
        r'guide[s]?[,:\s]*([A-Z][a-z]+)',
        r'([A-Z][a-z]+)\s+our guide',
        r'guide\s+was\s+([A-Z][a-z]+)',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None

df_sub['guide'] = df_sub['text'].apply(extract_name)
df_sub = df_sub[df_sub['guide'].notna()].copy()

# 4. Fuzzy-cluster spelling variants
counts = df_sub['guide'].value_counts().to_dict()
clusters = []
labels = {}
for name in sorted(counts):
    placed = False
    for cluster in clusters:
        if SequenceMatcher(None, name.lower(), cluster[0].lower()).ratio() >= threshold:
            cluster.append(name)
            placed = True
            break
    if not placed:
        clusters.append([name])
for cluster in clusters:
    canonical = max(cluster, key=lambda n: counts[n])
    for n in cluster:
        labels[n] = canonical

df_sub['canonical'] = df_sub['guide'].map(labels)

# 5. Aggregate reviews & counts
grouped = df_sub.groupby('canonical').agg(
    review_count=('text', 'size'),
    reviews=('text', lambda x: list(x))
).reset_index()

# 6. Generate highlights
adjectives = [
    'knowledgeable','friendly','helpful','terrific','phenomenal',
    'amazing','excellent','great','smooth','informative','engaging'
]
def summarize_highlights(rev_list):
    text = ' '.join(rev_list).lower()
    found = [a for a in adjectives if a in text]
    if found:
        if len(found) > 1:
            return "Known for being " + ", ".join(found[:-1]) + ", and " + found[-1] + "."
        return "Known for being " + found[0] + "."
    return rev_list[0].split('.')[0] + "."

grouped['highlights'] = grouped['reviews'].apply(summarize_highlights)

# 7. Display results
st.subheader("Guide Review Summary")
st.dataframe(grouped)
