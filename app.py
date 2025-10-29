
import streamlit as st
import pandas as pd
import html
import os

st.set_page_config(page_title="SwarmAgent — Demo", layout="wide")

# ---------- Global CSS (modern, readable) ----------
CSS = """
<style>
:root {
  --bg: #0f172a0a;
  --card-bg: #ffffff;
  --text: #0f172a;
  --muted: #475569;
  --border: #e2e8f0;
  --shadow: 0 6px 18px rgba(2, 6, 23, 0.06);
  --radius: 14px;
}
html, body, [class*="css"]  {
  font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
}
.block-container { max-width: 1100px !important; }
h1, h2, h3 { letter-spacing: -0.2px; }
.small { color: var(--muted); font-size: 0.9rem; }
.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px 18px;
  margin-bottom: 16px;
}
.card h3 {
  margin: 0 0 8px 0;
  font-size: 1.05rem;
}
.hr { height: 1px; background: var(--border); margin: 12px 0; }
.badges { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 8px; border-radius: 1000px; border: 1px solid var(--border);
  font-size: 0.82rem; color: var(--muted); background: #f8fafc;
}
.badge.type-conflict { border-color: #fecaca; background: #fff1f2; color: #7f1d1d; }
.badge.type-duplicate { border-color: #fde68a; background: #fffbeb; color: #7c2d12; }
.badge.type-synergy { border-color: #bbf7d0; background: #f0fdf4; color: #14532d; }
.badge.urgency-HIGH { border-color: #fecaca; background: #fff1f2; color: #7f1d1d; }
.badge.urgency-MEDIUM { border-color: #fde68a; background: #fffbeb; color: #7c2d12; }
.badge.urgency-LOW { border-color: #bfdbfe; background: #eff6ff; color: #1e3a8a; }
.section { margin-top: 6px; }
.section h4 { margin: 0 0 6px 0; font-size: 0.95rem; color: var(--muted); }
.section p, .section li { line-height: 1.55; font-size: 0.98rem; color: var(--text); }
.buttons { display: flex; gap: 8px; flex-wrap: wrap; }
.copyblock {
  white-space: pre-wrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  background: #0f172a08; border: 1px dashed var(--border); border-radius: var(--radius);
  padding: 10px 12px; color: #0f172a;
}
.kpi { color: #0e7490; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------- Load data ----------
@st.cache_data
def load_data(tasks_path: str, cards_path: str, scenario_path: str):
    tasks = pd.read_csv(tasks_path) if os.path.exists(tasks_path) else None
    cards = pd.read_csv(cards_path) if os.path.exists(cards_path) else None
    scenario = pd.read_csv(scenario_path) if os.path.exists(scenario_path) else None
    if cards is not None:
        cards["cross_product"] = cards["a_prod"] != cards["b_prod"]
        cards["signals_count"] = cards["signals"].fillna("").apply(lambda s: len([x for x in s.split(", ") if x]))
    return tasks, cards, scenario

DATA_DIR = "data"
TASKS_CSV = os.path.join(DATA_DIR, "tasks.csv")
CARDS_CSV = os.path.join(DATA_DIR, "cards.csv")
SCENARIO_CSV = os.path.join(DATA_DIR, "scenario_cards.csv")

tasks, cards, scenario = load_data(TASKS_CSV, CARDS_CSV, SCENARIO_CSV)

# ---------- Sidebar ----------
st.sidebar.header("Режим показа")
demo_mode = st.sidebar.checkbox("Demo mode (для руководителей)", value=True)
use_scenario = st.sidebar.checkbox("Сценарные карточки", value=True if scenario is not None else False, disabled=(scenario is None))

st.sidebar.header("Фильтры")
type_opts = sorted(cards["type"].unique()) if cards is not None else []
type_filter = st.sidebar.multiselect("Тип карточки", options=type_opts, default=type_opts)
only_cross = st.sidebar.checkbox("Только кросс‑продукт", value=False)
search_q = st.sidebar.text_input("Поиск", "")

# ---------- Helpers ----------
def filter_scenario(df):
    g = df.copy()
    if search_q:
        s = search_q.lower()
        g = g[g.apply(lambda r: s in str(r["title"]).lower() or s in str(r["plain_text"]).lower(), axis=1)]
    return g

def filter_cards(df):
    g = df[df["type"].isin(type_filter)].copy()
    if only_cross:
        g = g[g["a_prod"]!=g["b_prod"]]
    if search_q:
        s = search_q.lower()
        g = g[g.apply(lambda r: s in str(r["a_id"]).lower() or s in str(r["b_id"]).lower() or s in str(r.get("signals","")).lower(), axis=1)]
    return g

def render_badges(t, u, src):
    badges = []
    badges.append(f'<span class="badge type-{t}">{"⚠️" if t=="conflict" else ("🔁" if t=="duplicate" else "🤝")} {t.upper()}</span>')
    if u:
        badges.append(f'<span class="badge urgency-{u}">{u} • срочность</span>')
    if src:
        badges.append(f'<span class="badge">источники: {html.escape(src)}</span>')
    return '<div class="badges">' + "".join(badges) + '</div>'

def render_section(title, html_body):
    return f'<div class="section"><h4>{html.escape(title)}</h4>{html_body}</div>'

def render_list(items):
    safe = "".join([f"<li>{html.escape(x)}</li>" for x in items if x])
    return f"<ul>{safe}</ul>"

def render_paragraph(text):
    return f"<p>{html.escape(text)}</p>"

def render_card(row):
    title = html.escape(row.get("title",""))
    t = row.get("type","")
    u = row.get("urgency","")
    src = row.get("source","")
    why = [row.get("why_1",""), row.get("why_2",""), row.get("why_3","")]
    steps = [row.get("step_1",""), row.get("step_2",""), row.get("step_3","")]
    scenario = row.get("scenario","")
    user_story = row.get("user_story","")
    impact = row.get("impact","")

    top = f'<div class="card"><h3>{title}</h3>{render_badges(t,u,src)}'
    body = ""
    if scenario:
        body += render_section("Сценарий", render_paragraph(scenario))
    if user_story:
        body += render_section("Для пользователя", render_paragraph(user_story))
    body += render_section("Почему", render_list(why))
    if impact:
        body += render_section("Эффект", render_paragraph(impact))
    if any(steps):
        body += render_section("Что делаем", render_list(steps))
    bottom = "</div>"
    return top + body + bottom

# ---------- Layout ----------
st.title("SwarmAgent — функциональные пересечения")
st.caption("Читаемые карточки: без жаргона, с «почему», эффектом и шагами.")

if demo_mode and use_scenario and scenario is not None:
    st.subheader("Сценарные карточки")
    scen = filter_scenario(scenario)
    # Grid: 2 columns
    cols = st.columns(2, gap="large")
    for i, (_, row) in enumerate(scen.iterrows()):
        with cols[i % 2]:
            st.markdown(render_card(row), unsafe_allow_html=True)
            with st.expander("Скопировать текст"):
                st.code(row["plain_text"])

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

st.subheader("Рабочий инбокс (свёрнутые детали)")
if cards is None:
    st.info("Нет cards.csv")
else:
    fc = filter_cards(cards)
    st.write(f"Найдено карточек: **{len(fc)}**")
    for _, r in fc.head(60).iterrows():
        title = f"[{r['type'].upper()}] {r['a_id']} ⟷ {r['b_id']}"
        with st.expander(title):
            # map to scenario if exists
            scen_text = None
            if scenario is not None and "match_id" in r:
                m = scenario[scenario["match_id"]==str(r.get("match_id",""))]
                if len(m)>0:
                    st.markdown(render_card(m.iloc[0]), unsafe_allow_html=True)
                    scen_text = m.iloc[0]["plain_text"]
            if not scen_text:
                st.write("Сценарная версия отсутствует. Используйте раздел выше или обновите scenario_cards.csv.")
            # tech
            with st.expander("Технические детали", expanded=False):
                if tasks is not None:
                    t = tasks.set_index("task_id")
                    if r["a_id"] in t.index: st.json(t.loc[r["a_id"]].to_dict())
                    if r["b_id"] in t.index: st.json(t.loc[r["b_id"]].to_dict())

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
