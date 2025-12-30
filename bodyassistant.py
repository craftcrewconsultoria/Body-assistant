# app.py
import streamlit as st
import pandas as pd
from dataclasses import dataclass

st.set_page_config(page_title="Plano & Calorias - Vitor & Thayná", layout="wide")

# -----------------------------
# Perfis
# -----------------------------
@dataclass
class Profile:
    name: str
    age: int
    weight_kg: float
    sex: str
    base_intake_kcal: int  # plano alimentar base (pedido)
    default_height_cm: int = 170
    default_activity_factor: float = 1.45

PROFILES = {
    "Vitor": Profile(name="Vitor", age=35, weight_kg=97.0, sex="M", base_intake_kcal=1400, default_height_cm=180),
    "Thayná": Profile(name="Thayná", age=32, weight_kg=63.0, sex="F", base_intake_kcal=1200, default_height_cm=165),
}

DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MEALS = ["Whey pós-treino", "Almoço", "Lanche", "Jantar", "Ceia"]

# -----------------------------
# Cálculos (gasto calórico)
# -----------------------------
def kcal_from_met(weight_kg: float, minutes: float, met: float) -> float:
    # kcal = MET * 3.5 * peso(kg) / 200 * minutos
    minutes = max(0.0, float(minutes))
    met = max(0.0, float(met))
    return met * 3.5 * float(weight_kg) / 200.0 * minutes

def running_met_from_speed_kmh(speed_kmh: float) -> float:
    """
    Heurística para HIIT/corrida:
    usa velocidade média para aproximar o MET (inclui efeito de caminhar/correr intercalado).
    """
    v = max(0.0, float(speed_kmh))
    if v <= 0.1:
        return 0.0
    if v < 5.0:      # caminhada leve/moderada
        return 3.5
    if v < 6.5:      # caminhada rápida / trote leve
        return 5.0
    if v < 8.0:      # trote / corrida leve
        return 7.0
    if v < 10.0:     # corrida moderada
        return 9.8
    if v < 12.0:     # corrida forte
        return 11.5
    return 12.8      # bem forte

def calc_running_kcal(weight_kg: float, distance_km: float, minutes: float):
    minutes = max(0.0, float(minutes))
    distance_km = max(0.0, float(distance_km))
    if minutes <= 0.0 or distance_km <= 0.0:
        return 0.0, 0.0, 0.0  # kcal, speed, met
    hours = minutes / 60.0
    speed = distance_km / hours
    met = running_met_from_speed_kmh(speed)
    kcal = kcal_from_met(weight_kg, minutes, met)
    return kcal, speed, met

