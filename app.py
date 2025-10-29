
import streamlit as st
import pandas as pd
import html, os

st.set_page_config(page_title="SwarmAgent — Demo", layout="wide")

CSS = """
<style>
:root { --card-bg:#fff; --border:#e2e8f0; --muted:#475569; --shadow:0 6px 18px rgba(2,6,23,.06); --radius:14px; }
.block-container { max-width: 1100px !important; }
.card { background:var(--card-bg); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); padding:16px 18px; margin-bottom:16px; }
.card h3 { margin:0 0 8px 0; font-size:1.06rem;}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 6px 0}
.badge{display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:999px;border:1px solid var(--border);font-size:.82rem;color:var(--muted);background:#f8fafc}
.badge.type-conflict{border-color:#fecaca;background:#fff1f2;color:#7f1d1d}
.badge.type-duplicate{border-color:#fde68a;background:#fffbeb;color:#7c2d12}
.badge.type-synergy{border-color:#bbf7d0;background:#f0fdf4;color:#14532d}
.badge.cat{border-style:dashed}
.section{margin-top:6px}
.section h4{margin:0 0 6px 0;font-size:.95rem;color:var(--muted)}
.section p,.section li{line-height:1.55;font-size:.98rem}
.hr{height:1px;background:var(--border);margin:12px 0}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

@st.cache_data
def load_csv(path):
    return pd.read_csv(path) if os.path.exists(path) else None

DATA_DIR = "data"
SCENARIO_CSV = os.path.join(DATA_DIR, "scenario_cards.csv")
CARDS_CSV = os.path.join(DATA_DIR, "cards.csv")
TASKS_CSV = os.path.join(DATA_DIR, "tasks.csv")

scenario = load_csv(SCENARIO_CSV)
cards = load_csv(CARDS_CSV)
tasks = load_csv(TASKS_CSV)

st.sidebar.header("Режим")
demo = st.sidebar.checkbox("Demo mode", value=True)
st.sidebar.header("Фильтры")
types = sorted(scenario["type"].unique()) if scenario is not None else []
cats = sorted(scenario["category"].unique()) if scenario is not None else []
type_f = st.sidebar.multiselect("Тип", types, default=types)
cat_f = st.sidebar.multiselect("Категория", cats, default=cats)
q = st.sidebar.text_input("Поиск", "")

def section(title, body_html):
    return f'<div class="section"><h4>{html.escape(title)}</h4>{body_html}</div>'

def paragraph(text): return f"<p>{html.escape(text)}</p>"
def bullets(items): return "<ul>" + "".join([f"<li>{html.escape(x)}</li>" for x in items if x]) + "</ul>"

def render_card(row):
    t = row["type"]; cat = row.get("category","")
    badges = f'<div class="badges"><span class="badge type-{t}">{("⚠️" if t=="conflict" else ("🔁" if t=="duplicate" else "🤝"))} {t.upper()}</span><span class="badge cat">{html.escape(cat)}</span><span class="badge">источники: {html.escape(row.get("source",""))}</span></div>'
    body = ""
    body += section("Контекст продукта", paragraph(row.get("product_context","")))
    body += section("Цель и KPI", paragraph(row.get("objective_kpi","")))
    body += section("Почему", bullets([row.get("why_1",""),row.get("why_2",""),row.get("why_3","")]))
    if row.get("risks",""):
        body += section("Риски/гардрейлы", paragraph(row.get("risks","")))
    body += section("Что делаем", bullets([row.get("step_1",""),row.get("step_2",""),row.get("step_3","")]))
    html_card = f'<div class="card"><h3>{html.escape(row["title"])}</h3>{badges}{body}</div>'
    return html_card

st.title("SwarmAgent — продуктовые карточки")
st.caption("Показываем объяснимые пересечения: экран/объект/контракт/KPI. Без лишнего жаргона.")

if scenario is None:
    st.info("Загрузите scenario_cards.csv в папку data/.")
else:
    view = scenario.copy()
    view = view[view["type"].isin(type_f)]
    view = view[view["category"].isin(cat_f)]
    if q:
        s = q.lower()
        view = view[view.apply(lambda r: s in str(r["title"]).lower() or s in str(r["plain_text"]).lower() or s in str(r["category"]).lower(), axis=1)]
    st.write(f"Карточек: **{len(view)}**")
    cols = st.columns(2, gap="large")
    for i, (_, r) in enumerate(view.iterrows()):
        with cols[i%2]:
            st.markdown(render_card(r), unsafe_allow_html=True)
            with st.expander("Скопировать текст"):
                st.code(r["plain_text"])

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
st.subheader("Инбокс для команд (тех.)")
if cards is not None:
    st.write(f"Всего карточек: **{len(cards)}**")
else:
    st.info("Нет cards.csv")
