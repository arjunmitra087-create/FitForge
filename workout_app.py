"""
🏋️ FitForge — Premium Workout Tracker
A Flask-based workout application with a beautiful dark-themed UI.
Run: pip install flask && python workout_app.py
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from flask import send_from_directory

app = Flask(__name__)
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static', 'service-worker.js')

app.config["SECRET_KEY"] = "fitforge-secret-key-2026"

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fitforge.db")

# ──────────────────────── Database helpers ────────────────────────

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            muscle_group TEXT,
            equipment TEXT DEFAULT 'None',
            is_custom INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS workout_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS template_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            sets INTEGER DEFAULT 3,
            reps INTEGER DEFAULT 10,
            rest_seconds INTEGER DEFAULT 60,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (template_id) REFERENCES workout_templates(id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        );

        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER,
            name TEXT,
            started_at TEXT DEFAULT (datetime('now')),
            finished_at TEXT,
            duration_seconds INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (template_id) REFERENCES workout_templates(id)
        );

        CREATE TABLE IF NOT EXISTS session_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            set_number INTEGER NOT NULL,
            reps INTEGER,
            weight REAL DEFAULT 0,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        );

        CREATE TABLE IF NOT EXISTS personal_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_id INTEGER NOT NULL,
            max_weight REAL DEFAULT 0,
            max_reps INTEGER DEFAULT 0,
            achieved_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        );
    """)

    # Seed default exercises if table is empty
    cursor = db.execute("SELECT COUNT(*) FROM exercises")
    if cursor.fetchone()[0] == 0:
        exercises = [
            # Chest
            ("Bench Press", "Chest", "Barbell bench press on flat bench", "Pectorals", "Barbell"),
            ("Incline Dumbbell Press", "Chest", "Dumbbell press on incline bench", "Upper Pectorals", "Dumbbells"),
            ("Cable Flyes", "Chest", "Standing cable crossover flyes", "Pectorals", "Cable Machine"),
            ("Push-Ups", "Chest", "Bodyweight push-ups", "Pectorals", "Bodyweight"),
            ("Dumbbell Flyes", "Chest", "Flat bench dumbbell flyes", "Pectorals", "Dumbbells"),
            ("Decline Bench Press", "Chest", "Barbell press on decline bench", "Lower Pectorals", "Barbell"),
            # Back
            ("Deadlift", "Back", "Conventional barbell deadlift", "Full Back", "Barbell"),
            ("Pull-Ups", "Back", "Bodyweight pull-ups", "Lats", "Pull-up Bar"),
            ("Barbell Row", "Back", "Bent-over barbell row", "Mid Back", "Barbell"),
            ("Lat Pulldown", "Back", "Wide-grip lat pulldown", "Lats", "Cable Machine"),
            ("Seated Cable Row", "Back", "Seated cable row with V-bar", "Mid Back", "Cable Machine"),
            ("T-Bar Row", "Back", "T-bar row with handle", "Mid Back", "Barbell"),
            # Legs
            ("Squat", "Legs", "Barbell back squat", "Quadriceps", "Barbell"),
            ("Leg Press", "Legs", "Machine leg press", "Quadriceps", "Machine"),
            ("Romanian Deadlift", "Legs", "Barbell Romanian deadlift", "Hamstrings", "Barbell"),
            ("Leg Extension", "Legs", "Machine leg extension", "Quadriceps", "Machine"),
            ("Leg Curl", "Legs", "Machine leg curl", "Hamstrings", "Machine"),
            ("Calf Raise", "Legs", "Standing calf raises", "Calves", "Machine"),
            ("Bulgarian Split Squat", "Legs", "Single-leg split squat on bench", "Quadriceps", "Dumbbells"),
            # Shoulders
            ("Overhead Press", "Shoulders", "Standing barbell overhead press", "Deltoids", "Barbell"),
            ("Lateral Raise", "Shoulders", "Dumbbell lateral raises", "Side Deltoids", "Dumbbells"),
            ("Face Pull", "Shoulders", "Cable face pull with rope", "Rear Deltoids", "Cable Machine"),
            ("Arnold Press", "Shoulders", "Seated Arnold press with dumbbells", "Deltoids", "Dumbbells"),
            ("Front Raise", "Shoulders", "Dumbbell front raises", "Front Deltoids", "Dumbbells"),
            ("Reverse Flyes", "Shoulders", "Bent-over reverse dumbbell flyes", "Rear Deltoids", "Dumbbells"),
            # Arms
            ("Barbell Curl", "Arms", "Standing barbell curl", "Biceps", "Barbell"),
            ("Tricep Pushdown", "Arms", "Cable tricep pushdown with rope", "Triceps", "Cable Machine"),
            ("Hammer Curl", "Arms", "Dumbbell hammer curls", "Biceps", "Dumbbells"),
            ("Skull Crushers", "Arms", "Lying EZ-bar skull crushers", "Triceps", "EZ Bar"),
            ("Concentration Curl", "Arms", "Seated dumbbell concentration curl", "Biceps", "Dumbbells"),
            ("Dips", "Arms", "Parallel bar tricep dips", "Triceps", "Bodyweight"),
            # Core
            ("Plank", "Core", "Front plank hold", "Abdominals", "Bodyweight"),
            ("Hanging Leg Raise", "Core", "Hanging leg raises", "Lower Abs", "Pull-up Bar"),
            ("Cable Crunch", "Core", "Kneeling cable crunch", "Abdominals", "Cable Machine"),
            ("Ab Wheel Rollout", "Core", "Ab wheel rollout from knees", "Abdominals", "Ab Wheel"),
            ("Russian Twist", "Core", "Seated Russian twist with weight", "Obliques", "Dumbbell"),
            ("Mountain Climbers", "Core", "Bodyweight mountain climbers", "Full Core", "Bodyweight"),
        ]
        db.executemany(
            "INSERT INTO exercises (name, category, description, muscle_group, equipment) VALUES (?,?,?,?,?)",
            exercises,
        )

        # Seed default templates
        templates = [
            ("Push Day", "Chest, shoulders, and triceps", "Push"),
            ("Pull Day", "Back and biceps", "Pull"),
            ("Leg Day", "Quadriceps, hamstrings, and calves", "Legs"),
            ("Upper Body", "Full upper body workout", "Upper"),
            ("Full Body", "Complete full body session", "Full"),
        ]
        for name, desc, cat in templates:
            db.execute(
                "INSERT INTO workout_templates (name, description, category) VALUES (?,?,?)",
                (name, desc, cat),
            )

        # Link exercises to templates
        template_exercises = {
            1: [(1, 4, 8, 90), (2, 3, 10, 60), (3, 3, 12, 60), (20, 4, 8, 90), (21, 3, 15, 45), (27, 3, 12, 60)],
            2: [(7, 3, 5, 120), (8, 4, 8, 90), (9, 4, 10, 60), (10, 3, 12, 60), (26, 3, 12, 60), (28, 3, 12, 45)],
            3: [(13, 4, 8, 120), (14, 3, 12, 90), (15, 3, 10, 90), (16, 3, 15, 45), (17, 3, 12, 45), (18, 4, 15, 45)],
            4: [(1, 4, 8, 90), (9, 4, 10, 60), (20, 3, 8, 90), (8, 3, 8, 90), (26, 3, 12, 45), (27, 3, 12, 45)],
            5: [(13, 3, 8, 120), (1, 3, 8, 90), (9, 3, 10, 60), (20, 3, 8, 60), (26, 3, 12, 45), (31, 1, 60, 30)],
        }
        for tid, exs in template_exercises.items():
            for i, (eid, sets, reps, rest) in enumerate(exs):
                db.execute(
                    "INSERT INTO template_exercises (template_id, exercise_id, sets, reps, rest_seconds, sort_order) VALUES (?,?,?,?,?,?)",
                    (tid, eid, sets, reps, rest, i),
                )

    db.commit()
    db.close()