# -----------------------------
# Plano alimentar sugerido (pré-preenchido)
# -----------------------------
def meal_plan_template(profile_name: str) -> dict:
    """
    Retorna um dicionário: (Dia, Refeição) -> (Descrição, kcal)
    Ajustado às preferências: whey pela manhã, almoço principal, frutas, frango/legumes/salada,
    carne vermelha 2x/semana, sábado 1 refeição livre.
    """
    if profile_name == "Thayná":
        # Base ~1200/dia (aproximações)
        whey = ("Whey com leite (200ml) + café expresso (sem açúcar)", 220)
        lanche = [
            ("1 fruta (banana OU mamão) + café expresso", 140),
            ("Morangos (200g) OU uva (150g)", 120),
            ("Pera OU tangerina + café com leite (sem açúcar)", 170),
            ("Goiaba + café expresso", 120),
        ]
        # Almoços ~450-520
        almocos = {
            "Seg": ("Frango grelhado (120g) + salada (alface/rúcula/tomate) + abobrinha refogada + 1/2 xíc. arroz parboilizado", 500),
            "Ter": ("Frango desfiado (120g) + abóbora assada + salada + 1 batata média cozida", 480),
            "Qua": ("Carne vermelha magra (100g) + salada + berinjela grelhada + 1/2 xíc. arroz parboilizado", 520),
            "Qui": ("Frango grelhado (120g) + abobrinha + salada + 1/2 xíc. arroz parboilizado", 490),
            "Sex": ("Frango (120g) + abóbora + salada + batata (pequena/média)", 480),
            "Sáb": ("REFEIÇÃO LIVRE (almoço)", 650),
            "Dom": ("Frango (120g) + salada + legumes (berinjela/abobrinha) + 1/2 xíc. arroz parboilizado", 490),
        }
        # Jantares ~320-420
        jantares = {
            "Seg": ("Omelete (2 ovos) + salada grande + abobrinha", 380),
            "Ter": ("Frango (100g) + salada + berinjela", 350),
            "Qua": ("Sopa/creme de abóbora + frango desfiado (80g) + salada", 360),
            "Qui": ("Atum (1 lata) OU frango (100g) + salada + legumes", 360),
            "Sex": ("Carne vermelha magra (90g) + salada + abobrinha", 390),
            "Sáb": ("Jantar leve: salada + frango (100g) OU omelete (2 ovos)", 360),
            "Dom": ("Frango (100g) + salada + berinjela", 350),
        }
        ceia = ("Café com leite (sem açúcar) OU 1 fruta pequena", 120)

    else:
        # Vitor base ~1400/dia (aproximações)
        whey = ("Whey com leite (250ml) + (opcional) shot de café (sem açúcar)", 280)
        lanche = [
            ("1 banana + café expresso", 170),
            ("Mamão (300g) OU uva (200g)", 160),
            ("Pera + café com leite (sem açúcar)", 200),
            ("Goiaba + café expresso", 150),
        ]
        # Almoços ~550-700
        almocos = {
            "Seg": ("Frango grelhado (180g) + salada (alface/rúcula/tomate) + abobrinha + 3/4 xíc. arroz parboilizado", 650),
            "Ter": ("Frango desfiado (180g) + abóbora assada + salada + 1 batata média", 630),
            "Qua": ("Carne vermelha magra (150g) + salada + berinjela + 3/4 xíc. arroz parboilizado", 700),
            "Qui": ("Frango (180g) + salada + abobrinha + 3/4 xíc. arroz parboilizado", 640),
            "Sex": ("Frango (180g) + abóbora + salada + batata média", 630),
            "Sáb": ("REFEIÇÃO LIVRE (almoço)", 850),
            "Dom": ("Frango (180g) + salada + legumes + 3/4 xíc. arroz parboilizado", 650),
        }
        # Jantares ~400-520
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

    # Monta template
    tpl = {}
    for i, d in enumerate(DAYS):
        tpl[(d, "Whey pós-treino")] = whey
        tpl[(d, "Almoço")] = almocos[d]
        tpl[(d, "Lanche")] = lanche[i % len(lanche)]
        tpl[(d, "Jantar")] = jantares[d]
        tpl[(d, "Ceia")] = ceia

    return tpl

def init_week_plan(profile_name: str) -> pd.DataFrame:
    tpl = meal_plan_template(profile_name)
    rows = []
    for d in DAYS:
        for m in MEALS:
            desc, kcal = tpl.get((d, m), ("", 0))
            rows.append({"Dia": d, "Refeição": m, "Descrição": desc, "Calorias (kcal)": int(kcal)})
    return pd.DataFrame(rows)

def init_exercise_df() -> pd.DataFrame:
    return pd.DataFrame([{"Dia": d, "Corrida (km)": 0.0, "Corrida (min)": 0.0, "Musculação (min)": 0.0} for d in DAYS])

# -----------------------------
# Estado
# -----------------------------
if "plans" not in st.session_state:
    st.session_state.plans = {p: init_week_plan(p) for p in PROFILES.keys()}

if "exercise" not in st.session_state:
    st.session_state.exercise = {p: init_exercise_df() for p in PROFILES.keys()}

# -----------------------------
# UI
# -----------------------------
st.title("📊 Plano Alimentar + Gasto Calórico (Vitor & Thayná)")

top1, top2 = st.columns([1, 1])

with top1:
    selected = st.selectbox("Selecione o perfil", list(PROFILES.keys()))
    prof = PROFILES[selected]
with top2:
    weight_kg = st.number_input("Peso (kg) do perfil selecionado", min_value=30.0, max_value=250.0, value=float(prof.weight_kg), step=0.1)
    base_intake = st.number_input("Caloria base diária do plano (kcal)", min_value=800, max_value=4000, value=int(prof.base_intake_kcal), step=50)

st.divider()

# -----------------------------
# Exercícios
# -----------------------------
st.subheader("🏃 Exercícios (semana) — Corrida/HIIT + Musculação")

ex_df = st.session_state.exercise[selected].copy()

