
# Målenheter – Streamlit øving (lengde/masse/volum)
# Endringer i denne versjonen:
# - FIKS: Form leser SVARET fra session_state['answer_input'] (stabilt ved første Enter)
# - Tømmer answer_input når ny oppgave lages (ingen on_change brukt, så trygt)
# - Riktig konverteringsretning, fasit som tall, stabil kategori/bytte, standard Lengde
# Kjør: streamlit run malenheter_trening.py

import random
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
from decimal import Decimal, getcontext

getcontext().prec = 28

# ---------- Utilities ----------
def fmt(n: Decimal) -> str:
    if n == n.to_integral():
        s = str(int(n))
    else:
        s = format(n, 'f').rstrip('0').rstrip('.')
    return s.replace('.', ',') if s else '0'

def parse_user(s: str) -> Decimal:
    s = (s or "").strip().replace(' ', '').replace(',', '.')
    if s == "":
        raise ValueError("empty")
    return Decimal(s)

def pow10(exp: int) -> Decimal:
    return (Decimal(10) ** exp) if exp >= 0 else (Decimal(1) / (Decimal(10) ** (-exp)))

# ---------- Domain ----------
UNITS = {
    "Lengde": ["mm","cm","dm","m","km"],          # dam, hm fjernet
    "Masse":  ["mg","g","hg","kg","tonn"],        # hg lagt til
    "Volum":  ["ml","cl","dl","l"]
}

EXPONENTS = {
    "Lengde": {"mm": -3, "cm": -2, "dm": -1, "m": 0, "km": 3},
    "Masse":  {"mg": -3, "g": 0, "hg": 2, "kg": 3, "tonn": 6},
    "Volum":  {"ml": -3, "cl": -2, "dl": -1, "l": 0},
}

def random_value(difficulty: str) -> Decimal:
    if difficulty == "Hele tall":
        return Decimal(random.randint(1, 9999))
    elif difficulty == "Desimaltall":
        whole = random.randint(0, 999)
        frac_places = random.choice([1,2,3])
        frac = random.randint(1, 9*(10**(frac_places-1)))
        n = Decimal(f"{whole}.{str(frac).zfill(frac_places)}")
        if random.random() < 0.2:
            n = Decimal(f"0.{str(random.randint(1,999)).zfill(random.choice([1,2,3]))}")
        return n
    else:  # Blandet
        return random_value("Hele tall") if random.random() < 0.5 else random_value("Desimaltall")

def build_conversion_task(category: str, allowed_units, difficulty: str):
    units = [u for u in UNITS[category] if not allowed_units or u in allowed_units]
    if len(units) < 2:
        units = UNITS[category]
    u_from, u_to = random.sample(units, 2)
    value = random_value(difficulty)
    exp_from = EXPONENTS[category][u_from]
    exp_to = EXPONENTS[category][u_to]
    # Riktig retning: fra -> til = * 10^(exp_from - exp_to)
    exp_diff = exp_from - exp_to
    correct = value * pow10(exp_diff)
    text = f"Konverter: {fmt(value)} {u_from} → {u_to} = ?"
    return text, correct, u_from, u_to, value

# ---------- State helpers ----------
def queue_new_task():
    st.session_state['spawn_new_task'] = True

def reset_session():
    st.session_state.correct_count = 0
    st.session_state.tried = 0
    st.session_state.finished = False
    st.session_state.last_feedback = None
    st.session_state.focus_answer = True
    mode = st.session_state.get("mode", "Antall oppgaver")
    if mode == "Antall oppgaver":
        st.session_state.remaining = st.session_state.get("qcount", 20)
        st.session_state.pop("end_time", None)
    else:
        minutes = st.session_state.get("minutes", 2)
        st.session_state.end_time = (datetime.utcnow() + timedelta(minutes=minutes)).timestamp()
        st.session_state.pop("remaining", None)
    queue_new_task()

def focus_answer_input():
    components.html(
        """
        <script>
        const tryFocus = () => {
          const appRoot = window.parent.document.querySelector('section.main');
          if (!appRoot) return;
          const inputs = appRoot.querySelectorAll('input[type="text"]');
          if (inputs.length > 0) {
            inputs[0].focus();
            inputs[0].select && inputs[0].select();
          }
        };
        setTimeout(tryFocus, 50);
        </script>
        """, height=0
    )

# ---------- App ----------
st.set_page_config(page_title="Målenheter – trening", page_icon="📏")
st.title("Trening på målenheter (SI)")

DEFAULT_CATEGORY = "Lengde"

with st.sidebar:
    st.header("Innstillinger")
    st.session_state.mode = st.selectbox("Øktmodus", ["Antall oppgaver", "Tid"], index=0)

    if "category" not in st.session_state:
        st.session_state.category = DEFAULT_CATEGORY
    category = st.selectbox(
        "Kategori",
        list(UNITS.keys()),
        index=list(UNITS.keys()).index(st.session_state.category)
    )
    st.session_state.category = category

    all_units = UNITS[category]
    units_key = f"unit_sel_{category}"
    remembered = st.session_state.get(units_key, all_units)
    safe_default = [u for u in remembered if u in all_units] or all_units
    st.multiselect("Tillatte enheter", all_units, default=safe_default, key=units_key)
    current_units = st.session_state.get(units_key, all_units) or all_units

    st.session_state.difficulty = st.selectbox("Talltype", ["Hele tall","Desimaltall","Blandet"], index=2, key="diff_sel")

    if st.session_state.mode == "Antall oppgaver":
        qcount = st.number_input("Antall oppgaver i økt", min_value=1, max_value=200, value=20, step=1, key="qcount")
        if "remaining" not in st.session_state:
            st.session_state.remaining = qcount
    else:
        minutes = st.number_input("Varighet (minutter)", min_value=1, max_value=60, value=2, step=1, key="minutes")
        if "end_time" not in st.session_state:
            st.session_state.end_time = (datetime.utcnow() + timedelta(minutes=minutes)).timestamp()

    if st.button("Start/Nullstill økt", key="reset_btn"):
        reset_session()