# ──────────────────────── API Routes ────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Exercises ──

@app.route("/api/exercises")
def get_exercises():
    db = get_db()
    category = request.args.get("category")
    if category:
        rows = db.execute("SELECT * FROM exercises WHERE category = ? ORDER BY name", (category,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM exercises ORDER BY category, name").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/exercises", methods=["POST"])
def create_exercise():
    data = request.json
    db = get_db()
    cur = db.execute(
        "INSERT INTO exercises (name, category, description, muscle_group, equipment, is_custom) VALUES (?,?,?,?,?,1)",
        (data["name"], data["category"], data.get("description", ""), data.get("muscle_group", ""), data.get("equipment", "None")),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid}), 201


# ── Templates ──

@app.route("/api/templates")
def get_templates():
    db = get_db()
    templates = db.execute("SELECT * FROM workout_templates ORDER BY created_at DESC").fetchall()
    result = []
    for t in templates:
        exercises = db.execute("""
            SELECT te.*, e.name as exercise_name, e.category, e.muscle_group, e.equipment
            FROM template_exercises te
            JOIN exercises e ON te.exercise_id = e.id
            WHERE te.template_id = ?
            ORDER BY te.sort_order
        """, (t["id"],)).fetchall()
        td = dict(t)
        td["exercises"] = [dict(e) for e in exercises]
        result.append(td)
    return jsonify(result)


