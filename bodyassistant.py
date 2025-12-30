# app.py
import json
from pathlib import Path
from dataclasses import dataclass

import pandas as pd
import streamlit as st

# ============================================================
# Config
# ============================================================
st.set_page_config(page_title="Calorie tracker - Vitor & Thayná", layout="wide")

# Tema claro via CSS (reforço; recomendável também usar .streamlit/config.toml com base="light")
st.markdown(
    """
    <style>
      .stApp { background: #ffffff; color: #111827; }
      [data-testid="stAppViewContainer"] { background: #ffffff; }
      [data-testid="stHeader"] { background: rgba(255,255,255,0.90); }
      h1,h2,h3,h4 { color: #111827; }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# Constantes
# ============================================================
DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
DAY_ORDER = {d: i for i, d in enumerate(DAYS)}
MEALS = ["Whey pós-treino", "Almoço", "Lanche", "Jantar", "Ceia"]

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ============================================================
# Perfis
# ============================================================
@dataclass
class Profile:
    name: str
    age: int
    weight_kg: float
    sex: str  # "M" / "F"
    daily_limit_kcal: int
    default_height_cm: int
    default_activity_factor: float

PROFILES = {
    "Vitor": Profile(
        name="Vitor",
        age=35,
        weight_kg=97.0,
        sex="M",
        daily_limit_kcal=1500,
        default_height_cm=180,
        default_activity_factor=1.55,  # moderado
    ),
    "Thayná": Profile(
        name="Thayná",
        age=32,
        weight_kg=63.0,
        sex="F",
        daily_limit_kcal=1300,
        default_height_cm=169,
        default_activity_factor=1.55,  # moderado
    ),
}

# ============================================================
# Cálculos (exercício)
# ============================================================
def kcal_from_met(weight_kg: float, minutes: float, met: float) -> float:
    minutes = max(0.0, float(minutes))
    met = max(0.0, float(met))
    return met * 3.5 * float(weight_kg) / 200.0 * minutes

def running_met_from_speed_kmh(speed_kmh: float) -> float:
    v = max(0.0, float(speed_kmh))
    if v <= 0.1:
        return 0.0
    if v < 5.0:
        return 3.5   # caminhada
    if v < 6.5:
        return 5.0   # caminhada rápida / trote
    if v < 8.0:
        return 7.0   # trote / corrida leve
    if v < 10.0:
        return 9.8   # corrida moderada
    if v < 12.0:
        return 11.5  # forte
    return 12.8      # muito forte

def calc_running_kcal(weight_kg: float, distance_km: float, minutes: float):
    minutes = max(0.0, float(minutes))
    distance_km = max(0.0, float(distance_km))
    if minutes <= 0.0 or distance_km <= 0.0:
        return 0.0, 0.0, 0.0
    hours = minutes / 60.0
    speed = distance_km / hours
    met = running_met_from_speed_kmh(speed)
    kcal = kcal_from_met(weight_kg, minutes, met)
    return kcal, speed, met

# ============================================================
# Cálculos (metabolismo)
# ============================================================
def bmr_mifflin_st_jeor(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """
    BMR (kcal/dia) - Mifflin-St Jeor
    """
    w = float(weight_kg)
    h = float(height_cm)
    a = float(age)
    if str(sex).upper() == "M":
        return 10*w + 6.25*h - 5*a + 5
    return 10*w + 6.25*h - 5*a - 161

def tdee_kcal_day(bmr: float, activity_factor: float) -> float:
    """
    TDEE sem exercício estruturado (kcal/dia)
    """
    return float(bmr) * float(activity_factor)

# ============================================================
# Plano alimentar sugerido (fechando por dia no limite)
# ============================================================
def meal_plan_template(profile_name: str) -> dict:
    if profile_name == "Vitor":
        plan = {
            "Seg": {
                "Whey pós-treino": ("Whey + leite (250ml) + café (sem açúcar)", 250),
                "Almoço": ("Frango (180g) + salada (alface/rúcula/tomate) + abobrinha + arroz parboilizado (1/2 xíc)", 600),
                "Lanche": ("Banana", 150),
                "Jantar": ("Omelete (3 ovos) + salada grande + berinjela", 400),
                "Ceia": ("Café com leite (sem açúcar)", 100),
            },
            "Ter": {
                "Whey pós-treino": ("Whey + leite (250ml) + café (sem açúcar)", 250),
                "Almoço": ("Frango (180g) + abóbora assada + salada + batata pequena", 600),
                "Lanche": ("Mamão (300g)", 150),
                "Jantar": ("Frango (150g) + salada + abobrinha", 400),
                "Ceia": ("1 fruta (tangerina/pera pequena)", 100),
            },
            "Qua": {  # carne vermelha
                "Whey pós-treino": ("Whey + leite (250ml) + café (sem açúcar)", 250),
                "Almoço": ("Carne vermelha magra (150g) + salada + berinjela + arroz (1/3–1/2 xíc)", 650),
                "Lanche": ("Uva (200g)", 150),
                "Jantar": ("Creme de abóbora + frango desfiado (120g) + salada", 350),
                "Ceia": ("Café com leite (sem açúcar)", 100),
            },
            "Qui": {
                "Whey pós-treino": ("Whey + leite (250ml) + café (sem açúcar)", 250),
                "Almoço": ("Frango (180g) + salada + abobrinha + batata média", 600),
                "Lanche": ("Morango (250g)", 120),
                "Jantar": ("Atum (1 lata) + 2 ovos + salada", 430),
                "Ceia": ("Café com leite (sem açúcar)", 100),
            },
            "Sex": {  # carne vermelha
                "Whey pós-treino": ("Whey + leite (250ml) + café (sem açúcar)", 250),
                "Almoço": ("Frango (180g) + salada + abóbora + arroz (1/2 xíc)", 600),
                "Lanche": ("Goiaba", 150),
                "Jantar": ("Carne vermelha magra (130g) + salada + abobrinha", 400),
                "Ceia": ("Café com leite (sem açúcar)", 100),
            },
            "Sáb": {  # refeição livre no almoço
                "Whey pós-treino": ("Whey + leite (250ml) + café (sem açúcar)", 250),
                "Almoço": ("REFEIÇÃO LIVRE (almoço)", 700),
                "Lanche": ("Fruta leve (morangos ou tangerina)", 100),
                "Jantar": ("Salada grande + frango (150g) (bem limpo)", 350),
                "Ceia": ("Café com leite (sem açúcar)", 100),
            },
            "Dom": {
                "Whey pós-treino": ("Whey + leite (250ml) + café (sem açúcar)", 250),
                "Almoço": ("Frango (180g) + salada + legumes + arroz (1/2 xíc)", 600),
                "Lanche": ("Pera", 150),
                "Jantar": ("Omelete (3 ovos) + salada + abobrinha", 400),
                "Ceia": ("Café com leite (sem açúcar)", 100),
            },
        }
    else:
        plan = {
            "Seg": {
                "Whey pós-treino": ("Whey + leite (200ml) + café (sem açúcar)", 200),
                "Almoço": ("Frango (120g) + salada (alface/rúcula/tomate) + abobrinha + arroz (1/3–1/2 xíc)", 520),
                "Lanche": ("Banana pequena", 120),
                "Jantar": ("Omelete (2 ovos) + salada grande + berinjela", 380),
                "Ceia": ("Café com leite (sem açúcar)", 80),
            },
            "Ter": {
                "Whey pós-treino": ("Whey + leite (200ml) + café (sem açúcar)", 200),
                "Almoço": ("Frango (120g) + abóbora assada + salada + batata pequena", 520),
                "Lanche": ("Mamão (250–300g)", 130),
                "Jantar": ("Frango (100g) + salada + abobrinha", 370),
                "Ceia": ("Café com leite (sem açúcar)", 80),
            },
            "Qua": {  # carne vermelha
                "Whey pós-treino": ("Whey + leite (200ml) + café (sem açúcar)", 200),
                "Almoço": ("Carne vermelha magra (100g) + salada + berinjela + arroz (1/3 xíc)", 560),
                "Lanche": ("Uva (150g)", 110),
                "Jantar": ("Creme de abóbora + frango desfiado (80g) + salada", 350),
                "Ceia": ("Café com leite (sem açúcar)", 80),
            },
            "Qui": {
                "Whey pós-treino": ("Whey + leite (200ml) + café (sem açúcar)", 200),
                "Almoço": ("Frango (120g) + salada + abobrinha + batata pequena", 520),
                "Lanche": ("Morango (200g)", 100),
                "Jantar": ("Atum (1 lata) OU frango (100g) + salada", 400),
                "Ceia": ("Café com leite (sem açúcar)", 80),
            },
            "Sex": {  # carne vermelha
                "Whey pós-treino": ("Whey + leite (200ml) + café (sem açúcar)", 200),
                "Almoço": ("Frango (120g) + salada + abóbora + arroz (1/3–1/2 xíc)", 520),
                "Lanche": ("Goiaba", 120),
                "Jantar": ("Carne vermelha magra (90g) + salada + abobrinha", 380),
                "Ceia": ("Café com leite (sem açúcar)", 80),
            },
            "Sáb": {  # refeição livre no almoço
                "Whey pós-treino": ("Whey + leite (200ml) + café (sem açúcar)", 200),
                "Almoço": ("REFEIÇÃO LIVRE (almoço)", 600),
                "Lanche": ("Fruta leve", 100),
                "Jantar": ("Salada grande + frango (100g)", 320),
                "Ceia": ("Café com leite (sem açúcar)", 80),
            },
            "Dom": {
                "Whey pós-treino": ("Whey + leite (200ml) + café (sem açúcar)", 200),
                "Almoço": ("Frango (120g) + salada + legumes + arroz (1/3–1/2 xíc)", 520),
                "Lanche": ("Pera ou tangerina", 120),
                "Jantar": ("Omelete (2 ovos) + salada + abobrinha", 380),
                "Ceia": ("Café com leite (sem açúcar)", 80),
            },
        }

    tpl = {}
    for d in DAYS:
        for m in MEALS:
            desc, kcal = plan[d][m]
            tpl[(d, m)] = (desc, int(kcal))
    return tpl

def init_week_plan(profile_name: str) -> pd.DataFrame:
    tpl = meal_plan_template(profile_name)
    rows = []
    rid = 1
    for d in DAYS:
        for m in MEALS:
            desc, kcal = tpl.get((d, m), ("", 0))
            rows.append({"rid": rid, "Dia": d, "Refeição": m, "Descrição": desc, "Calorias (kcal)": int(kcal)})
            rid += 1
    return pd.DataFrame(rows).set_index("rid")

def init_exercise_df() -> pd.DataFrame:
    rows = []
    rid = 1
    for d in DAYS:
        rows.append({"rid": rid, "Dia": d, "Corrida (km)": 0.0, "Corrida (min)": 0.0, "Musculação (min)": 0.0})
        rid += 1
    return pd.DataFrame(rows).set_index("rid")

# ============================================================
# Persistência (JSON por perfil)
# ============================================================
def state_path(profile_name: str) -> Path:
    safe = (
        profile_name.lower()
        .replace("ã", "a").replace("á", "a").replace("â", "a")
        .replace(" ", "_")
    )
    return DATA_DIR / f"state_{safe}.json"

def save_profile_state(
    profile_name: str,
    plan_df: pd.DataFrame,
    ex_df: pd.DataFrame,
    weight_kg: float,
    height_cm: int,
    activity_factor: float,
):
    payload = {
        "weight_kg": float(weight_kg),
        "height_cm": int(height_cm),
        "activity_factor": float(activity_factor),
        "plan": plan_df.reset_index().to_dict(orient="records"),
        "exercise": ex_df.reset_index().to_dict(orient="records"),
    }
    state_path(profile_name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def load_profile_state(profile_name: str, default_weight: float, default_height: int, default_activity: float):
    p = state_path(profile_name)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        weight_kg = float(payload.get("weight_kg", default_weight))
        height_cm = int(payload.get("height_cm", default_height))
        activity_factor = float(payload.get("activity_factor", default_activity))

        plan = pd.DataFrame(payload.get("plan", []))
        ex = pd.DataFrame(payload.get("exercise", []))

        if not plan.empty and "rid" in plan.columns:
            plan = plan.set_index("rid")
        if not ex.empty and "rid" in ex.columns:
            ex = ex.set_index("rid")

        return weight_kg, height_cm, activity_factor, plan, ex
    except Exception:
        return None

# ============================================================
# Estado (session)
# ============================================================
if "plans" not in st.session_state:
    st.session_state.plans = {}
if "exercise" not in st.session_state:
    st.session_state.exercise = {}
if "weight" not in st.session_state:
    st.session_state.weight = {}
if "height_cm" not in st.session_state:
    st.session_state.height_cm = {}
if "activity_factor" not in st.session_state:
    st.session_state.activity_factor = {}

# Inicializa perfis
for pname, prof in PROFILES.items():
    if pname not in st.session_state.plans:
        loaded = load_profile_state(pname, prof.weight_kg, prof.default_height_cm, prof.default_activity_factor)
        if loaded is None:
            st.session_state.weight[pname] = prof.weight_kg
            st.session_state.height_cm[pname] = prof.default_height_cm
            st.session_state.activity_factor[pname] = prof.default_activity_factor
            st.session_state.plans[pname] = init_week_plan(pname)
            st.session_state.exercise[pname] = init_exercise_df()
            save_profile_state(
                pname,
                st.session_state.plans[pname],
                st.session_state.exercise[pname],
                st.session_state.weight[pname],
                st.session_state.height_cm[pname],
                st.session_state.activity_factor[pname],
            )
        else:
            weight_kg, height_cm, activity_factor, plan_df, ex_df = loaded
            if plan_df is None or plan_df.empty:
                plan_df = init_week_plan(pname)
            if ex_df is None or ex_df.empty:
                ex_df = init_exercise_df()
            st.session_state.weight[pname] = weight_kg
            st.session_state.height_cm[pname] = height_cm
            st.session_state.activity_factor[pname] = activity_factor
            st.session_state.plans[pname] = plan_df
            st.session_state.exercise[pname] = ex_df

# ============================================================
# UI
# ============================================================
st.title("📊 Calorie tracker — Vitor & Thayná")

c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])

with c1:
    selected = st.selectbox("Selecione o perfil", list(PROFILES.keys()))
    prof = PROFILES[selected]

with c2:
    weight_kg = st.number_input(
        "Peso (kg)",
        min_value=30.0, max_value=250.0,
        value=float(st.session_state.weight[selected]),
        step=0.1,
        key=f"weight_{selected}",
    )
    st.session_state.weight[selected] = float(weight_kg)

with c3:
    height_cm = st.number_input(
        "Altura (cm)",
        min_value=120, max_value=220,
        value=int(st.session_state.height_cm[selected]),
        step=1,
        key=f"height_{selected}",
    )
    st.session_state.height_cm[selected] = int(height_cm)

with c4:
    activity_choice = st.selectbox(
        "Atividade (fora treino)",
        options=[
            ("Sedentário (1.2)", 1.2),
            ("Leve (1.375)", 1.375),
            ("Moderado (1.55)", 1.55),
            ("Alto (1.725)", 1.725),
        ],
        index=[1.2, 1.375, 1.55, 1.725].index(
            float(st.session_state.activity_factor[selected])
        ) if float(st.session_state.activity_factor[selected]) in [1.2, 1.375, 1.55, 1.725] else 2,
        format_func=lambda x: x[0],
        key=f"activity_{selected}",
    )
    activity_factor = float(activity_choice[1])
    st.session_state.activity_factor[selected] = activity_factor

st.caption("✅ Balanço semanal: Ingestão − (TDEE + Exercício). Negativo = déficit (emagrecimento).")
st.caption(f"Limite diário do plano: {prof.daily_limit_kcal} kcal (referência por dia).")

st.divider()

# ============================================================
# Exercícios
# ============================================================
st.subheader("🏃 Exercícios da semana (editável)")
MUSC_MET_MODERADO = 6.0

ex_df = st.session_state.exercise[selected].copy()

# UI sem índice e sem rid
ex_ui = ex_df.reset_index().drop(columns=["rid"], errors="ignore")

ex_ui_edited = st.data_editor(
    ex_ui,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "Dia": st.column_config.TextColumn(disabled=True),
        "Corrida (km)": st.column_config.NumberColumn(min_value=0.0, max_value=200.0, step=0.1),
        "Corrida (min)": st.column_config.NumberColumn(min_value=0.0, max_value=600.0, step=1.0),
        "Musculação (min)": st.column_config.NumberColumn(min_value=0.0, max_value=600.0, step=5.0),
    },
    key=f"ex_editor_{selected}",
)

# Merge de volta pelo Dia
ex_full = ex_df.copy()
for _, row in ex_ui_edited.iterrows():
    mask = (ex_full["Dia"] == row["Dia"])
    ex_full.loc[mask, ["Corrida (km)", "Corrida (min)", "Musculação (min)"]] = [
        float(row.get("Corrida (km)", 0) or 0),
        float(row.get("Corrida (min)", 0) or 0),
        float(row.get("Musculação (min)", 0) or 0),
    ]
st.session_state.exercise[selected] = ex_full

# Calcula gastos
kcal_run_list, speed_list, met_list, kcal_musc_list, kcal_total_list = [], [], [], [], []
for _, r in ex_full.iterrows():
    kcal_run, speed, met = calc_running_kcal(weight_kg, r["Corrida (km)"], r["Corrida (min)"])
    kcal_musc = kcal_from_met(weight_kg, r["Musculação (min)"], MUSC_MET_MODERADO)
    kcal_total = kcal_run + kcal_musc

    kcal_run_list.append(kcal_run)
    speed_list.append(speed)
    met_list.append(met)
    kcal_musc_list.append(kcal_musc)
    kcal_total_list.append(kcal_total)

ex_calc = ex_full.copy()
ex_calc["Vel. média (km/h)"] = [round(x, 1) for x in speed_list]
ex_calc["MET corrida (estim.)"] = [round(x, 1) for x in met_list]
ex_calc["Gasto corrida (kcal)"] = [int(round(x)) for x in kcal_run_list]
ex_calc["Gasto musculação (kcal)"] = [int(round(x)) for x in kcal_musc_list]
ex_calc["Gasto total exercício (kcal)"] = [int(round(x)) for x in kcal_total_list]

st.dataframe(
    ex_calc[[
        "Dia", "Corrida (km)", "Corrida (min)", "Vel. média (km/h)", "MET corrida (estim.)",
        "Musculação (min)", "Gasto corrida (kcal)", "Gasto musculação (kcal)", "Gasto total exercício (kcal)"
    ]],
    use_container_width=True,
    hide_index=True,
)

st.caption("Corrida/HIIT: usa velocidade média (km/h) para estimar MET. Musculação moderada fixa em MET=6.0.")

st.divider()

# ============================================================
# Plano alimentar
# ============================================================
st.subheader("🍽️ Plano alimentar (editável)")
day_filter = st.selectbox("Filtrar por dia", ["Todos"] + DAYS, index=0, key=f"day_filter_{selected}")

plan_full = st.session_state.plans[selected].copy()
plan_view = plan_full.copy() if day_filter == "Todos" else plan_full[plan_full["Dia"] == day_filter].copy()

# UI sem índice e sem rid
plan_view_ui = plan_view.reset_index().drop(columns=["rid"], errors="ignore")

plan_ui_edited = st.data_editor(
    plan_view_ui,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "Dia": st.column_config.TextColumn(disabled=True),
        "Refeição": st.column_config.TextColumn(disabled=True),
        "Descrição": st.column_config.TextColumn(width="large"),
        "Calorias (kcal)": st.column_config.NumberColumn(min_value=0, max_value=5000, step=10),
    },
    key=f"plan_editor_{selected}_{day_filter}",
)

plan_ui_edited["Calorias (kcal)"] = (
    plan_ui_edited["Calorias (kcal)"]
    .fillna(0)
    .astype(int)
    .clip(0, 20000)
)

# Merge por (Dia, Refeição)
plan_full2 = plan_full.copy()
for _, row in plan_ui_edited.iterrows():
    mask = (plan_full2["Dia"] == row["Dia"]) & (plan_full2["Refeição"] == row["Refeição"])
    plan_full2.loc[mask, ["Descrição", "Calorias (kcal)"]] = [row["Descrição"], int(row["Calorias (kcal)"])]

st.session_state.plans[selected] = plan_full2

st.divider()

# ============================================================
# Resumo por dia + alertas de limite
# ============================================================
st.subheader("📈 Resumo por dia (limite do plano)")
plan_full = st.session_state.plans[selected].copy()

daily_intake = (
    plan_full.groupby("Dia", as_index=False)["Calorias (kcal)"]
    .sum()
    .rename(columns={"Calorias (kcal)": "Ingestão (kcal)"})
)

daily_ex = ex_calc[["Dia", "Gasto total exercício (kcal)"]].reset_index(drop=True)

daily = daily_intake.merge(daily_ex, on="Dia", how="left")
daily["Gasto total exercício (kcal)"] = daily["Gasto total exercício (kcal)"].fillna(0).astype(int)

daily_limit = int(prof.daily_limit_kcal)
daily["Limite diário (kcal)"] = daily_limit
daily["Diferença (Limite - Ingestão)"] = daily["Limite diário (kcal)"] - daily["Ingestão (kcal)"]

daily["__ord"] = daily["Dia"].map(DAY_ORDER).fillna(999).astype(int)
daily = daily.sort_values("__ord").drop(columns=["__ord"])

over = daily[daily["Ingestão (kcal)"] > daily_limit]
under = daily[daily["Ingestão (kcal)"] < daily_limit]

if not over.empty:
    excedentes = ", ".join([f"{r['Dia']} (+{int(r['Ingestão (kcal)'] - daily_limit)} kcal)" for _, r in over.iterrows()])
    st.error(f"Acima do limite do plano em: {excedentes}")

if not under.empty:
    faltas = ", ".join([f"{r['Dia']} (-{int(daily_limit - r['Ingestão (kcal)'])} kcal)" for _, r in under.iterrows()])
    st.info(f"Abaixo do limite do plano em: {faltas}")

def highlight_rows(row):
    if int(row["Ingestão (kcal)"]) > daily_limit:
        return ["background-color: rgba(255, 0, 0, 0.18)"] * len(row)
    return [""] * len(row)

cols_show = ["Dia", "Ingestão (kcal)", "Gasto total exercício (kcal)", "Limite diário (kcal)", "Diferença (Limite - Ingestão)"]

st.dataframe(
    daily[cols_show].style.apply(highlight_rows, axis=1),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ============================================================
# Total da semana — balanço real + estimativa de perda de peso
# ============================================================
st.subheader("🧾 Total da semana — balanço energético real")

week_intake = int(daily["Ingestão (kcal)"].sum())
week_ex = int(daily["Gasto total exercício (kcal)"].sum())

bmr_day = bmr_mifflin_st_jeor(prof.sex, weight_kg, height_cm, prof.age)
tdee_day = tdee_kcal_day(bmr_day, activity_factor)  # sem exercício estruturado
week_tdee = int(round(tdee_day * 7))

# Balanço: ingestão - (tdee + exercício)
week_balance = int(round(week_intake - (week_tdee + week_ex)))

# Estimativa de variação de peso (1 kg ~ 7700 kcal)
# Negativo => perda; positivo => ganho.
kg_change_est = week_balance / 7700.0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Ingestão semanal (kcal)", f"{week_intake}")
k2.metric("Exercício semanal (kcal)", f"{week_ex}")
k3.metric("TDEE semanal (kcal) (BMR×atividade)", f"{week_tdee}")

if week_balance < 0:
    k4.metric("Déficit semanal (kcal)", f"{week_balance}")
    st.success(f"✅ Déficit de {abs(week_balance)} kcal na semana (tendência a emagrecimento).")
elif week_balance > 0:
    k4.metric("Superávit semanal (kcal)", f"{week_balance}")
    st.warning(f"⚠️ Superávit de {week_balance} kcal na semana (tendência a ganho/manutenção).")
else:
    k4.metric("Saldo semanal (kcal)", "0")
    st.info("Saldo neutro na semana (manutenção).")

# Estimativa em kg
if week_balance < 0:
    st.write(f"📉 **Estimativa de perda de peso na semana:** ~ **{abs(kg_change_est):.2f} kg** (aprox.).")
elif week_balance > 0:
    st.write(f"📈 **Estimativa de ganho de peso na semana:** ~ **{abs(kg_change_est):.2f} kg** (aprox.).")
else:
    st.write("⚖️ **Estimativa de variação de peso:** ~ **0.00 kg**.")

st.caption("Obs.: estimativa aproximada (7700 kcal ≈ 1 kg). Peso real varia por água, glicogênio e retenção.")

st.divider()

# ============================================================
# SALVAR AUTOMÁTICO + AÇÕES
# ============================================================
save_profile_state(
    selected,
    st.session_state.plans[selected],
    st.session_state.exercise[selected],
    st.session_state.weight[selected],
    st.session_state.height_cm[selected],
    st.session_state.activity_factor[selected],
)

a1, a2 = st.columns([1, 1])

with a1:
    if st.button("🔄 Resetar (perfil atual)"):
        st.session_state.weight[selected] = PROFILES[selected].weight_kg
        st.session_state.height_cm[selected] = PROFILES[selected].default_height_cm
        st.session_state.activity_factor[selected] = PROFILES[selected].default_activity_factor
        st.session_state.plans[selected] = init_week_plan(selected)
        st.session_state.exercise[selected] = init_exercise_df()

        save_profile_state(
            selected,
            st.session_state.plans[selected],
            st.session_state.exercise[selected],
            st.session_state.weight[selected],
            st.session_state.height_cm[selected],
            st.session_state.activity_factor[selected],
        )
        st.rerun()

with a2:
    if st.button("📋 Copiar do outro perfil"):
        other = "Thayná" if selected == "Vitor" else "Vitor"
        st.session_state.plans[selected] = st.session_state.plans[other].copy()
        st.session_state.exercise[selected] = st.session_state.exercise[other].copy()

        save_profile_state(
            selected,
            st.session_state.plans[selected],
            st.session_state.exercise[selected],
            st.session_state.weight[selected],
            st.session_state.height_cm[selected],
            st.session_state.activity_factor[selected],
        )
        st.rerun()
