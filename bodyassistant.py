# app.py
import json
from pathlib import Path
from dataclasses import dataclass

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Calorie tracker - Vitor & Thayná", layout="wide")

# -----------------------------
# Constantes
# -----------------------------
DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
DAY_ORDER = {d: i for i, d in enumerate(DAYS)}
MEALS = ["Whey pós-treino", "Almoço", "Lanche", "Jantar", "Ceia"]

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# -----------------------------
# Perfis
# -----------------------------
@dataclass
class Profile:
    name: str
    age: int
    weight_kg: float
    sex: str
    base_intake_kcal: int

PROFILES = {
    "Vitor": Profile(name="Vitor", age=35, weight_kg=97.0, sex="M", base_intake_kcal=1400),
    "Thayná": Profile(name="Thayná", age=32, weight_kg=63.0, sex="F", base_intake_kcal=1200),
}

# -----------------------------
# Cálculos (gasto calórico)
# -----------------------------
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

# -----------------------------
# Plano alimentar sugerido
# -----------------------------
def meal_plan_template(profile_name: str) -> dict:
    if profile_name == "Thayná":
        whey = ("Whey com leite (200ml) + café expresso (sem açúcar)", 220)
        lanches = [
            ("1 fruta (banana OU mamão) + café expresso", 140),
            ("Morangos (200g) OU uva (150g)", 120),
            ("Pera OU tangerina + café com leite (sem açúcar)", 170),
            ("Goiaba + café expresso", 120),
        ]
        almocos = {
            "Seg": ("Frango (120g) + salada (alface/rúcula/tomate) + abobrinha + 1/2 xíc. arroz parboilizado", 500),
            "Ter": ("Frango (120g) + abóbora assada + salada + 1 batata média", 480),
            "Qua": ("Carne vermelha magra (100g) + salada + berinjela + 1/2 xíc. arroz parboilizado", 520),
            "Qui": ("Frango (120g) + abobrinha + salada + 1/2 xíc. arroz parboilizado", 490),
            "Sex": ("Frango (120g) + abóbora + salada + batata (pequena/média)", 480),
            "Sáb": ("REFEIÇÃO LIVRE (almoço)", 650),
            "Dom": ("Frango (120g) + salada + legumes + 1/2 xíc. arroz parboilizado", 490),
        }
        jantares = {
            "Seg": ("Omelete (2 ovos) + salada grande + abobrinha", 380),
            "Ter": ("Frango (100g) + salada + berinjela", 350),
            "Qua": ("Creme de abóbora + frango desfiado (80g) + salada", 360),
            "Qui": ("Atum (1 lata) OU frango (100g) + salada + legumes", 360),
            "Sex": ("Carne vermelha magra (90g) + salada + abobrinha", 390),
            "Sáb": ("Jantar leve: salada + frango (100g) OU omelete (2 ovos)", 360),
            "Dom": ("Frango (100g) + salada + berinjela", 350),
        }
        ceia = ("Café com leite (sem açúcar) OU 1 fruta pequena", 120)
    else:
        whey = ("Whey com leite (250ml) + (opcional) shot de café (sem açúcar)", 280)
        lanches = [
            ("1 banana + café expresso", 170),
            ("Mamão (300g) OU uva (200g)", 160),
            ("Pera + café com leite (sem açúcar)", 200),
            ("Goiaba + café expresso", 150),
        ]
        almocos = {
            "Seg": ("Frango (180g) + salada (alface/rúcula/tomate) + abobrinha + 3/4 xíc. arroz parboilizado", 650),
            "Ter": ("Frango (180g) + abóbora assada + salada + 1 batata média", 630),
            "Qua": ("Carne vermelha magra (150g) + salada + berinjela + 3/4 xíc. arroz parboilizado", 700),
            "Qui": ("Frango (180g) + salada + abobrinha + 3/4 xíc. arroz parboilizado", 640),
            "Sex": ("Frango (180g) + abóbora + salada + batata média", 630),
            "Sáb": ("REFEIÇÃO LIVRE (almoço)", 850),
            "Dom": ("Frango (180g) + salada + legumes + 3/4 xíc. arroz parboilizado", 650),
        }
        jantares = {
            "Seg": ("Omelete (3 ovos) + salada grande + abobrinha", 480),
            "Ter": ("Frango (150g) + salada + berinjela", 430),
            "Qua": ("Creme de abóbora + frango desfiado (120g) + salada", 450),
            "Qui": ("Atum (1 lata) + 2 ovos OU frango (150g) + salada + legumes", 480),
            "Sex": ("Carne vermelha magra (130g) + salada + abobrinha", 500),
            "Sáb": ("Jantar leve: salada + frango (150g) OU omelete (3 ovos)", 480),
            "Dom": ("Frango (150g) + salada + berinjela", 430),
        }
        ceia = ("Café com leite (sem açúcar) OU 1 fruta", 150)

    tpl = {}
    for i, d in enumerate(DAYS):
        tpl[(d, "Whey pós-treino")] = whey
        tpl[(d, "Almoço")] = almocos[d]
        tpl[(d, "Lanche")] = lanches[i % len(lanches)]
        tpl[(d, "Jantar")] = jantares[d]
        tpl[(d, "Ceia")] = ceia
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
    df = pd.DataFrame(rows).set_index("rid")
    return df