@app.route("/api/templates", methods=["POST"])
def create_template():
    data = request.json
    db = get_db()
    cur = db.execute(
        "INSERT INTO workout_templates (name, description, category) VALUES (?,?,?)",
        (data["name"], data.get("description", ""), data.get("category", "")),
    )
    tid = cur.lastrowid
    for i, ex in enumerate(data.get("exercises", [])):
        db.execute(
            "INSERT INTO template_exercises (template_id, exercise_id, sets, reps, rest_seconds, sort_order) VALUES (?,?,?,?,?,?)",
            (tid, ex["exercise_id"], ex.get("sets", 3), ex.get("reps", 10), ex.get("rest_seconds", 60), i),
        )
    db.commit()
    return jsonify({"id": tid}), 201


@app.route("/api/templates/<int:tid>", methods=["DELETE"])
def delete_template(tid):
    db = get_db()
    db.execute("DELETE FROM template_exercises WHERE template_id = ?", (tid,))
    db.execute("DELETE FROM workout_templates WHERE id = ?", (tid,))
    db.commit()
    return jsonify({"ok": True})


# ── Workout Sessions ──

@app.route("/api/sessions", methods=["POST"])
def start_session():
    data = request.json
    db = get_db()
    cur = db.execute(
        "INSERT INTO workout_sessions (template_id, name) VALUES (?,?)",
        (data.get("template_id"), data.get("name", "Quick Workout")),
    )
    session_id = cur.lastrowid

    # Pre-populate sets from template
    if data.get("template_id"):
        tex = db.execute(
            "SELECT * FROM template_exercises WHERE template_id = ? ORDER BY sort_order",
            (data["template_id"],),
        ).fetchall()
        for te in tex:
            for s in range(1, te["sets"] + 1):
                db.execute(
                    "INSERT INTO session_sets (session_id, exercise_id, set_number, reps, weight) VALUES (?,?,?,?,0)",
                    (session_id, te["exercise_id"], s, te["reps"]),
                )
    db.commit()
    return jsonify({"session_id": session_id}), 201


@app.route("/api/sessions/<int:sid>")
def get_session(sid):
    db = get_db()
    session = db.execute("SELECT * FROM workout_sessions WHERE id = ?", (sid,)).fetchone()
    if not session:
        return jsonify({"error": "Not found"}), 404
    sets = db.execute("""
        SELECT ss.*, e.name as exercise_name, e.category, e.muscle_group
        FROM session_sets ss
        JOIN exercises e ON ss.exercise_id = e.id
        WHERE ss.session_id = ?
        ORDER BY ss.exercise_id, ss.set_number
    """, (sid,)).fetchall()
    result = dict(session)
    result["sets"] = [dict(s) for s in sets]
    return jsonify(result)


@app.route("/api/sessions/<int:sid>/sets/<int:set_id>", methods=["PUT"])
def update_set(sid, set_id):
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE session_sets SET reps=?, weight=?, completed=1, completed_at=datetime('now') WHERE id=? AND session_id=?",
        (data.get("reps", 0), data.get("weight", 0), set_id, sid),
    )
    db.commit()

    # Check & update personal records
    ss = db.execute("SELECT * FROM session_sets WHERE id=?", (set_id,)).fetchone()
    if ss:
        pr = db.execute(
            "SELECT * FROM personal_records WHERE exercise_id=? ORDER BY max_weight DESC LIMIT 1",
            (ss["exercise_id"],),
        ).fetchone()
        weight = data.get("weight", 0)
        if not pr or weight > pr["max_weight"]:
            db.execute(
                "INSERT INTO personal_records (exercise_id, max_weight, max_reps) VALUES (?,?,?)",
                (ss["exercise_id"], weight, data.get("reps", 0)),
            )
            db.commit()
            return jsonify({"ok": True, "new_pr": True})

    return jsonify({"ok": True, "new_pr": False})


