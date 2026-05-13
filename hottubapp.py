import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

TASKS_SAVE_PATH = Path(__file__).resolve().parent / "saved_tasks.json"
SUPABASE_TABLE = "shared_board_tasks"


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


st.set_page_config(page_title="Snowboard Project Tracker", layout="wide")

# --- TITLE ---
st.title("🏂 🏂 Snowboard Lodge Task Board")
st.caption("Tiny progress still counts.")

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

    completed_tasks = int(edited["Done"].sum())
    total_tasks = len(df)

    progress = completed_tasks / total_tasks

    st.subheader("🏔️ Progress")

    st.progress(progress)

    st.write(
        f"Completed {completed_tasks} out of {total_tasks} tasks."
    )

    # FUN LITTLE MESSAGE
    if progress == 1:
        st.balloons()
        st.success("🏂 All tasks complete! Time to ride.")
else:
    st.info("No tasks added yet.")

# Persist after every run (JSON locally, or Supabase on Streamlit Cloud).
if use_supabase():
    save_tasks_supabase(st.session_state.tasks)
else:
    save_tasks(TASKS_SAVE_PATH, st.session_state.tasks)