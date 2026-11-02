# UI demo walkthrough

About 6 minutes, on version 1.1.0. Every result below comes from a real run on the committed synthetic data.

## Before you start

Run this from the repo root. The throwaway database means the first saved check is check 1.

```bash
rm -rf /tmp/demo
PYTHONPATH=src COMPLIANCE_DB_PATH=/tmp/demo/compliance.db .venv/bin/python -m compliance serve
```

Open <http://127.0.0.1:8000>. The page needs no internet connection. Get the demo sign-in from the team; it is not in this repo.

## The walkthrough

### 1. Sign in and start on Home

Sign in as `compliance.manager`. Home should say **4 parts at risk, 6 issues need action, 2 expiring soon.**

Say: the tool flags problems, shows which parts are affected, and keeps a dated history. It never approves or blocks anything, because the manager decides. Open **What the words mean** if anyone asks about a term.

### 2. Open Reminders

Select **Reminders (17)** at the top. It groups everything by urgency:

| Group | Count | Point to |
|---|---:|---|
| Needs action | 6 | Safety certificate expired 147 days ago (DOC-005) |
| Expiring soon | 2 | Expires today (DOC-008), then in 25 days (DOC-006) |
| Waiting for approval | 1 | DOC-013, which does not count until approved |
| Could not use | 8 | Broken records, each with a reason |

### 3. Act on an issue

On the DOC-005 reminder, select **Draft reminder**. The message names the document, the date and the part affected. Select **Copy text**. Say: nothing is sent from here, because the customer scoped notifications for later.

Close it, then select **View history** on the same reminder to jump to that supplier.

### 4. Issues: per-part risk

Open **Issues**. Set **Supplier** to **SUP-103**.

- PRT-5003 is at risk because it needs a safety certificate.
- PRT-5004, from the same supplier, is not. Risk is per part.
- DOC-008 expires today, so it is **expiring soon**, not expired.

Set **Supplier** to **SUP-106**: PRT-5005 has no documents at all, so it has two issues. Select **All suppliers** and try the filter buttons, such as **Could not use (8)**.

### 5. Change the date

Set **Check as of** to **2026-11-25 (30 days later)**. Results update straight away. Parts at risk goes from 4 to 5: DOC-008 has now expired, so PRT-5004 is at risk. A warning became a real problem, which is why the customer wants 45 days' notice.

Set it back to **2026-10-26**.

### 6. Scenarios

Scenarios are preview only, so **Save to history** is unavailable.

| Data set | Result | What to say |
|---|---|---|
| **Sample + a renewal** | 3 parts at risk, DOC-005 gone | A renewal clears the old flag, and the old certificate stays on file for audit |
| **A day with no issues** | "No issues found", and the Reminders count disappears | A clean supplier gets a clean result |
| **Broken input file** | A clear error naming the file | A bad file stops the run and saves nothing |

Switch back to **Sample data**. It works straight away after the error.

### 7. Save history and answer the auditor

1. With **Sample data** on **2026-10-26**, select **Save to history**. The page confirms check 1.
2. Change the date to **2026-11-25**, then select **Save to history** again. The page confirms check 2.
3. Select **View history** in the message, then choose **SUP-103**.

Check 2 is first and marks DOC-008's expired flag as **New**. Say: this answers "what did you know on date X?". **SUP-101** shows no flags in any saved check. **SUP-104** has no saved record, because rejected documents are never saved.

### 8. Input data

Open **Input data** to show the scoped data: 19 usable documents, 9 parts, 8 rejected records, and what each category requires.

## What the UI does not show

The rollback from 1.1.0 to 1.0.0 is still shown with Docker, because 1.0.0 has no UI. See `docs/release.md`.

## If something goes wrong

| What happens | What to do |
|---|---|
| "Can't reach the server" | The server stopped. Start it again with the command above, then sign in |
| "Your session ended" | The server restarted. Sign in again; saved checks are kept |
| "Too many failed attempts" | Wait a minute, or restart the server |
| "Address already in use" when starting | Another copy is running. Stop it, or add `--port 8001` and open that port |
| Check numbers are higher than the script | The database has earlier checks. Stop the server, repeat "Before you start", and sign in again |