@app.route("/api/sessions/<int:sid>/finish", methods=["PUT"])
def finish_session(sid):
    data = request.json
    db = get_db()
    db.execute(
        "UPDATE workout_sessions SET finished_at=datetime('now'), duration_seconds=?, notes=? WHERE id=?",
        (data.get("duration_seconds", 0), data.get("notes", ""), sid),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/sessions/<int:sid>/sets", methods=["POST"])
def add_set_to_session(sid):
    data = request.json
    db = get_db()
    # Find next set number for this exercise in this session
    row = db.execute(
        "SELECT COALESCE(MAX(set_number),0) as mx FROM session_sets WHERE session_id=? AND exercise_id=?",
        (sid, data["exercise_id"]),
    ).fetchone()
    next_num = row["mx"] + 1
    cur = db.execute(
        "INSERT INTO session_sets (session_id, exercise_id, set_number, reps, weight) VALUES (?,?,?,?,?)",
        (sid, data["exercise_id"], next_num, data.get("reps", 10), data.get("weight", 0)),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid, "set_number": next_num}), 201


# ── History & Stats ──

@app.route("/api/history")
def get_history():
    db = get_db()
    limit = request.args.get("limit", 20, type=int)
    sessions = db.execute("""
        SELECT ws.*, wt.name as template_name,
               COUNT(ss.id) as total_sets,
               SUM(CASE WHEN ss.completed=1 THEN 1 ELSE 0 END) as completed_sets,
               SUM(CASE WHEN ss.completed=1 THEN ss.weight * ss.reps ELSE 0 END) as total_volume
        FROM workout_sessions ws
        LEFT JOIN workout_templates wt ON ws.template_id = wt.id
        LEFT JOIN session_sets ss ON ws.id = ss.session_id
        WHERE ws.finished_at IS NOT NULL
        GROUP BY ws.id
        ORDER BY ws.started_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return jsonify([dict(s) for s in sessions])


@app.route("/api/stats")
def get_stats():
    db = get_db()
    total_workouts = db.execute("SELECT COUNT(*) as c FROM workout_sessions WHERE finished_at IS NOT NULL").fetchone()["c"]
    total_sets = db.execute("SELECT COUNT(*) as c FROM session_sets WHERE completed=1").fetchone()["c"]
    total_volume = db.execute("SELECT COALESCE(SUM(weight * reps), 0) as v FROM session_sets WHERE completed=1").fetchone()["v"]

    # Streak calculation
    dates = db.execute("""
        SELECT DISTINCT DATE(started_at) as d FROM workout_sessions
        WHERE finished_at IS NOT NULL ORDER BY d DESC
    """).fetchall()
    streak = 0
    today = datetime.now().date()
    for i, row in enumerate(dates):
        expected = today - timedelta(days=i)
        if row["d"] == str(expected):
            streak += 1
        else:
            break

    # Weekly workouts (last 7 days)
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    weekly = db.execute(
        "SELECT COUNT(*) as c FROM workout_sessions WHERE finished_at IS NOT NULL AND started_at >= ?",
        (week_ago,),
    ).fetchone()["c"]

    # Personal records
    prs = db.execute("""
        SELECT pr.*, e.name as exercise_name, e.category
        FROM personal_records pr
        JOIN exercises e ON pr.exercise_id = e.id
        ORDER BY pr.achieved_at DESC LIMIT 10
    """).fetchall()

    # Category breakdown
    categories = db.execute("""
        SELECT e.category, COUNT(ss.id) as sets_count, SUM(ss.weight * ss.reps) as volume
        FROM session_sets ss
        JOIN exercises e ON ss.exercise_id = e.id
        WHERE ss.completed = 1
        GROUP BY e.category
        ORDER BY volume DESC
    """).fetchall()

    return jsonify({
        "total_workouts": total_workouts,
        "total_sets": total_sets,
        "total_volume": round(total_volume, 1),
        "current_streak": streak,
        "weekly_workouts": weekly,
        "personal_records": [dict(p) for p in prs],
        "category_breakdown": [dict(c) for c in categories],
    })


# ──────────────────────── Run ────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
