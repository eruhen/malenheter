
# Målenheter – Streamlit øving (forenklet diagnoseversjon) – FIX
# Endringer:
# - Bruker ÉN widget-state: key="answer_input" på text_input
# - Leser alltid verdien fra st.session_state['answer_input'] ved evaluering
# - Ingen manuell setting av answer_input fra return-verdien (unngår racing)
#
# Kjør: streamlit run malenheter_trening_simple.py

import random
from decimal import Decimal, getcontext
import streamlit as st
import streamlit.components.v1 as components

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

# ---------- Domain (kun lengde) ----------
UNITS = ["mm","cm","dm","m","km"]
EXP = {"mm": -3, "cm": -2, "dm": -1, "m": 0, "km": 3}

def random_value() -> Decimal:
    if random.random() < 0.5:
        return Decimal(random.randint(1, 9999))
    whole = random.randint(0, 999)
    frac_places = random.choice([1,2,3])
    frac = random.randint(1, 9*(10**(frac_places-1)))
    n = Decimal(f"{whole}.{str(frac).zfill(frac_places)}")
    if random.random() < 0.2:
        n = Decimal(f"0.{str(random.randint(1,999)).zfill(random.choice([1,2,3]))}")
    return n

def new_task():
    u_from, u_to = random.sample(UNITS, 2)
    value = random_value()
    exp_diff = EXP[u_from] - EXP[u_to]  # riktig retning
    correct = value * pow10(exp_diff)
    st.session_state.task_text = f"Konverter: {fmt(value)} {u_from} → {u_to} = ?"
    st.session_state.correct = correct
    st.session_state.last_feedback = None
    # Tøm input FØR neste visning
    st.session_state['answer_input'] = ""

def reset_session():
    st.session_state.total = 10
    st.session_state.remaining = st.session_state.total
    st.session_state.tried = 0
    st.session_state.correct_count = 0
    st.session_state.finished = False
    st.session_state.last_feedback = None
    st.session_state['answer_input'] = ""
    new_task()

# ---------- App ----------
st.set_page_config(page_title="Målenheter – enkel øving", page_icon="📏")
st.title("Trening på målenheter (lengde) – enkel testversjon")

# Init state
for key, default in [
    ("total", 10), ("remaining", 10), ("tried", 0), ("correct_count", 0),
    ("finished", False), ("task_text", None), ("correct", Decimal(0)),
    ("answer_input", ""), ("last_feedback", None)
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Første oppgave
if st.session_state.task_text is None:
    reset_session()

# Header metrics
col1, col2, col3 = st.columns(3)
with col1: st.metric("Riktige", st.session_state.correct_count)
with col2: st.metric("Forsøkt", st.session_state.tried)
with col3: st.metric("Igjen", st.session_state.remaining)

st.divider()

# Slutt
if st.session_state.finished or st.session_state.remaining == 0:
    st.session_state.finished = True
    if st.session_state.tried > 0 and st.session_state.correct_count == st.session_state.tried:
        st.balloons()
        st.success(f"🎉 Perfekt! {st.session_state.correct_count} av {st.session_state.tried} (100%).")
    else:
        pct = int(round(100*st.session_state.correct_count/max(1,st.session_state.tried)))
        st.success(f"Ferdig! Resultat: {st.session_state.correct_count} av {st.session_state.tried} (≈ {pct}%).")
    if st.button("Start ny økt (10 oppgaver)", type="primary", use_container_width=True):
        reset_session()

else:
    # Feedback
    if st.session_state.last_feedback == "correct":
        st.success("Riktig! ✅")
    elif st.session_state.last_feedback == "wrong":
        st.error(f"Feil. Riktig svar er **{fmt(st.session_state.correct)}**.")
    elif st.session_state.last_feedback == "parse_error":
        st.warning("Kunne ikke tolke tallet. Bruk komma eller punktum.")

    # Oppgave
    st.markdown(
        f"<div style='font-size:34px; font-weight:700; margin: 10px 0 20px 0;'>{st.session_state.task_text}</div>",
        unsafe_allow_html=True
    )

    # Input – ÉN sann kilde: key="answer_input"
    st.text_input("Svar (skriv bare tallet):", key="answer_input")

    # Evalueringsfunksjon
    def evaluate():
        txt = st.session_state.get("answer_input","")
        try:
            val = parse_user(txt)
        except Exception:
            st.session_state.last_feedback = "parse_error"
            return

        st.session_state.tried += 1
        if val == st.session_state.correct:
            st.session_state.correct_count += 1
            st.session_state.last_feedback = "correct"
            st.session_state.remaining = max(0, st.session_state.remaining - 1)
            if st.session_state.remaining == 0:
                st.session_state.finished = True
            else:
                new_task()
        else:
            st.session_state.last_feedback = "wrong"

    # Knapper
    colA, colB = st.columns([1,1])
    with colA:
        if st.button("Sjekk svar", type="primary", use_container_width=True):
            evaluate()
    with colB:
        if st.button("Ny oppgave", use_container_width=True):
            new_task()

    # JS: Enter i input klikker "Sjekk svar"
    components.html(
        """
        <script>
        (function() {
          const root = window.parent.document;
          function bind() {
            // Finn input via label-tekst
            const labels = [...root.querySelectorAll('label')];
            const lab = labels.find(l => l.textContent.trim().startsWith('Svar (skriv bare tallet)'));
            if (!lab) { setTimeout(bind, 120); return; }
            // Input er neste/relatert element
            const input = lab.parentElement.querySelector('input[type="text"]') || root.querySelector('input[type="text"]');
            const buttons = [...root.querySelectorAll('button')];
            const checkBtn = buttons.find(b => b.innerText.trim() === "Sjekk svar");
            if (!input || !checkBtn) { setTimeout(bind, 120); return; }
            input.addEventListener('keydown', function(e) {
              if (e.key === 'Enter') {
                e.preventDefault();
                checkBtn.click();
              }
            }, { once: false });
          }
          setTimeout(bind, 200);
        })();
        </script>
        """, height=0
    )
