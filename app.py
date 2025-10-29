
import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="SwarmAgent — Demo", layout="wide")

@st.cache_data
def load_data(tasks_path: str, cards_path: str, scenario_path: str):
    tasks = pd.read_csv(tasks_path)
    cards = pd.read_csv(cards_path)
    scenario = None
    if os.path.exists(scenario_path):
        scenario = pd.read_csv(scenario_path)
    cards["cross_product"] = cards["a_prod"] != cards["b_prod"]
    cards["signals_count"] = cards["signals"].fillna("").apply(lambda s: len([x for x in s.split(", ") if x]))
    return tasks, cards, scenario

DATA_DIR = "data"
TASKS_CSV = os.path.join(DATA_DIR, "tasks.csv")
CARDS_CSV = os.path.join(DATA_DIR, "cards.csv")
SCENARIO_CSV = os.path.join(DATA_DIR, "scenario_cards.csv")

# Writable actions path
ACTIONS_DIR = os.environ.get("ACTIONS_DIR", DATA_DIR)
try:
    os.makedirs(ACTIONS_DIR, exist_ok=True)
    test_path = os.path.join(ACTIONS_DIR, ".write_test")
    with open(test_path, "w") as _f: _f.write("ok")
    os.remove(test_path)
except Exception:
    ACTIONS_DIR = "/tmp"
ACTIONS_CSV = os.path.join(ACTIONS_DIR, "actions.csv")

tasks, cards, scenario = load_data(TASKS_CSV, CARDS_CSV, SCENARIO_CSV)

# ---------------- Sidebar ----------------
st.sidebar.header("Режим")
demo_mode = st.sidebar.checkbox("Demo mode (для руководителей)", value=True)
use_scenario = st.sidebar.checkbox("Сценарные карточки", value=True if scenario is not None else False, disabled=(scenario is None))
st.sidebar.header("Фильтры (для экспертов)")
type_filter = st.sidebar.multiselect("Тип карточки", options=sorted(cards["type"].unique()), default=list(sorted(cards["type"].unique())))
prod_filter = st.sidebar.multiselect("Продукты", options=sorted(pd.unique(tasks["product"])), default=list(sorted(pd.unique(tasks["product"]))))
only_cross = st.sidebar.checkbox("Только кросс-продукт", value=False)
min_score = st.sidebar.slider("Мин. score (synergy/duplicate)", 0, 100, 50, 5)
search_q = st.sidebar.text_input("Поиск", "")

# ---------------- Helpers ----------------
def priority(row):
    w_type = {"conflict":3, "duplicate":2, "synergy":1}.get(row["type"],0)
    w_signal = {
        "contract":2.0,"kpi_tension":2.0,"surface":1.5,"entity":1.2,
        "goal_overlap":1.5,"opposite_lever":1.5,"surface_contention":1.2,
        "capability_same":1.0,"capability_complement":1.0,"kpi_family":0.8
    }
    s = (row.get("signals") or "")
    total = w_type + sum(w_signal.get(sig.strip(), 0) for sig in s.split(", "))
    try:
        if row["type"] in ("synergy","duplicate"):
            total += (int(row.get("score") or 0))/100.0
    except Exception:
        pass
    return total

def filter_cards(df):
    g = df[df["type"].isin(type_filter)].copy()
    g = g[(g["a_prod"].isin(prod_filter)) | (g["b_prod"].isin(prod_filter))]
    if only_cross:
        g = g[g["a_prod"] != g["b_prod"]]
    def pass_score(row):
        if row["type"] in ["synergy","duplicate"]:
            try: return int(row["score"]) >= min_score
            except: return False
        return True
    g = g[g.apply(pass_score, axis=1)]
    if search_q:
        s = search_q.lower()
        # Search across task ids and signals
        g = g[g.apply(lambda r: s in str(r["a_id"]).lower() or s in str(r["b_id"]).lower() or s in str(r.get("signals","")).lower(), axis=1)]
    g["_prio"] = g.apply(priority, axis=1)
    return g.sort_values(by=["_prio"], ascending=False)

# ---------------- UI ----------------
st.title("SwarmAgent — функциональные пересечения без LLM")
st.caption("Карточки объясняют *почему* совпало: capability / экран / объект / контракт / KPI / цель.")

