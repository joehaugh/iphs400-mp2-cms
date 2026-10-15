"""Seed data: Schools, the Network School, an Admin, and Editors for two Schools.

The School rows are made-up placeholders; the real list of about 60 comes from
the client. Safe to run twice.
"""
from __future__ import annotations

import sqlite3

from app.passwords import hash_password

NETWORK_URL_NAME = "network"

SCHOOLS = [
    # name, short_name, city, state, url_name, is_network
    ("Jesuit Schools Network", "Network", "Washington", "DC", NETWORK_URL_NAME, 1),
    ("St. Ignatius Preparatory School", "St. Ignatius", "Springfield", "OH", "st-ignatius", 0),
    ("Loyola Academy of Riverton", "Loyola Riverton", "Riverton", "IL", "loyola-riverton", 0),
    ("Xavier High School of Lakeside", "Xavier Lakeside", "Lakeside", "MI", "xavier-lakeside", 0),
    ("Campion College Preparatory", "Campion", "Prairie Falls", "WI", "campion", 0),
]

# Made-up placeholders to reach the Network's roughly 60 Schools: patron, city, state.
_MORE = """
Aloysius|Millbrook|NY
Ambrose|Cedar Hollow|PA
Andrew Bobola|Fairhaven|MA
Augustine|Oakridge|NJ
Benedict|Stonebridge|CT
Bellarmine|Harborview|WA
Brebeuf|Northfield|MN
Canisius|Elmwood|NY
Claver|Sunset Bay|FL
Copleston|Red Rock|CO
De Smet|Bitterroot|MT
Edmund Campion|Linden|OH
Francis Borgia|Willow Creek|CA
Gaspar|Pinecrest|OR
Gonzaga|Lakemont|VA
Hopkins|Ashford|MD
Isaac Jogues|Maple Glen|NY
Joseph Pignatelli|Briar Cliff|IA
Kino|Mesa Verde|AZ
Lainez|Quarry Hill|TN
Le Moyne|Port Alder|ME
Marquette|Sandy Shores|MI
Neri|Foxgrove|IL
Nobili|Silver Lake|UT
Ortiz|Cottonwood|TX
Peter Faber|Hartwell|KS
Peter Canisius|Bayside|LA
Ricci|Clover Field|IN
Rodriguez|Eastgate|GA
Salmeron|Highpoint|NC
Stanislaus|Greenvale|WI
Suarez|Ridgemont|KY
Teilhard|Westbrook|VT
Torres|Laurel Ford|SC
Valignano|Summit Park|NH
Verbiest|Rockport|RI
Xavier Heights|Brookside|MO
Acosta|Driftwood|AL
Borja|Larkspur|NM
Camillus|Wren Hill|NE
Dolores|Thornbury|OK
Eusebius|Marlow|AR
Felix|Gladstone|ID
Gregory|Haverford Park|DE
Hilary|Ironwood|WV
Ignatius Loyola North|Juniper Falls|NV
Jerome|Kestrel Point|WY
Leo|Lindenhurst|ND
Martin|Moorfield|SD
Norbert|Northhaven|AK
Oswald|Orchard Bay|HI
Patrick|Plainsboro Ridge|MS
Quentin|Queensbury Flats|OH
Raphael|Redwood Glen|CA
Sebastian|Saltmarsh|NJ
Tarcisius|Tidewater|VA
"""
_KINDS = ("Preparatory School", "High School", "Academy", "College Preparatory")


def _more_schools():
    for i, line in enumerate(_MORE.strip().splitlines()):
        patron, city, state = line.split("|")
        slug = "".join(c if c.isalnum() else "-" for c in patron.lower())
        name = f"{patron} {_KINDS[i % len(_KINDS)]}"
        yield (name, patron, city, state, f"{slug}-{city.lower().replace(' ', '-')}", 0)


SCHOOLS += list(_more_schools())

# key -> (email, role, school url_name)
USERS = {
    "admin": ("admin@example.test", "admin", None),
    "editor": ("editor@example.test", "editor", "st-ignatius"),
    "editor_b": ("editor-b@example.test", "editor", "loyola-riverton"),
}


def seed(conn: sqlite3.Connection, passwords: dict[str, str]) -> None:
    """`passwords` maps the keys in USERS to a plain password (hashed here)."""
    for row in SCHOOLS:
        conn.execute(
            "INSERT OR IGNORE INTO schools (name, short_name, city, state, url_name, is_network)"
            " VALUES (?, ?, ?, ?, ?, ?)", row)
    for key, (email, role, school_url) in USERS.items():
        school = conn.execute(
            "SELECT id FROM schools WHERE url_name = ?", (school_url,)).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO users (email, password_hash, role, school_id)"
            " VALUES (?, ?, ?, ?)",
            (email, hash_password(passwords[key]), role, school["id"] if school else None))
    conn.commit()
