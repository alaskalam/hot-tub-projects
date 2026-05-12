-- Run this in Supabase → SQL Editor once, then add secrets to Streamlit Cloud:
--   SUPABASE_URL = Project Settings → API → Project URL
--   SUPABASE_KEY = service_role key (server-side only; never put in client JS)
--
-- Using the service_role key from Streamlit secrets avoids RLS setup for a small internal board.

create table if not exists shared_board_tasks (
  position integer primary key,
  task text not null default '',
  assignee text not null default '',
  due_date date not null,
  done boolean not null default false
);