# Init defaults
for key, default in [
    ("task_text", None), ("correct", Decimal(0)),
    ("from_unit", None), ("to_unit", None), ("start_value", None),
    ("finished", False), ("correct_count", 0), ("tried", 0),
    ("last_feedback", None), ("focus_answer", False),
    ("spawn_new_task", False)
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Queue processing BEFORE UI
if st.session_state.spawn_new_task:
    text, correct, u_from, u_to, v = build_conversion_task(
        st.session_state.category,
        current_units,
        st.session_state.difficulty
    )
    st.session_state.task_text = text
    st.session_state.correct = correct
    st.session_state.from_unit = u_from
    st.session_state.to_unit = u_to
    st.session_state.start_value = v
    st.session_state.spawn_new_task = False
    # Tøm input trygt (ingen on_change i bruk)
    st.session_state['answer_input'] = ""
    st.session_state.focus_answer = True

# First task
if st.session_state.task_text is None:
    text, correct, u_from, u_to, v = build_conversion_task(
        st.session_state.category,
        current_units,
        st.session_state.difficulty
    )
    st.session_state.task_text = text
    st.session_state.correct = correct
    st.session_state.from_unit = u_from
    st.session_state.to_unit = u_to
    st.session_state.start_value = v
    st.session_state['answer_input'] = ""

# Header metrics
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Riktige", st.session_state.get("correct_count", 0))
with col2:
    st.metric("Forsøkt", st.session_state.get("tried", 0))
with col3:
    if st.session_state.mode == "Antall oppgaver":
        st.metric("Igjen", st.session_state.get("remaining", 0))
    else:
        end_ts = st.session_state.get("end_time", None)
        tl = max(0, int(end_ts - datetime.utcnow().timestamp())) if end_ts else 0
        m, s = divmod(tl, 60)
        st.metric("Tid igjen", f"{m:02d}:{s:02d}")

st.divider()

# End conditions
if st.session_state.mode == "Tid":
    end_ts = st.session_state.get("end_time", None)
    if end_ts is not None and datetime.utcnow().timestamp() >= end_ts:
        st.session_state.finished = True

if st.session_state.get("finished", False) or (
    st.session_state.mode == "Antall oppgaver" and st.session_state.get("remaining", 0) == 0
):
    st.session_state.finished = True
    tried = st.session_state.get("tried", 0)
    correct = st.session_state.get("correct_count", 0)
    pct = int(round((100*correct/tried),0)) if tried else 0
    if tried > 0 and correct == tried:
        st.balloons()
        st.success(f"🎉 Perfekt økt! {correct} av {tried} (100%).")
    else:
        st.success(f"Økten er ferdig. Resultat: {correct} riktige av {tried} (≈ {pct}%).")
    st.button("Start ny økt", type="primary", on_click=reset_session, use_container_width=True)

else:
    # Feedback
    if st.session_state.last_feedback == "correct":
        st.success("Riktig! ✅")
    elif st.session_state.last_feedback == "wrong":
        st.error(f"Feil. Riktig svar er **{fmt(st.session_state.correct)}**.")
    elif st.session_state.last_feedback == "parse_error":
        st.warning("Kunne ikke tolke tallet. Bruk komma eller punktum.")

    # Task text
    st.markdown(
        f"<div style='font-size:30px; font-weight:700; margin: 10px 0 20px 0;'>{st.session_state.task_text}</div>",
        unsafe_allow_html=True
    )

    # --- Form: bruk en nøkkel, les fra session_state ETTER submit ---
    with st.form("answer_form", clear_on_submit=False):
        st.text_input("Svar (skriv bare tallet):", key="answer_input", placeholder="Skriv svaret her")
        submitted = st.form_submit_button("Sjekk svar", use_container_width=True)

    def evaluate_current_answer():
        val_str = st.session_state.get('answer_input', '')
        try:
            u = parse_user(val_str)
        except Exception:
            st.session_state.last_feedback = "parse_error"
            st.session_state.focus_answer = True
            return

        st.session_state.tried += 1
        if u == st.session_state.correct:
            st.session_state.correct_count += 1
            st.session_state.last_feedback = "correct"
            if st.session_state.get("mode","Antall oppgaver") == "Antall oppgaver":
                st.session_state.remaining = max(0, st.session_state.get("remaining", 0) - 1)
                if st.session_state.remaining == 0:
                    st.session_state.finished = True
            queue_new_task()
        else:
            st.session_state.last_feedback = "wrong"
            st.session_state.focus_answer = True

    if submitted:
        evaluate_current_answer()

    # Ny oppgave-knapp
    if st.button("Ny oppgave", use_container_width=True, key="new_task_btn"):
        queue_new_task()

# Fokus på input etter behov
if st.session_state.get("focus_answer", False):
    focus_answer_input()
    st.session_state["focus_answer"] = False

st.caption("Skriv bare tallet. Du kan bruke komma eller punktum som desimaltegn.")
