"""Load the whiteboard as transcribed on 2026-11-17.

Run once on an empty database:
    python scripts/seed_board.py            (locally, from the project root)
    docker compose exec fmrp-board python scripts/seed_board.py   (on the NAS)

It refuses to run if records already exist. Every row it creates is written to the
audit log as "seed (whiteboard 2026-11-17)".
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app import create_app, models  # noqa: E402
from app.db import get_db  # noqa: E402

ACTOR = {"user_id": None, "name": "seed (whiteboard 2026-11-17)", "ip": None}

# (lab, direction, value, residents, note). Board order. "?" = handwriting uncertain.
# Direction is a best guess from the lab name (FLAGGED in project_log.md).
SEED = [
    ("HCO3", "Low", "2", "Willis / Jackson", ""),
    ("A1c", "High", ">15.5", "Dunn / Bidaisee", ""),
    ("Glucose", "High", "2281", "Dawson", ""),
    ("Glucose", "Low", "<10", "Taylor / Pander", ""),
    ("Hgb", "Low", "2.8", "Carter / Alkalini?", ""),
    ("BNP", "High", "7,818", "Laroda / Peyton / Carter", ""),
    ("Troponin", "High", "121,469", "Bennett", ""),
    ("BMI", "High", "76", "Macbeth", ""),
    ("BMI", "Low", "12.8", "Scott / Por?", ""),
    ("Anion gap", "High", "37", "Scott", ""),
    ("LDH", "High", ">3,600", "Scott / Klade", ""),
    ("Wt loss per day (Lasix)", "High", "20 lbs", "Lopes / Belgrave", ""),
    ("Platelets", "High", "909", "Martin / Osbon", ""),
    ("Temp", "Low", "80.2 °F", "Martin / Osbon", ""),
    ("PSA", "High", "1,700", "Pander / Nowitzky?", ""),
    ("Lactate", "High", "24.1", "Haner? / Charite", ""),
    ("Procalcitonin", "High", "482.5", "Willis", ""),
    ("Admissions in a day", "Count", "7", "Lopez / Cunningham", ""),
    ("TSH", "High", "239", "Macbeth", ""),
    ("AST", "High", ">10,000", "Hammer / Charite", ""),
    ("Lipase", "High", ">1,800", "Hammer / Charite", ""),
    ("ALT", "High", ">5,000", "Dunn / St. Juste", ""),
    ("K+", "Low", "1.5", "Bennett / Alexis", ""),
    ("K+", "High", "8.7", "Willis / Belgrave", ""),
    ("Vit B12", "Low", "<50", "Bennett / Laroda", ""),
    ("Age", "High", "101", "Martin / Taylor", ""),
    ("EF", "Low", "10%", "Bridges / Dunn", ""),
    ("Na", "Low", "108", "Kerr / Bidaisse", ""),
    ("Alcohol level", "High", "479", "Macbeth / Lopes", ""),
    ("Paracentesis fluid", "High", "19 L", "Reid / St. Juste", ""),
    ("Units of insulin", "High", "1,235", "Shahid / Osbon", ""),
    ("Most codes in 1 shift", "Count", "7", "Kerr / Bidaisse?", ""),
    ("BUN", "High", "186", "Talebi / Charite", ""),  # previous value seeded below
    ("Creatinine", "High", "14.4", "Dantas / Charite", ""),
    ("pH", "Low", "<7", "Kerr / Dunn / Dantas / Bennett", "Two teams: Kerr + Dunn / Dantas + Bennett"),
    ("β-OH butyrate", "High", "7.44", "Dunn", ""),
    ("Vit D", "Low", "<7", "Dunn", ""),
    ("RDW", "High", "40.9", "Martin", ""),
    ("Weight", "High", "535 lb", "Talebi / Kerr", ""),
    ("PR interval", "High", "280 ms", "Reid / Macbeth", ""),
    ("CK", "High", "61,800+", "Headley / Dawson", ""),
    ("T. bili", "High", "57.4", "Osbon / Reid", ""),
    ("CRP", "High", "30.9", "Brown / Dantas", ""),
    ("Iron sat", "Low", "2%", "Laroda / Collins", ""),
    ("WBC", "Low", "0.2", "Willis / Bennett", ""),
    ("Discharges in a day", "Count", "7", "Cunningham", ""),
    ("Hrs to bounceback", "Low", "4", "Cunningham", ""),
    ("Platelets", "Low", "9", "Willis / Bennett", ""),
    ("Mg", "Low", "0.6", "Bennett / Bowens", ""),
    ("WBC", "High", "265", "Scott / Bowens", ""),
    ("Uric acid", "High", "19", "Scott / Bowens", ""),
    ("pCO2", "High", "107.9", "Kerr / Talebi", ""),
    ("CD4", "Low", "15", "Knibbe? / Martin", ""),
    ("MCV", "High", "124", "Willis", ""),
    ("Ferritin", "High", ">7,500", "Shane? / Evan", ""),
]
BUN_PREVIOUS = ("166", "Hammer / Belgrave")


def seed(db):
    if db.execute("SELECT COUNT(*) FROM records").fetchone()[0]:
        raise SystemExit("Records already exist; seed skipped.")

    def people(text):
        return [models.get_or_create_resident(db, ACTOR, n.strip()) for n in text.split("/") if n.strip()]

    with db:
        for lab, direction, value, names, note in SEED:
            lab_id = models.get_or_create_lab(db, ACTOR, lab)
            if lab == "BUN":
                rid = models.create_record(db, ACTOR, lab_id, direction, BUN_PREVIOUS[0], "",
                                           people(BUN_PREVIOUS[1]))
                models.update_record(db, ACTOR, rid, value_text=value, resident_ids=people(names))
            else:
                models.create_record(db, ACTOR, lab_id, direction, value, note, people(names))
    return len(SEED)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        n = seed(get_db())
    print(f"Seeded {n} records.")
