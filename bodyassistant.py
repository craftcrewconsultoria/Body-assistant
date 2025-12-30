# app.py
import streamlit as st
import pandas as pd
from dataclasses import dataclass

st.set_page_config(page_title="Calculadora de Calorias - Vitor & Thayná", layout="wide")

# -----------------------------
# Perfis
# -----------------------------
@dataclass
class Profile:
    name: str
    age: int
    weight_kg: float
    sex: str  # "M" or "F"
    deficit_kcal: int
    default_height_cm: int
    default_activity_factor: float

PROFILES = {
    "Vitor": Profile(
        name="Vitor",
        age=35,
        weight_kg=97.0,
        sex="M",
        deficit_kcal=900,
        default_height_cm=180,
        default_activity_factor=1.45,  # leve/moderado
    ),
    "Thayná": Profile(
        name="Thayná",
        age=32,
        weight_kg=63.0,
        sex="F",
        deficit_kcal=500,
        default_height_cm=165,
        default_activity_factor=1.40,  # leve/moderado
    ),
}

DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MEALS = ["Café", "Lanche AM", "Almoço", "Lanche PM", "Jantar", "Ceia"]


# -----------------------------
# Helpers de cálculo
# -----------------------------
def mifflin_st_jeor_bmr(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    # BMR (kcal/dia)
    # Homem: 10W + 6.25H - 5A + 5
    # Mulher: 10W + 6.25H - 5A - 161
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + (5 if sex.upper() == "M" else -161)


def tdee(bmr: float, activity_factor: float) -> float:
    return bmr * activity_factor


def kcal_running(weight_kg: float, distance_km: float) -> float:
    # Regra de bolso bem usada: ~1 kcal/kg/km (corrida)
    return max(0.0, weight_kg * max(0.0, distance_km))


def kcal_training_from_met(weight_kg: float, minutes: float, met: float) -> float:
    # kcal = MET * 3.5 * peso(kg) / 200 * minutos
    minutes = max(0.0, minutes)
    met = max(0.0, met)
    return met * 3.5 * weight_kg / 200.0 * minutes


def clamp_int(x, lo=0, hi=20000):
    try:
        v = int(x)
    except Exception:
        v = 0
    return max(lo, min(hi, v))


def init_week_plan() -> pd.DataFrame:
    rows = []
    for d in DAYS:
        for m in MEALS:
            rows.append({"Dia": d, "Refeição": m, "Descrição": "", "Calorias (kcal)": 0})
    return pd.DataFrame(rows)


# -----------------------------
# Estado
# -----------------------------
if "plans" not in st.session_state:
    st.session_state.plans = {p: init_week_plan() for p in PROFILES.keys()}

if "exercise" not in st.session_state:
    # por perfil, por dia
    st.session_state.exercise = {
        p: pd.DataFrame(
            [{"Dia": d, "Corrida (km)": 0.0, "Treino (min)": 0.0, "MET treino": 6.0} for d in DAYS]
        )
        for p in PROFILES.keys()
    }

# -----------------------------
# UI
# -----------------------------
st.title("📊 Calculadora de Calorias — Plano Semanal (Vitor & Thayná)")

colA, colB, colC = st.columns([1.2, 1, 1])

with colA:
    selected = st.selectbox("Quem está preenchendo?", list(PROFILES.keys()))
    prof = PROFILES[selected]

with colB:
    st.write("**Perfil (editável no app):**")
    weight_kg = st.number_input("Peso (kg)", min_value=30.0, max_value=250.0, value=float(prof.weight_kg), step=0.1)
    height_cm = st.number_input("Altura (cm)", min_value=130, max_value=220, value=int(prof.default_height_cm), step=1)
    age = st.number_input("Idade (anos)", min_value=10, max_value=90, value=int(prof.age), step=1)

with colC:
    st.write("**Parâmetros de gasto:**")
    sex = st.selectbox("Sexo (para estimar BMR)", ["M", "F"], index=0 if prof.sex == "M" else 1)
    activity_factor = st.selectbox(
        "Fator de atividade (TDEE)",
        options=[1.2, 1.375, 1.45, 1.55, 1.725, 1.9],
        index=[1.2, 1.375, 1.45, 1.55, 1.725, 1.9].index(prof.default_activity_factor)
        if prof.default_activity_factor in [1.2, 1.375, 1.45, 1.55, 1.725, 1.9]
        else 2,
        help="1.2 sedentário | 1.375 leve | 1.45 leve/moderado | 1.55 moderado | 1.725 alto | 1.9 muito alto",
    )
    deficit = st.number_input(
        "Déficit diário (kcal)",
        min_value=0,
        max_value=2000,
        value=int(prof.deficit_kcal),
        step=50,
        help="Vitor: 900 | Thayná: 500 (você pode ajustar se quiser)",
    )

st.divider()

# Cálculos base
bmr = mifflin_st_jeor_bmr(sex, weight_kg, height_cm, age)
maintenance = tdee(bmr, float(activity_factor))
target_intake = max(0.0, maintenance - deficit)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("BMR estimado (kcal/dia)", f"{bmr:,.0f}".replace(",", "."))
kpi2.metric("Manutenção estimada (kcal/dia)", f"{maintenance:,.0f}".replace(",", "."))
kpi3.metric("Meta com déficit (kcal/dia)", f"{target_intake:,.0f}".replace(",", "."))
kpi4.metric("Déficit configurado (kcal/dia)", f"{deficit}")

st.caption(
    "As estimativas de gasto (BMR/TDEE e exercício) são aproximadas e servem para controle/planejamento."
)

# -----------------------------
# Exercício (por dia)
# -----------------------------
st.subheader("🏃‍♂️ Exercícios (por dia da semana)")
ex_df = st.session_state.exercise[selected].copy()

ex_edited = st.data_editor(
    ex_df,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "Dia": st.column_config.TextColumn(disabled=True),
        "Corrida (km)": st.column_config.NumberColumn(min_value=0.0, max_value=200.0, step=0.1),
        "Treino (min)": st.column_config.NumberColumn(min_value=0.0, max_value=600.0, step=5.0),
        "MET treino": st.column_config.NumberColumn(min_value=1.0, max_value=15.0, step=0.5),
    },
    key=f"ex_editor_{selected}",
)