if demo_mode and use_scenario and scenario is not None:
    st.subheader("Executive Summary")
    # pick heroine cases by urgency and type
    scen_sorted = scenario.copy()
    urg_map = {"HIGH":3, "MEDIUM":2, "LOW":1}
    scen_sorted["_u"] = scen_sorted["urgency"].map(urg_map).fillna(1)
    # prefer 1 conflict (HIGH), 1 duplicate, 1 synergy
    hero_conf = scen_sorted[scen_sorted["type"]=="conflict"].sort_values(by=["_u"], ascending=False).head(1)
    hero_dup = scen_sorted[scen_sorted["type"]=="duplicate"].head(1)
    hero_syn = scen_sorted[scen_sorted["type"]=="synergy"].head(1)
    cols = st.columns(3)
    tiles = [("⚠️ Конфликт", hero_conf), ("🔁 Дубликат", hero_dup), ("🤝 Синергия", hero_syn)]
    for col, (label, dfh) in zip(cols, tiles):
        if dfh is not None and len(dfh)>0:
            row = dfh.iloc[0]
            col.metric(label, row["title"], help=row["scenario"])
    st.markdown("---")

    st.subheader("Сценарные карточки (готовые тексты для отправки)")
    # Filter by search in scenario title/text
    scen_view = scenario.copy()
    if search_q:
        s = search_q.lower()
        scen_view = scen_view[scen_view.apply(lambda r: s in str(r["title"]).lower() or s in str(r["plain_text"]).lower(), axis=1)]
    # Order: urgency then type
    scen_view["_u"] = scen_view["urgency"].map(urg_map).fillna(1)
    scen_view = scen_view.sort_values(by=["_u","type"], ascending=[False, True])
    for _, r in scen_view.iterrows():
        with st.expander(f"[{r['type'].upper()}][{r['urgency']}] {r['title']}  ·  Источники: {r['source']}"):
            st.write(r["plain_text"])
            # simple copy: show as code block to ease copy
            st.code(r["plain_text"])

st.subheader("Рабочий инбокс (для команд)")
fc = filter_cards(cards)
st.write(f"Найдено карточек: **{len(fc)}**")
for _, row in fc.head(60).iterrows():
    with st.expander(f"[{row['type'].upper()}] {row['a_id']} ⟷ {row['b_id']}  ·  signals: {row.get('signals','')}  ·  score: {row.get('score','-')}"):
        # Summary in plain language
        # Try to map to scenario card text if present
        scen_text = None
        if scenario is not None:
            m = scenario[scenario["match_id"]==str(row.get("match_id",""))]
            if len(m)>0:
                scen_text = m.iloc[0]["plain_text"]
        if scen_text:
            st.write(scen_text)
            st.code(scen_text)
        else:
            st.write("Карточка совпадения. Открой сценарные карточки выше для читабельного текста.")
        # Minimal tech context toggler
        with st.expander("Детали (тех.)", expanded=False):
            t = tasks.set_index("task_id")
            if row["a_id"] in t.index:
                st.json(t.loc[row["a_id"]].to_dict())
            if row["b_id"] in t.index:
                st.json(t.loc[row["b_id"]].to_dict())

# Sidebar upload
st.sidebar.markdown("---")
st.sidebar.header("Обновление данных")
u_tasks = st.sidebar.file_uploader("Загрузить tasks.csv", type=["csv"], key="u_tasks")
u_cards = st.sidebar.file_uploader("Загрузить cards.csv", type=["csv"], key="u_cards")
u_scenario = st.sidebar.file_uploader("Загрузить scenario_cards.csv", type=["csv"], key="u_scenario")
if st.sidebar.button("Применить загруженные CSV"):
    if u_tasks is not None: pd.read_csv(u_tasks).to_csv(TASKS_CSV, index=False)
    if u_cards is not None: pd.read_csv(u_cards).to_csv(CARDS_CSV, index=False)
    if u_scenario is not None: pd.read_csv(u_scenario).to_csv(SCENARIO_CSV, index=False)
    st.success("Данные обновлены. Обновите страницу.")
