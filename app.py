"""
Local web UI for the Job Opportunity Agent.

    python app.py     ->  http://localhost:8000

Paste a job description, watch the agent work, download the PDFs. Past runs stay
listed so you can see what you applied to and what the agent thought.

This runs on YOUR machine against YOUR key. It is not the portfolio demo — that
one replays cached runs and calls nothing. This one is the real thing, so every
run costs real money.

A run takes several minutes, which is too long to hold an HTTP request open. So
POST /api/run starts the work on a background thread and returns immediately;
the page polls /api/status for progress lines and the finished result.
"""

import json
import os
import shutil
import threading
import uuid
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

from agent import MODEL, evaluate, parse_field, parse_recommendation, report_text
from application_generator import (
    OUTPUT_DIR, SOURCES_FILE, generate_application_package, render_document,
)

app = Flask(__name__, static_folder=None)
ROOT = os.path.dirname(os.path.abspath(__file__))

# Runs live in memory for the life of the process; the durable record is the
# run.json written into each output folder.
RUNS: dict = {}


def _execute(run_id: str, job_description: str) -> None:
    """One full agent run, on a background thread."""
    state = RUNS[run_id]

    def step(line: str) -> None:
        state["progress"].append(line)

    try:
        step("evaluating against your profile...")
        result = evaluate(job_description)
        report = report_text(result["response"])

        recommendation = parse_recommendation(report)
        company = parse_field(report, "Company")
        role = parse_field(report, "Role")

        for query in result["search_queries"]:
            state["searches"].append(query)

        state.update({
            "recommendation": recommendation,
            "reasoning": parse_field(report, "Reasoning"),
            "company": company,
            "role": role,
            "report": report,
            "agent_tokens": {"input": result["input_tokens"],
                             "output": result["output_tokens"],
                             "cache_read": result["cache_read"]},
        })

        if recommendation == "UNPARSED":
            state["status"] = "error"
            state["error"] = "The model's reply had no recommendation line."
            return

        # The UI decides whether to generate; the caller passed the choice in.
        if recommendation == "SKIP" and not state["generate_on_skip"]:
            step("SKIP — no materials generated")
            state["status"] = "done"
            return

        step("generating application package...")
        package = generate_application_package(
            job_description, recommendation, state["reasoning"], result["research"],
            company=company, role=role, progress=step,
        )
        state["run_dir"] = os.path.relpath(package["run_dir"], ROOT)
        state["files"] = [os.path.basename(p) for p in package["files"].values()]
        state["generation_tokens"] = {"input": package["input_tokens"],
                                      "output": package["output_tokens"],
                                      "cache_read": package["cache_read"]}
        state["status"] = "done"
    except Exception as exc:  # a failed run must report, not vanish
        state["status"] = "error"
        state["error"] = f"{type(exc).__name__}: {exc}"


@app.get("/")
def index():
    return send_from_directory(os.path.join(ROOT, "ui"), "index.html")


@app.get("/favicon.ico")
def favicon():
    return ("", 204)


@app.post("/api/run")
def start_run():
    if not os.environ.get("ANTHROPIC_API_KEY") or not MODEL:
        return jsonify({"error": "ANTHROPIC_API_KEY or ANTHROPIC_MODEL is missing from .env"}), 500

    body = request.get_json(silent=True) or {}
    job_description = (body.get("job_description") or "").strip()
    if not job_description:
        return jsonify({"error": "Paste a job description first."}), 400

    run_id = uuid.uuid4().hex[:12]
    RUNS[run_id] = {
        "id": run_id, "status": "running", "progress": [], "searches": [],
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "generate_on_skip": bool(body.get("generate_on_skip")),
    }
    threading.Thread(target=_execute, args=(run_id, job_description), daemon=True).start()
    return jsonify({"id": run_id})


@app.get("/api/status/<run_id>")
def status(run_id: str):
    state = RUNS.get(run_id)
    if not state:
        return jsonify({"error": "Unknown run."}), 404
    return jsonify(state)


@app.get("/api/history")
def history():
    """Past applications, newest first, read from the run.json in each folder."""
    out = []
    if os.path.isdir(OUTPUT_DIR):
        for name in sorted(os.listdir(OUTPUT_DIR), reverse=True):
            meta_path = os.path.join(OUTPUT_DIR, name, "run.json")
            if not os.path.isfile(meta_path):
                continue
            with open(meta_path) as handle:
                meta = json.load(handle)
            meta["folder"] = name
            meta["files"] = sorted(f for f in os.listdir(os.path.join(OUTPUT_DIR, name))
                                   if f.endswith(".pdf"))
            # Packages generated before the markdown was kept cannot be edited,
            # so the UI does not offer it for them.
            meta["editable"] = os.path.isfile(os.path.join(OUTPUT_DIR, name, SOURCES_FILE))
            meta.pop("job_description", None)  # too big for a list view
            out.append(meta)
    return jsonify(out)