def init_exercise_df() -> pd.DataFrame:
    rows = []
    rid = 1
    for d in DAYS:
        rows.append({"rid": rid, "Dia": d, "Corrida (km)": 0.0, "Corrida (min)": 0.0, "Musculação (min)": 0.0})
        rid += 1
    return pd.DataFrame(rows).set_index("rid")

# -----------------------------
# Persistência (JSON por perfil)
# -----------------------------
def state_path(profile_name: str) -> Path:
    safe = profile_name.lower().replace("ã", "a").replace("á", "a").replace("â", "a").replace(" ", "_")
    return DATA_DIR / f"state_{safe}.json"

def save_profile_state(profile_name: str, plan_df: pd.DataFrame, ex_df: pd.DataFrame, base_intake: int, weight_kg: float):
    payload = {
        "base_intake": int(base_intake),
        "weight_kg": float(weight_kg),
        "plan": plan_df.reset_index().to_dict(orient="records"),
        "exercise": ex_df.reset_index().to_dict(orient="records"),
    }
    state_path(profile_name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def load_profile_state(profile_name: str, default_base: int, default_weight: float):
    p = state_path(profile_name)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        base_intake = int(payload.get("base_intake", default_base))
        weight_kg = float(payload.get("weight_kg", default_weight))

        plan = pd.DataFrame(payload.get("plan", []))
        ex = pd.DataFrame(payload.get("exercise", []))

        if not plan.empty and "rid" in plan.columns:
            plan = plan.set_index("rid")
        if not ex.empty and "rid" in ex.columns:
            ex = ex.set_index("rid")

        return base_intake, weight_kg, plan, ex
    except Exception:
        return None

# -----------------------------
# Estado em memória (session)
# -----------------------------
if "plans" not in st.session_state:
    st.session_state.plans = {}
if "exercise" not in st.session_state:
    st.session_state.exercise = {}
if "base_intake" not in st.session_state:
    st.session_state.base_intake = {}
if "weight" not in st.session_state:
    st.session_state.weight = {}

# Inicializa cada perfil (carrega do disco se existir)
for pname, prof in PROFILES.items():
    if pname not in st.session_state.plans:
        loaded = load_profile_state(pname, prof.base_intake_kcal, prof.weight_kg)
        if loaded is None:
            st.session_state.base_intake[pname] = prof.base_intake_kcal
            st.session_state.weight[pname] = prof.weight_kg
            st.session_state.plans[pname] = init_week_plan(pname)
            st.session_state.exercise[pname] = init_exercise_df()
            save_profile_state(pname, st.session_state.plans[pname], st.session_state.exercise[pname],
                               st.session_state.base_intake[pname], st.session_state.weight[pname])
        else:
            base_intake, weight_kg, plan_df, ex_df = loaded
            # fallback se algo vier vazio
            if plan_df is None or plan_df.empty:
                plan_df = init_week_plan(pname)
            if ex_df is None or ex_df.empty:
                ex_df = init_exercise_df()

            st.session_state.base_intake[pname] = base_intake
            st.session_state.weight[pname] = weight_kg
            st.session_state.plans[pname] = plan_df
            st.session_state.exercise[pname] = ex_df

# -----------------------------
# UI
# -----------------------------
st.title("📊 Plano Alimentar + Gasto Calórico (Vitor & Thayná)")

c1, c2, c3 = st.columns([1.1, 1, 1])

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
    st.session_state.weight[selected] = weight_kg

with c3:
    base_intake = st.number_input(
        "Caloria base diária do plano (kcal)",
        min_value=800, max_value=4000,
        value=int(st.session_state.base_intake[selected]),
        step=50,
        key=f"base_{selected}",
    )
    st.session_state.base_intake[selected] = int(base_intake)

st.divider()

# -----------------------------
# Exercícios
# -----------------------------
st.subheader("Exercícios da semana")

MUSC_MET_MODERADO = 6.0

ex_df = st.session_state.exercise[selected].copy()

ex_edited = st.data_editor(
    ex_df.reset_index(),
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "rid": st.column_config.NumberColumn("rid", disabled=True),
        "Dia": st.column_config.TextColumn(disabled=True),
        "Corrida (km)": st.column_config.NumberColumn(min_value=0.0, max_value=200.0, step=0.1),
        "Corrida (min)": st.column_config.NumberColumn(min_value=0.0, max_value=600.0, step=1.0),
        "Musculação (min)": st.column_config.NumberColumn(min_value=0.0, max_value=600.0, step=5.0),
    },
    key=f"ex_editor_{selected}",
)

