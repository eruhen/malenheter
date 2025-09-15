
# Målenheter – Streamlit øving (lengde/masse/volum)
# Kjør: streamlit run malenheter_trening.py
import random
from datetime import datetime, timedelta
import streamlit as st
import streamlit.components.v1 as components
from decimal import Decimal, getcontext

getcontext().prec = 28

# ---------------- Utilities ----------------
def fmt(n: Decimal) -> str:
    """Format Decimal with comma as decimal separator, no trailing zeros."""
    if n == n.to_integral():
        s = str(int(n))
    else:
        s = format(n, 'f').rstrip('0').rstrip('.')
    return s.replace('.', ',') if s else '0'

def parse_user(s: str) -> Decimal:
    """Parse user input that may use comma or dot as decimal separator."""
    s = s.strip().replace(' ', '').replace(',', '.')
    return Decimal(s)

def pow10(exp: int) -> Decimal:
    if exp >= 0:
        return Decimal(10) ** exp
    else:
        # negative exponent
        return Decimal(1) / (Decimal(10) ** (-exp))

# ---------------- Domain ----------------
UNITS = {
    "Lengde": ["mm","cm","dm","m","dam","hm","km"],
    "Masse":  ["mg","g","kg","tonn"],
    "Volum":  ["ml","cl","dl","l"]
}

# exponents relative to a base unit for each category (SI-ish progression)
EXPONENTS = {
    "Lengde": {"mm": -3, "cm": -2, "dm": -1, "m": 0, "dam": 1, "hm": 2, "km": 3},
    "Masse":  {"mg": -3, "g": 0, "kg": 3, "tonn": 6},
    "Volum":  {"ml": -3, "cl": -2, "dl": -1, "l": 0},
}

def random_value(difficulty: str) -> Decimal:
    """Generate a random starting value, with option for integers/decimals/blended."""
    if difficulty == "Hele tall":
        n = Decimal(random.randint(1, 9999))
    elif difficulty == "Desimaltall":
        whole = random.randint(0, 999)
        frac_places = random.choice([1,2,3])
        frac = random.randint(1, 9*(10**(frac_places-1)))
        n = Decimal(f"{whole}.{str(frac).zfill(frac_places)}")
        if random.random() < 0.2:
            # sometimes less than 1
            n = Decimal(f"0.{str(random.randint(1,999)).zfill(random.choice([1,2,3]))}")
    else:
        # Blandet
        if random.random() < 0.5:
            return random_value("Hele tall")
        else:
            return random_value("Desimaltall")
    return n

def build_conversion_task(category: str, allowed_units: list[str], difficulty: str):
    """Build a single conversion task within a category and allowed units."""
    units = [u for u in UNITS[category] if u in allowed_units] if allowed_units else UNITS[category]
    if len(units) < 2:
        units = UNITS[category]
    u_from, u_to = random.sample(units, 2)
    value = random_value(difficulty)
    exp_from = EXPONENTS[category][u_from]
    exp_to = EXPONENTS[category][u_to]
    exp_diff = exp_to - exp_from  # multiply by 10^exp_diff
    correct = value * pow10(exp_diff)
    text = f"Konverter: {fmt(value)} {u_from} → {u_to} = ?"
    return text, correct

# ---------------- State helpers ----------------
def queue_new_task():
    st.session_state['spawn_new_task'] = True

def reset_session():
    st.session_state.correct_count = 0
    st.session_state.tried = 0
    st.session_state.finished = False
    st.session_state.last_feedback = None
    st.session_state.focus_answer = True
    st.session_state.ignore_change = False
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

# ---------------- App ----------------
st.set_page_config(page_title="Målenheter – trening", page_icon="📏")
st.title("Trening på målenheter (SI)")

with st.sidebar:
    st.header("Innstillinger")
    st.session_state.mode = st.selectbox("Øktmodus", ["Antall oppgaver", "Tid"], index=0)
    category = st.selectbox("Kategori", list(UNITS.keys()), index=0)
    # Unit filters per category
    all_units = UNITS[category]
    default_units = all_units  # preselect all
    chosen_units = st.multiselect("Tillatte enheter", all_units, default=default_units, key="unit_sel")
    st.session_state.unit_sel = chosen_units or all_units

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
        st.session_state.category = category
        reset_session()

# Init defaults
for key, default in [
    ("task_text", None), ("correct", Decimal(0)), ("answer", ""),
    ("finished", False), ("correct_count", 0), ("tried", 0),
    ("last_feedback", None), ("focus_answer", False),
    ("spawn_new_task", False), ("ignore_change", False),
    ("category", "Lengde")
]:
    if key not in st.session_state:
        st.session_state[key] = default

# If category changed outside reset, still accept
st.session_state.category = st.session_state.get("category", category)

# Process queued new task BEFORE UI
if st.session_state.spawn_new_task:
    text, correct = build_conversion_task(
        st.session_state.category,
        st.session_state.unit_sel,
        st.session_state.difficulty
    )
    st.session_state.task_text = text
    st.session_state.correct = correct
    st.session_state['ignore_change'] = True  # suppress on_change once
    st.session_state.answer = ""
    st.session_state.spawn_new_task = False
    st.session_state.focus_answer = True

if st.session_state.task_text is None:
    text, correct = build_conversion_task(
        category,
        st.session_state.get("unit_sel", UNITS[category]),
        st.session_state.difficulty
    )
    st.session_state.task_text = text
    st.session_state.correct = correct

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
    # Show last feedback
    if st.session_state.last_feedback == "correct":
        st.success("Riktig! ✅")
    elif st.session_state.last_feedback == "wrong":
        st.error("Feil. Prøv igjen.")
    elif st.session_state.last_feedback == "parse_error":
        st.warning("Kunne ikke tolke svaret. Bruk tall med komma eller punktum.")

    # Big task text
    st.markdown(
        f"<div style='font-size:30px; font-weight:700; margin: 10px 0 20px 0;'>{st.session_state.task_text}</div>",
        unsafe_allow_html=True
    )

    # Check/submit logic
    def submit_answer():
        # Suppress on_change caused by programmatic clears
        if st.session_state.get('ignore_change', False):
            st.session_state['ignore_change'] = False
            return

        s = st.session_state.get('answer', '')
        try:
            u = parse_user(s)
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

    st.text_input("Svar (bruk komma eller punktum):", key="answer", on_change=submit_answer)

    colA, colB = st.columns([1,1])
    with colA:
        if st.button("Sjekk svar", type="primary", use_container_width=True, key="check_btn"):
            submit_answer()
    with colB:
        if st.button("Ny oppgave", use_container_width=True, key="new_task_btn"):
            queue_new_task()

# Focus back to input
if st.session_state.get("focus_answer", False):
    focus_answer_input()
    st.session_state["focus_answer"] = False

st.caption("Skriv svaret i riktig enhet. Desimaltall kan skrives med komma eller punktum.")