def _run_dir(folder: str):
    """Resolve a history folder name. Returns (path, None) or (None, response).

    Every route that reads, writes or removes real files goes through here, so
    the check happens once. The resolved target must sit directly inside
    outputs/ and carry a run.json: a traversal, an absolute path, a nested path
    or an unrelated directory is rejected before any filesystem work happens.
    """
    base = os.path.realpath(os.path.join(ROOT, OUTPUT_DIR))
    target = os.path.realpath(os.path.join(base, folder))

    if os.path.dirname(target) != base or target == base:
        return None, (jsonify({"error": "Invalid folder."}), 400)
    if not os.path.isdir(target):
        return None, (jsonify({"error": "That application no longer exists."}), 404)
    if not os.path.isfile(os.path.join(target, "run.json")):
        return None, (jsonify({"error": "Not a generated application folder."}), 400)
    return target, None


def _sources(run_dir: str):
    """The markdown behind a run's PDFs, or None for a run generated before
    sources were kept."""
    path = os.path.join(run_dir, SOURCES_FILE)
    if not os.path.isfile(path):
        return None
    with open(path) as handle:
        return json.load(handle)


@app.delete("/api/history/<folder>")
def delete_run(folder: str):
    """Delete one past application, folder and all. No undo, hence the guard."""
    target, error = _run_dir(folder)
    if error:
        return error
    shutil.rmtree(target)
    return jsonify({"deleted": folder})


@app.get("/api/document/<folder>/<key>")
def read_document(folder: str, key: str):
    """The editable markdown behind one generated PDF."""
    run_dir, error = _run_dir(folder)
    if error:
        return error

    sources = _sources(run_dir)
    if sources is None:
        return jsonify({"error": "This application was generated before the text "
                                 "was kept, so there is nothing to edit. Re-run the "
                                 "job description to get an editable version."}), 409
    if key not in sources:
        return jsonify({"error": "No such document."}), 404

    entry = sources[key]
    return jsonify({"key": key, "file": entry["file"], "style": entry["style"],
                    "markdown": entry["markdown"]})


@app.put("/api/document/<folder>/<key>")
def write_document(folder: str, key: str):
    """Replace one document's text and re-render its PDF.

    The edit names a document by key, never by path: the filename and style
    come from the run's own sources.json, so a request cannot choose what gets
    overwritten. The PDF is rendered to a temporary file first and moved into
    place only once it exists, so a render that fails leaves the previous PDF
    intact rather than truncating it.
    """
    run_dir, error = _run_dir(folder)
    if error:
        return error

    sources = _sources(run_dir)
    if sources is None:
        return jsonify({"error": "This application has no editable text."}), 409
    if key not in sources:
        return jsonify({"error": "No such document."}), 404

    markdown_text = (request.get_json(silent=True) or {}).get("markdown")
    if not isinstance(markdown_text, str) or not markdown_text.strip():
        return jsonify({"error": "The document cannot be empty."}), 400
    if len(markdown_text) > 200_000:
        return jsonify({"error": "That is far larger than any of these documents."}), 400

    entry = sources[key]
    final = os.path.join(run_dir, entry["file"])
    draft = final + ".rendering"
    try:
        pages, pt = render_document(markdown_text, draft, entry["style"])
    except Exception as exc:
        if os.path.exists(draft):
            os.remove(draft)
        return jsonify({"error": f"Could not render that text: {exc}"}), 400
    os.replace(draft, final)

    entry["markdown"] = markdown_text
    with open(os.path.join(run_dir, SOURCES_FILE), "w") as handle:
        json.dump(sources, handle, indent=2)

    fitted = entry["style"] in ("resume", "letter")
    return jsonify({"file": entry["file"], "pages": pages, "body_pt": pt,
                    "fitted": fitted})


@app.get("/outputs/<path:relative>")
def outputs(relative: str):
    """Serve a generated PDF. send_from_directory rejects path traversal."""
    return send_from_directory(os.path.join(ROOT, OUTPUT_DIR), relative)


if __name__ == "__main__":
    # Bound to localhost on purpose: this runs the real agent with your key and
    # your private experience bank, and is not built to face the internet.
    print("Job Opportunity Agent — http://localhost:8000")
    app.run(host="127.0.0.1", port=8000, debug=False)
