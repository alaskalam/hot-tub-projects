import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
import streamlit as st

TASKS_SAVE_PATH = Path(__file__).resolve().parent / "saved_tasks.json"
SUPABASE_TABLE = "shared_board_tasks"

# Snowboard celebration overlay — swap for any direct image URL ("open in new tab" = just the photo).

SB_MOUNTAIN_BG_URL = (
    "https://raw.githubusercontent.com/alaskalam/hot-tub-projects/main/assets/killytrail.jpg"
    "?auto=format&fit=crop&w=1600&q=80"
)


def _supabase_credentials() -> Optional[Tuple[str, str]]:
    try:
        s = st.secrets
        url = (s.get("SUPABASE_URL") or "").strip()
        key = (s.get("SUPABASE_KEY") or "").strip()
    except Exception:
        return None
    if url and key:
        return url, key
    return None


def use_supabase() -> bool:
    return _supabase_credentials() is not None


def load_tasks_supabase() -> list:
    from supabase import create_client

    creds = _supabase_credentials()
    if not creds:
        return []
    url, key = creds
    try:
        client = create_client(url, key)
        res = (
            client.table(SUPABASE_TABLE)
            .select("id,task,assignee,due_date,done")
            .order("id")
            .execute()
        )
    except Exception as e:
        st.error(f"Could not load the shared board from Supabase: {e}")
        return []
    out = []
    for row in res.data or []:
        raw_due = row.get("due_date", "")
        if isinstance(raw_due, str):
            due = date.fromisoformat(raw_due[:10])
        else:
            due = pd.Timestamp(raw_due).date()
        out.append(
            {
                "Task": row.get("task") or "",
                "Assignee": row.get("assignee") or "",
                "Due Date": due,
                "Done": bool(row.get("done")),
            }
        )
    return out


def save_tasks_supabase(tasks: list) -> None:
    from supabase import create_client

    creds = _supabase_credentials()
    if not creds:
        return
    url, key = creds
    client = create_client(url, key)
    rows = []
    for i, t in enumerate(tasks):
        d = t.get("Due Date")
        if isinstance(d, datetime):
            due_s = d.date().isoformat()
        elif isinstance(d, date):
            due_s = d.isoformat()
        else:
            due_s = str(pd.Timestamp(d).date())
        rows.append(
            {
                "task": t.get("Task") or "",
                "assignee": t.get("Assignee") or "",
                "due_date": due_s,
                "done": bool(t.get("Done", False)),
            }
        )
    try:
        # Every row has position >= 0, so this clears the whole board.
        client.table(SUPABASE_TABLE).delete().gt("id", 0).execute()
        if rows:
            client.table(SUPABASE_TABLE).insert(rows).execute()
    except Exception as e:
        st.error(f"Could not save the shared board to Supabase: {e}")


def load_tasks(path: Path) -> list:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        rows = json.load(f)
    out = []
    for row in rows:
        r = dict(row)
        raw_due = r.get("Due Date", "")
        if isinstance(raw_due, str):
            r["Due Date"] = date.fromisoformat(raw_due[:10])
        else:
            r["Due Date"] = pd.Timestamp(raw_due).date()
        r["Done"] = bool(r.get("Done", False))
        out.append(r)
    return out


def save_tasks(path: Path, tasks: list) -> None:
    rows = []
    for t in tasks:
        r = dict(t)
        d = r.get("Due Date")
        if isinstance(d, datetime):
            r["Due Date"] = d.date().isoformat()
        elif isinstance(d, date):
            r["Due Date"] = d.isoformat()
        else:
            r["Due Date"] = str(pd.Timestamp(d).date())
        r["Done"] = bool(r.get("Done", False))
        rows.append(r)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)


def _rerun() -> None:
    """Streamlit 1.27+ has st.rerun(); older releases use st.experimental_rerun()."""
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
    else:
        st.experimental_rerun()