ex_edited = ex_edited.set_index("rid")
st.session_state.exercise[selected] = ex_edited

kcal_run_list, speed_list, met_list, kcal_musc_list, kcal_total_list = [], [], [], [], []
for _, r in ex_edited.iterrows():
    kcal_run, speed, met = calc_running_kcal(weight_kg, r["Corrida (km)"], r["Corrida (min)"])
    kcal_musc = kcal_from_met(weight_kg, r["Musculação (min)"], MUSC_MET_MODERADO)
    kcal_total = kcal_run + kcal_musc

    kcal_run_list.append(kcal_run)
    speed_list.append(speed)
    met_list.append(met)
    kcal_musc_list.append(kcal_musc)
    kcal_total_list.append(kcal_total)

ex_calc = ex_edited.copy()
ex_calc["Vel. média (km/h)"] = [round(x, 1) for x in speed_list]
ex_calc["MET corrida (estim.)"] = [round(x, 1) for x in met_list]
ex_calc["Gasto corrida (kcal)"] = [int(round(x)) for x in kcal_run_list]
ex_calc["Gasto musculação (kcal)"] = [int(round(x)) for x in kcal_musc_list]
ex_calc["Gasto total exercício (kcal)"] = [int(round(x)) for x in kcal_total_list]

st.dataframe(
    ex_calc[["Dia", "Corrida (km)", "Corrida (min)", "Vel. média (km/h)", "MET corrida (estim.)",
             "Musculação (min)", "Gasto corrida (kcal)", "Gasto musculação (kcal)", "Gasto total exercício (kcal)"]],
    use_container_width=True,
)

st.caption("Corrida/HIIT: usa velocidade média (km/h) para estimar MET. Musculação moderada fixa em MET=6.0.")

st.divider()

# -----------------------------
# Plano alimentar com filtro por dia
# -----------------------------
st.subheader("Plano alimentar semanal sugerido")

day_filter = st.selectbox("Filtrar por dia", ["Todos"] + DAYS, index=0, key=f"day_filter_{selected}")

plan_full = st.session_state.plans[selected].copy()

if day_filter == "Todos":
    plan_view = plan_full.copy()
else:
    plan_view = plan_full[plan_full["Dia"] == day_filter].copy()

plan_edited_view = st.data_editor(
    plan_view.reset_index(),
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "rid": st.column_config.NumberColumn("rid", disabled=True),
        "Dia": st.column_config.TextColumn(disabled=True),
        "Refeição": st.column_config.TextColumn(disabled=True),
        "Descrição": st.column_config.TextColumn(width="large"),
        "Calorias (kcal)": st.column_config.NumberColumn(min_value=0, max_value=5000, step=10),
    },
    key=f"plan_editor_{selected}_{day_filter}",
)