ex_edited = st.data_editor(
    ex_df,
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

st.session_state.exercise[selected] = ex_edited

# Calcula gastos por dia
MUSC_MET_MODERADO = 6.0

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

st.caption(
    "Corrida/HIIT: o app usa velocidade média (km/h) para estimar MET e calcular o gasto. "
    "Musculação moderada fixa em MET=6.0."
)

st.divider()

# -----------------------------
# Plano alimentar
# -----------------------------
st.subheader("🍽️ Plano alimentar semanal (sugestão já preenchida)")

plan_df = st.session_state.plans[selected].copy()

plan_edited = st.data_editor(
    plan_df,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "Dia": st.column_config.TextColumn(disabled=True),
        "Refeição": st.column_config.TextColumn(disabled=True),
        "Descrição": st.column_config.TextColumn(width="large"),
        "Calorias (kcal)": st.column_config.NumberColumn(min_value=0, max_value=5000, step=10),
    },
    key=f"plan_editor_{selected}",
)

plan_edited["Calorias (kcal)"] = plan_edited["Calorias (kcal)"].fillna(0).astype(int).clip(0, 20000)
st.session_state.plans[selected] = plan_edited

# -----------------------------
# Resumo por dia (ingestão x base + exercício)
# -----------------------------
st.subheader("📈 Resumo por dia")

daily_intake = (
    plan_edited.groupby("Dia", as_index=False)["Calorias (kcal)"]
    .sum()
    .rename(columns={"Calorias (kcal)": "Ingestão (kcal)"})
)

daily_ex = ex_calc[["Dia", "Gasto total exercício (kcal)"]].copy()

daily = daily_intake.merge(daily_ex, on="Dia", how="left")
daily["Gasto total exercício (kcal)"] = daily["Gasto total exercício (kcal)"].fillna(0).astype(int)

daily["Base do plano (kcal)"] = int(base_intake)
daily["Base + exercício (kcal)"] = daily["Base do plano (kcal)"] + daily["Gasto total exercício (kcal)"]
daily["Saldo (Base+Ex - Ingestão)"] = daily["Base + exercício (kcal)"] - daily["Ingestão (kcal)"]

st.dataframe(
    daily[["Dia", "Ingestão (kcal)", "Gasto total exercício (kcal)", "Base do plano (kcal)", "Base + exercício (kcal)", "Saldo (Base+Ex - Ingestão)"]],
    use_container_width=True,
)

# Semana
st.subheader("🧾 Semana (totais)")
week_intake = int(daily["Ingestão (kcal)"].sum())
week_ex = int(daily["Gasto total exercício (kcal)"].sum())
week_base = int(base_intake * 7)
week_base_plus_ex = int(daily["Base + exercício (kcal)"].sum())
week_saldo = int(week_base_plus_ex - week_intake)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ingestão semanal (kcal)", f"{week_intake}")
c2.metric("Exercício semanal (kcal)", f"{week_ex}")
c3.metric("Base semanal (kcal)", f"{week_base}")
c4.metric("Saldo semanal (Base+Ex - Ingestão)", f"{week_saldo}")

st.divider()

# -----------------------------
# Ações
# -----------------------------
b1, b2, b3 = st.columns([1, 1, 2])

with b1:
    if st.button("🔄 Resetar (perfil atual)"):
        st.session_state.plans[selected] = init_week_plan(selected)
        st.session_state.exercise[selected] = init_exercise_df()
        st.rerun()

with b2:
    if st.button("📋 Copiar do outro perfil"):
        other = "Thayná" if selected == "Vitor" else "Vitor"
        st.session_state.plans[selected] = st.session_state.plans[other].copy()
        st.session_state.exercise[selected] = st.session_state.exercise[other].copy()
        st.rerun()

with b3:
    export_plan = st.session_state.plans[selected].copy()
    export_ex = st.session_state.exercise[selected].copy()

    st.download_button(
        "⬇️ Baixar CSV do Plano",
        export_plan.to_csv(index=False).encode("utf-8"),
        file_name=f"plano_{selected.lower()}.csv",
        mime="text/csv",
    )
    st.download_button(
        "⬇️ Baixar CSV dos Exercícios",
        export_ex.to_csv(index=False).encode("utf-8"),
        file_name=f"exercicios_{selected.lower()}.csv",
        mime="text/csv",
    )