def _flash_hottub_emoji() -> None:
    """Hot tub image overlay for a couple seconds after a task is added."""
    splash_url = (
        "https://imgproxy.attic.sh/insecure/f:webp/h:1434/q:90/w:1434/plain/"
        "https://attic.sh/9sm6qi8g68mdx7ybkumio3ostdzz"
    )
    st.markdown(
        f"""
        <style>

        .htb-task-text {{
            margin-top: 20rem;
            text-align: center;
           
            font-size: clamp(1rem, 2vw, 1.4rem);
            font-weight: 700;
            letter-spacing: 0.03em;

            color: white;


            text-shadow:
                0 0 10px rgba(0,0,0,0.45),
                0 0 20px rgba(0,0,0,0.28);
            
        }}

        
        @keyframes hottub-task-added {{
            0% {{ transform: translate(-50%, -50%) scale(0); opacity: 0; }}
            14% {{ transform: translate(-50%, -50%) scale(1); opacity: 1; }}
            72% {{ transform: translate(-50%, -50%) scale(1); opacity: 1; }}
            100% {{ transform: translate(-50%, -50%) scale(0.25); opacity: 0; }}
        }}
        .htb-task-added-splash {{
            position: fixed;
            left: 50%;
            top: 30%;
            z-index: 100001;
            line-height: 0;
            pointer-events: none;
            user-select: none;
            animation: hottub-task-added 2.1s ease-in-out forwards;
            filter: drop-shadow(0 0.4rem 0.55rem rgba(0, 0, 0, 0.18));
        }}
        .htb-task-added-splash img {{
            display: block;
            width: min(42vw, 260px);
            height: auto;
        }}
        </style>
        <div class="htb-task-added-splash" aria-hidden="true">
          <img src="{splash_url}" alt="" />
        </div>
        <div class="htb-task-text">
            Get in. The hot tub's waiting.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _flash_snowboard_completion() -> None:
    """Full-screen mini scene: mountain + snowboarder when a task is marked completed."""
    _bg = SB_MOUNTAIN_BG_URL.replace("\\", "/")
    _html = """
        <style>
        @keyframes sb-scene-fade {
            0%, 72% { opacity: 1; }
            100% { opacity: 0; }
        }
        @keyframes sb-shred {
            0% { left: 6%; top: 16%; transform: rotate(-38deg) scale(0.85); }
            45% { left: 40%; top: 34%; transform: rotate(-8deg) scale(1); }
            100% { left: 74%; top: 50%; transform: rotate(22deg) scale(1); }
        }
        .sb-celebrate-wrap {
            position: fixed;
            inset: 0;
            z-index: 99990;
            pointer-events: none;
            animation: sb-scene-fade 2.7s ease forwards;
        }
        .sb-celebrate-sky {
            position: absolute;
            inset: 0;

            background-image:
                linear-gradient(
                    180deg,
                    rgba(60, 120, 190, 0.45) 0%,
                    rgba(120, 180, 240, 0.15) 100%
                ),
                url("https://www.killingtonzone.com/albums/album36/killington_1980s.sized.jpg");
            background-size: cover;
            background-position: center;
        }
        .sb-celebrate-mtn {
            position: absolute;
            left: -12%;
            right: -12%;
            bottom: 0;
            height: 72%;
            clip-path: polygon(
                0% 100%,
                5% 46%,
                26% 66%,
                50% 28%,
                74% 50%,
                93% 34%,
                100% 56%,
                100% 100%
            );
            background-image:
                linear-gradient(
                    168deg,
                    rgba(8, 22, 42, 0.72) 0%,
                    rgba(25, 55, 80, 0.25) 38%,
                    rgba(180, 215, 245, 0.4) 100%
                ),
                url("__MOUNTAIN_BG__");
            background-size: cover;
            background-position: center 55%;
            filter: saturate(1.12) contrast(1.08) brightness(1.03);
        }
        .sb-celebrate-snowline {
            position: absolute;
            left: 0;
            right: 0;
            bottom: 36%;
            height: 16%;
            background: linear-gradient(180deg, rgba(255,255,255,0.92) 0%, rgba(255,255,255,0) 100%);
            clip-path: polygon(0% 85%, 22% 38%, 52% 62%, 80% 32%, 100% 58%, 100% 100%, 0% 100%);
        }
        .sb-celebrate-rider {
            position: absolute;
            font-size: clamp(2.4rem, 7.5vw, 3.4rem);
            line-height: 1;
            filter: drop-shadow(0 0.25rem 0.4rem rgba(0,0,0,0.35));
            animation: sb-shred 2.1s cubic-bezier(0.33, 0, 0.15, 1) forwards;
        }
        </style>
        <div class="sb-celebrate-wrap" aria-hidden="true">
            <div class="sb-celebrate-sky"></div>
            <div class="sb-celebrate-mtn"></div>
            <div class="sb-celebrate-snowline"></div>
            <div class="sb-celebrate-rider">🏂</div>
        </div>
    """
    st.markdown(_html.replace("__MOUNTAIN_BG__", _bg), unsafe_allow_html=True)


st.set_page_config(page_title="Snowboard Project Tracker", layout="wide")

# --- TITLE ---
st.title("🏂 🏂 Ski Lodge Task Board")
st.caption("Only those who are willing to go too far can possibly see how far one can go.")

# --- PROJECT TITLE ---
project_title = st.text_input(
    "Project Board Title",
    placeholder="Example: Peace Out Website Redesign"
)

# --- SESSION STATE ---
if "tasks" not in st.session_state:
    if use_supabase():
        st.session_state.tasks = load_tasks_supabase()
    else:
        st.session_state.tasks = load_tasks(TASKS_SAVE_PATH)
if "task_add_message" not in st.session_state:
    st.session_state.task_add_message = None
if "add_due_date" not in st.session_state:
    st.session_state["add_due_date"] = date.today()

# Reset add-task fields on the run *after* Add Task (cannot set widget keys after widgets render).
if st.session_state.pop("_clear_add_task_form", False):
    st.session_state["add_task_name"] = ""
    st.session_state["add_assignee"] = ""
    st.session_state["add_due_date"] = date.today()

# --- ADD TASK SECTION ---
st.subheader("➕ Add a Task")
if st.session_state.task_add_message:
    _flash_hottub_emoji()
    st.success(st.session_state.task_add_message)
    st.session_state.task_add_message = None

col1, col2 = st.columns(2)

with col1:
    task_name = st.text_input("Task Name", key="add_task_name")
    assignee = st.text_input("Assignee", key="add_assignee")

with col2:
    due_date = st.date_input("Due Date", key="add_due_date")

if st.button("Add Task"):
    if task_name:
        st.session_state.tasks.append({
            "Task": task_name,
            "Assignee": assignee,
            "Due Date": due_date,
            "Done": False,
        })
        st.session_state.task_add_message = f"Added task: {task_name}"
        st.session_state["_clear_add_task_form"] = True
        _rerun()
    else:
        st.warning("Please enter a task name.")

# --- DISPLAY TASKS ---
st.subheader("📋 Task Board")
if use_supabase():
    st.caption(
        "Shared cloud board (Supabase). Other users' edits show up after you reload this tab "
        "or click **Refresh board** below."
    )
    rf1, rf2 = st.columns([1, 4])
    with rf1:
        if st.button("Refresh board", help="Load the latest tasks from the database"):
            st.session_state.tasks = load_tasks_supabase()
            st.session_state.pop("task_board_editor", None)
            _rerun()

if st.session_state.tasks:
    df = pd.DataFrame(st.session_state.tasks)

    edited = st.data_editor(
        df,
        column_config={
            "Done": st.column_config.CheckboxColumn(
                "Completed",
                help="Check here when the task is done",
                default=False,
            ),
        },
        disabled=["Task", "Assignee", "Due Date"],
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key="task_board_editor",
    )
    st.session_state.tasks = edited.to_dict("records")

    done_now = int(edited["Done"].sum())
    n_now = len(st.session_state.tasks)
    prev_n = st.session_state.get("_board_task_count")
    prev_done = st.session_state.get("_board_done_count")
    if prev_n is None or prev_n != n_now:
        st.session_state._board_task_count = n_now
        st.session_state._board_done_count = done_now
    elif done_now > prev_done:
        _flash_snowboard_completion()
        st.session_state._board_done_count = done_now
    elif done_now < prev_done:
        st.session_state._board_done_count = done_now

    st.caption("Made a mistake? Pick a task and click Remove.")
    n_tasks = len(st.session_state.tasks)

    def _delete_label(i: int) -> str:
        t = st.session_state.tasks[i]
        who = t.get("Assignee") or "—"
        return f"{t.get('Task', '')} ({who})"

    rm_col1, rm_col2 = st.columns([4, 1])
    with rm_col1:
        pick_del = st.selectbox(
            "Task to remove",
            range(n_tasks),
            format_func=_delete_label,
            key="task_delete_select",
            label_visibility="collapsed",
        )
    with rm_col2:
        if st.button("Remove", key="task_delete_btn"):
            st.session_state.tasks.pop(int(pick_del))
            _rerun()

    completed_tasks = done_now
    total_tasks = len(df)

    progress = completed_tasks / total_tasks

    if progress < 1:
        st.session_state.apres_shown = False

    st.subheader("🏔️ Progress")

    st.progress(progress)

    st.write(
        f"Completed {completed_tasks} out of {total_tasks} tasks."
    )

    # FUN LITTLE MESSAGE
    #if progress == 1:
        #st.snow()
        #st.success("🏂 All tasks complete! Time to ride.")

    # APRÈS-SKI CELEBRATION
if progress == 1 and not st.session_state.get("apres_shown", False):
    st.markdown(
        """
        <style>
        @keyframes apresFade {
            0% { opacity: 0; }
            15% { opacity: 1; }
            75% { opacity: 1; }
            100% { opacity: 0; }
        }

        @keyframes neonPulse {
            0%, 100% {
                text-shadow:
                    0 0 8px #ff9966,
                    0 0 18px #ff7733,
                    0 0 28px #ff5500;
            }

            50% {
                text-shadow:
                    0 0 14px #ffbb88,
                    0 0 30px #ff8844,
                    0 0 48px #ff5500;
            }
        }

        .apres-overlay {
            position: fixed;
            inset: 0;
            background:
                radial-gradient(
                    circle at center,
                    rgba(255,170,90,0.18) 0%,
                    rgba(120,50,10,0.78) 100%
                );

            backdrop-filter: blur(3px);
            z-index: 99999;
            pointer-events: none;

            animation: apresFade 4s ease forwards;
        }

        .apres-neon {
            position: fixed;
            top: 38%;
            left: 50%;
            transform: translateX(-50%);

            text-align: center;
            line-height: 1.05;
            white-space: normal;

            font-size: clamp(2.8rem, 8vw, 5rem);
            font-weight: 800;
            letter-spacing: 0.18em;

            color: #ffd6b3;

            text-shadow:
                0 0 8px #ff9966,
                0 0 18px #ff7733,
                0 0 28px #ff5500;

            animation: neonPulse 1.6s infinite;
            animation: apresFade 4s ease forwards;

            z-index: 100000;

            font-family: sans-serif;
        }

        .apres-sub {
            position: fixed;
            top: 72%;
            left: 50%;
            transform: translateX(-50%);

            color: #fff4ea;
            font-size: 1.3rem;
            letter-spacing: 0.08em;

            z-index: 100000;

            animation: apresFade 4s ease forwards;
        }
        </style>

        <div class="apres-overlay"></div>

        <div class="apres-neon">
            HOT TUB<br>OPEN
        </div>

        <div class="apres-sub">
            All runs cleared. Time for après-ski.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.apres_shown = True
else:
    st.info("No tasks added yet.")

# Persist after every run (JSON locally, or Supabase on Streamlit Cloud).
if use_supabase():
    save_tasks_supabase(st.session_state.tasks)
else:
    save_tasks(TASKS_SAVE_PATH, st.session_state.tasks)