plan_edited_view = plan_edited_view.set_index("rid")
plan_edited_view["Calorias (kcal)"] = (
    plan_edited_view["Calorias (kcal)"].fillna(0).astype(int).clip(0, 20000)
)

# Merge de volta para o plano completo (atualiza só os rids editados)
plan_full.loc[plan_edited_view.index, ["Descrição", "Calorias (kcal)"]] = plan_edited_view[["Descrição", "Calorias (kcal)"]]
st.session_state.plans[selected] = plan_full

st.divider()

# -----------------------------
# Resumo por dia (ordenado Seg..Dom)
# -----------------------------
st.subheader("Resumo por dia")

daily_intake = (
    plan_full.groupby("Dia", as_index=False)["Calorias (kcal)"]
    .sum()
    .rename(columns={"Calorias (kcal)": "Ingestão (kcal)"})
)

daily_ex = ex_calc[["Dia", "Gasto total exercício (kcal)"]].reset_index(drop=True)

daily = daily_intake.merge(daily_ex, on="Dia", how="left")
daily["Gasto total exercício (kcal)"] = daily["Gasto total exercício (kcal)"].fillna(0).astype(int)

daily["Base do plano (kcal)"] = int(base_intake)
daily["Base + exercício (kcal)"] = daily["Base do plano (kcal)"] + daily["Gasto total exercício (kcal)"]
daily["Saldo (Base+Ex - Ingestão)"] = daily["Base + exercício (kcal)"] - daily["Ingestão (kcal)"]

daily["__ord"] = daily["Dia"].map(DAY_ORDER).fillna(999).astype(int)
daily = daily.sort_values("__ord").drop(columns=["__ord"])

st.dataframe(
    daily[["Dia", "Ingestão (kcal)", "Gasto total exercício (kcal)", "Base do plano (kcal)", "Base + exercício (kcal)", "Saldo (Base+Ex - Ingestão)"]],
    use_container_width=True,
)

# Semana
st.subheader("Total da semana")
week_intake = int(daily["Ingestão (kcal)"].sum())
week_ex = int(daily["Gasto total exercício (kcal)"].sum())
week_base = int(base_intake * 7)
week_base_plus_ex = int(daily["Base + exercício (kcal)"].sum())
week_saldo = int(week_base_plus_ex - week_intake)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Ingestão semanal (kcal) (+)", f"{week_intake}")
k2.metric("Exercício semanal (kcal)(-)", f"{week_ex}")
k3.metric("Base semanal (kcal)(-)", f"{week_base}")
k4.metric("Gasto total semanal", f"{week_saldo}")

st.divider()

# -----------------------------
# Ações + SALVAR AUTOMÁTICO
# -----------------------------
# salva automaticamente a cada execução após as edições
save_profile_state(
    selected,
    st.session_state.plans[selected],
    st.session_state.exercise[selected],
    st.session_state.base_intake[selected],
    st.session_state.weight[selected],
)

a1, a2 = st.columns([1, 1])

with a1:
    if st.button("🔄 Resetar (perfil atual)"):
        st.session_state.plans[selected] = init_week_plan(selected)
        st.session_state.exercise[selected] = init_exercise_df()
        st.session_state.base_intake[selected] = PROFILES[selected].base_intake_kcal
        st.session_state.weight[selected] = PROFILES[selected].weight_kg
        save_profile_state(
            selected,
            st.session_state.plans[selected],
            st.session_state.exercise[selected],
            st.session_state.base_intake[selected],
            st.session_state.weight[selected],
        )
        st.rerun()

with a2:
    if st.button("📋 Copiar do outro perfil"):
        other = "Thayná" if selected == "Vitor" else "Vitor"
        st.session_state.plans[selected] = st.session_state.plans[other].copy()
        st.session_state.exercise[selected] = st.session_state.exercise[other].copy()
        # mantém base/peso do perfil atual
        save_profile_state(
            selected,
            st.session_state.plans[selected],
            st.session_state.exercise[selected],
            st.session_state.base_intake[selected],
            st.session_state.weight[selected],
        )
        st.rerun()
