
# Målenheter – Streamlit øving (ENKEL OG STABIL — form-basert)
# Mål: Løse Enter/verdilagring-race helt.
# - Kun LENGDE (mm, cm, dm, m, km)
# - 10 oppgaver per økt (fast)
# - Hver oppgave rendres i EGEN FORM med unik nøkkel (form_{qid})
# - Enter/«Sjekk svar» sender inn formen; vi leser verdien fra formens input-key
# - Vi rydder IKKE i widget-verdier programmatisk; ny oppgave = ny qid = nytt inputfelt
#
# Kjør: streamlit run malenheter_trening_stabil.py

import random
from decimal import Decimal, getcontext
import streamlit as st

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
EXP   = {"mm": -3, "cm": -2, "dm": -1, "m": 0, "km": 3}

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

def make_task():
    """Returnerer (u_from, u_to, value, correct, text)."""
    u_from, u_to = random.sample(UNITS, 2)
    value = random_value()
    exp_diff = EXP[u_from] - EXP[u_to]  # riktig retning (fra -> til)
    correct = value * pow10(exp_diff)
    text = f"Konverter: {fmt(value)} {u_from} → {u_to} = ?"
    return u_from, u_to, value, correct, text

# ---------- Init state ----------
st.set_page_config(page_title="Målenheter – stabil øving", page_icon="📏")
st.title("Trening på målenheter (lengde) – stabil versjon")

defaults = {
    "qid": 0,
    "total": 10,
    "remaining": 10,
    "tried": 0,
    "correct_count": 0,
    "finished": False,
    "task_text": None,
    "correct": Decimal(0),
    "last_feedback": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def new_task():
    st.session_state["qid"] += 1
    u_from, u_to, value, correct, text = make_task()
    st.session_state["task_text"] = text
    st.session_state["correct"] = correct
    st.session_state["last_feedback"] = None

def reset_session():
    st.session_state["qid"] = 0
    st.session_state["total"] = 10
    st.session_state["remaining"] = 10
    st.session_state["tried"] = 0
    st.session_state["correct_count"] = 0
    st.session_state["finished"] = False
    st.session_state["last_feedback"] = None
    new_task()

if st.session_state["task_text"] is None:
    reset_session()

# ---------- Header ----------
c1, c2, c3 = st.columns(3)
with c1: st.metric("Riktige", st.session_state["correct_count"])
with c2: st.metric("Forsøkt", st.session_state["tried"])
with c3: st.metric("Igjen",   st.session_state["remaining"])

st.divider()

# ---------- End state ----------
if st.session_state["finished"] or st.session_state["remaining"] == 0:
    st.session_state["finished"] = True
    tried, corr = st.session_state["tried"], st.session_state["correct_count"]
    if tried > 0 and corr == tried:
        st.balloons()
        st.success(f"🎉 Perfekt! {corr} av {tried} (100%).")
    else:
        pct = int(round(100*corr/max(1, tried)))
        st.success(f"Ferdig! Resultat: {corr} av {tried} (≈ {pct}%).")
    if st.button("Start ny økt (10 oppgaver)", type="primary", use_container_width=True):
        reset_session()

else:
    # Feedback
    fb = st.session_state["last_feedback"]
    if fb == "correct":
        st.success("Riktig! ✅")
    elif fb == "wrong":
        st.error(f"Feil. Riktig svar er **{fmt(st.session_state['correct'])}**.")
    elif fb == "parse_error":
        st.warning("Kunne ikke tolke tallet. Bruk komma eller punktum.")

    # Oppgave
    st.markdown(
        f"<div style='font-size:34px; font-weight:700; margin: 10px 0 20px 0;'>{st.session_state['task_text']}</div>",
        unsafe_allow_html=True
    )

    # --- EN form per oppgave ---
    form_key = f"form_{st.session_state['qid']}"
    answer_key = f"answer_{st.session_state['qid']}"
    with st.form(form_key, clear_on_submit=False):
        st.text_input("Svar (skriv bare tallet):", key=answer_key)
        submitted = st.form_submit_button("Sjekk svar", use_container_width=True)

    if submitted:
        raw = st.session_state.get(answer_key, "")
        try:
            u = parse_user(raw)
        except Exception:
            st.session_state["last_feedback"] = "parse_error"
        else:
            st.session_state["tried"] += 1
            if u == st.session_state["correct"]:
                st.session_state["correct_count"] += 1
                st.session_state["last_feedback"] = "correct"
                st.session_state["remaining"] = max(0, st.session_state["remaining"] - 1)
                if st.session_state["remaining"] == 0:
                    st.session_state["finished"] = True
                else:
                    new_task()
            else:
                st.session_state["last_feedback"] = "wrong"

    # «Ny oppgave»-knapp (frivillig hopp over)
    if st.button("Ny oppgave", use_container_width=True):
        new_task()