# Persist
st.session_state.exercise[selected] = ex_edited

# calcula gasto por dia
ex_edited["Gasto corrida (kcal)"] = ex_edited["Corrida (km)"].apply(lambda km: kcal_running(weight_kg, float(km)))
ex_edited["Gasto treino (kcal)"] = ex_edited.apply(
    lambda r: kcal_training_from_met(weight_kg, float(r["Treino (min)"]), float(r["MET treino"])),
    axis=1,
)
ex_edited["Gasto total exercício (kcal)"] = ex_edited["Gasto corrida (kcal)"] + ex_edited["Gasto treino (kcal)"]

st.dataframe(
    ex_edited[["Dia", "Gasto corrida (kcal)", "Gasto treino (kcal)", "Gasto total exercício (kcal)"]],
    use_container_width=True,
)

st.divider()

# -----------------------------
# Plano alimentar semanal
# -----------------------------
st.subheader("🍽️ Plano alimentar semanal (editável)")
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

# Persist
plan_edited["Calorias (kcal)"] = plan_edited["Calorias (kcal)"].apply(lambda v: clamp_int(v, 0, 20000))
st.session_state.plans[selected] = plan_edited

# -----------------------------
# Resumo por dia
# -----------------------------
st.subheader("📈 Resumo por dia")
daily_intake = (
    plan_edited.groupby("Dia", as_index=False)["Calorias (kcal)"]
    .sum()
    .rename(columns={"Calorias (kcal)": "Ingestão (kcal)"})
)

daily = daily_intake.merge(ex_edited[["Dia", "Gasto total exercício (kcal)"]], on="Dia", how="left")
daily["Gasto total exercício (kcal)"] = daily["Gasto total exercício (kcal)"].fillna(0.0)

# Se você quer "meta líquida" (considerando exercício), some o exercício à meta
daily["Meta (kcal)"] = target_intake
daily["Meta + exercício (kcal)"] = daily["Meta (kcal)"] + daily["Gasto total exercício (kcal)"]
daily["Saldo vs Meta+exercício (kcal)"] = daily["Meta + exercício (kcal)"] - daily["Ingestão (kcal)"]

st.dataframe(
    daily[["Dia", "Ingestão (kcal)", "Gasto total exercício (kcal)", "Meta (kcal)", "Meta + exercício (kcal)", "Saldo vs Meta+exercício (kcal)"]],
    use_container_width=True,
)

# KPIs semana
st.subheader("🧾 Semana (totais)")
week_total_intake = float(daily["Ingestão (kcal)"].sum())
week_total_ex = float(daily["Gasto total exercício (kcal)"].sum())
week_target = float(target_intake * 7)
week_target_plus_ex = float(daily["Meta + exercício (kcal)"].sum())
week_balance = float(week_target_plus_ex - week_total_intake)

w1, w2, w3, w4 = st.columns(4)
w1.metric("Ingestão semanal (kcal)", f"{week_total_intake:,.0f}".replace(",", "."))
w2.metric("Exercício semanal (kcal)", f"{week_total_ex:,.0f}".replace(",", "."))
w3.metric("Meta semanal (kcal)", f"{week_target:,.0f}".replace(",", "."))
w4.metric("Saldo semanal vs Meta+exercício", f"{week_balance:,.0f}".replace(",", "."))

st.divider()

# -----------------------------
# Ações: reset / export
# -----------------------------
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("🔄 Resetar plano (perfil atual)"):
        st.session_state.plans[selected] = init_week_plan()
        st.session_state.exercise[selected] = pd.DataFrame(
            [{"Dia": d, "Corrida (km)": 0.0, "Treino (min)": 0.0, "MET treino": 6.0} for d in DAYS]
        )
        st.rerun()

with col2:
    if st.button("📋 Copiar plano do outro perfil"):
        other = "Thayná" if selected == "Vitor" else "Vitor"
        st.session_state.plans[selected] = st.session_state.plans[other].copy()
        st.session_state.exercise[selected] = st.session_state.exercise[other].copy()
        st.rerun()

with col3:
    # Export simples em CSV (plano + exercício)
    export_plan = st.session_state.plans[selected].copy()
    export_ex = st.session_state.exercise[selected].copy()
    csv_plan = export_plan.to_csv(index=False).encode("utf-8")
    csv_ex = export_ex.to_csv(index=False).encode("utf-8")

    st.download_button("⬇️ Baixar CSV do Plano", csv_plan, file_name=f"plano_{selected.lower()}.csv", mime="text/csv")
    st.download_button("⬇️ Baixar CSV do Exercício", csv_ex, file_name=f"exercicio_{selected.lower()}.csv", mime="text/csv")
