"""Fill a fresh database with realistic demo accounts and content.

Can be run standalone:
    python seed_demo.py

Or called automatically on app startup if the database is fresh.
All demo accounts use password: demo1234
"""
import os
import sqlite3

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except Exception:
    HAS_PIL = False

from werkzeug.security import generate_password_hash

import db as dbmod
import media

PASSWORD = "demo1234"

USERS = [
    ("aarav_s", "Aarav Sharma", "Building AgriFlow: IoT drip irrigation controller for Maharashtra farmers. BITS Pilani grad."),
    ("pooja_i", "Pooja Iyer", "Founder @ HealthSathi. Bringing affordable diagnostic tele-consults to Tier-2/3 towns."),
    ("vikram_roy", "Vikramaditya Roy", "Angel backer & ex-founder. Investing in early-stage student builders and impact tech."),
    ("kavita_d", "Kavita Desai", "CSR Lead @ ImpactFirst Fund. Looking for sustainability & healthcare pilots."),
    ("rohan_v", "Rohan Verma", "EdTech builder. Creating PocketLabs — virtual STEM experiments for vernacular schools."),
]

# (author, title, pitch, description, domain, stage, funding, [card colours & labels])
SLATE, EMERALD, BLUE, AMBER, TEAL, INDIGO = (
    (30, 41, 59), (5, 150, 105), (37, 99, 235), (217, 119, 6), (13, 148, 136), (79, 70, 229)
)

POSTS = [
    (
        "aarav_s",
        "AgriFlow",
        "Solar-powered IoT drip irrigation valves reducing water waste by 40%",
        "Small-scale farmers in dry regions lose up to 40% of their groundwater due to unmetered flooding. "
        "AgriFlow is a rugged, GSM-enabled valve controller running on a 5W mini solar panel that lets farmers "
        "schedule and monitor irrigation cycles via SMS or WhatsApp bot. Tested with 12 farmer groups in Baramati.",
        "AgriTech",
        "prototype",
        350000,
        [(SLATE, EMERALD, "Field Prototype"), (EMERALD, TEAL, "12 Pilot Farms"), (SLATE, BLUE, "GSM Controller")]
    ),
    (
        "pooja_i",
        "HealthSathi",
        "Portable offline diagnostic vital signs kit for rural community health clinics",
        "Over 65% of rural primary clinics lack trained lab technicians on site. HealthSathi is a rugged, "
        "backpack-sized vitals monitor (ECG, SpO2, blood pressure, glucose) that operates offline and syncs clinical "
        "summaries with district hospitals over 2G/3G networks.",
        "HealthTech",
        "mvp",
        750000,
        [(SLATE, BLUE, "Diagnostic Kit"), (BLUE, TEAL, "Offline Sync"), (EMERALD, BLUE, "Clinic Trials")]
    ),
    (
        "rohan_v",
        "PocketLabs",
        "Bite-sized interactive physics & chemistry labs on low-cost Android phones",
        "Most government and rural high schools lack functional laboratory infrastructure. PocketLabs provides "
        "interactive, vernacular 3D lab simulations that run on low-spec phones without needing high-speed internet. "
        "Over 600 students across 15 schools have completed physics modules with a 35% higher test score retention.",
        "EdTech",
        "growth",
        250000,
        [(INDIGO, BLUE, "Interactive Labs"), (AMBER, SLATE, "600+ Students")]
    ),
    (
        "aarav_s",
        "VoltCycle",
        "Repurposed second-life EV batteries for night market vendor clean lighting",
        "Instead of loud, toxic kerosene lamps or diesel generators, VoltCycle converts retired electric 2-wheeler "
        "battery cells into rugged 12V portable clean power packs for street food vendors with zero emissions.",
        "CleanTech",
        "idea",
        400000,
        [(TEAL, EMERALD, "Clean Power"), (SLATE, AMBER, "Vendor Trials")]
    ),
]


def make_fast_image(name, c1, c2, label, size=700):
    """Generate a clean, high-performance card preview in milliseconds."""
    if not HAS_PIL:
        return None
    try:
        # Create a small 2x2 color base and scale up smoothly (sub-millisecond!)
        base = Image.new("RGB", (2, 2))
        base.putpixel((0, 0), c1)
        base.putpixel((1, 0), tuple((a + b) // 2 for a, b in zip(c1, c2)))
        base.putpixel((0, 1), tuple((a + b) // 2 for a, b in zip(c1, c2)))
        base.putpixel((1, 1), c2)
        resample_mode = getattr(getattr(Image, 'Resampling', None), 'BILINEAR', Image.BILINEAR)
        image = base.resize((size, size), resample=resample_mode)

        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.load_default(size=48)
        except TypeError:
            font = ImageFont.load_default()
        
        # Subtle dark overlay card inside image for human, readable contrast
        pad = 60
        draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=24, fill=(15, 23, 42, 180), outline=(255, 255, 255, 40), width=2)
        
        # Draw readable label in center
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text(((size - text_w) / 2, (size - text_h) / 2), label, fill="#ffffff", font=font)

        os.makedirs(media.UPLOAD_DIR, exist_ok=True)
        image.save(os.path.join(media.UPLOAD_DIR, name), "PNG")
        return f"uploads/{name}"
    except Exception:
        return None


def seed(conn):
    """Seed demo data into the provided SQLite connection."""
    pw = generate_password_hash(PASSWORD)
    ids = {}
    for username, full_name, bio in USERS:
        cur = conn.execute(
            """INSERT INTO users (full_name, username, email, password_hash, bio, theme, accent)
               VALUES (?, ?, ?, ?, ?, 'system', 'aurora')""",
            (full_name, username, f"{username}@example.com", pw, bio)
        )
        ids[username] = cur.lastrowid

    post_ids = {}
    for author, title, pitch, text, domain, stage, funding, images in POSTS:
        cur = conn.execute(
            """INSERT INTO projects (innovator_id, title, summary, description, domain, stage, funding_needed, accepts_money, accepts_goods, accepts_pilot)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 1)""",
            (ids[author], title, pitch, text, domain, stage, funding)
        )
        post_ids[title] = cur.lastrowid
        for position, (c1, c2, label) in enumerate(images):
            path = make_fast_image(f"demo-{cur.lastrowid}-{position}.png", c1, c2, label)
            if path:
                conn.execute(
                    "INSERT INTO post_media (post_id, path, type, position) VALUES (?, ?, 'image', ?)",
                    (cur.lastrowid, path, position)
                )

    # Likes
    likes_map = {
        "AgriFlow": ["vikram_roy", "kavita_d", "pooja_i"],
        "HealthSathi": ["vikram_roy", "kavita_d", "aarav_s"],
        "PocketLabs": ["pooja_i", "aarav_s", "kavita_d"],
        "VoltCycle": ["vikram_roy", "rohan_v"],
    }
    for title, fans in likes_map.items():
        if title in post_ids:
            for fan in fans:
                conn.execute("INSERT OR IGNORE INTO likes (post_id, user_id) VALUES (?, ?)", (post_ids[title], ids[fan]))

    # Comments
    comments = [
        ("AgriFlow", "vikram_roy", "Tested this on farms in Baramati? Incredible progress Aarav! How does battery life hold during monsoon clouds?"),
        ("AgriFlow", "aarav_s", "Thanks Vikram! The 5W panel charges a 2-day backup battery, and our firmware goes to ultra-low sleep mode between readings."),
        ("HealthSathi", "kavita_d", "Tata Impact team is actively evaluating rural diagnostic pilots in Nashik. Sending an offer through your deal room!"),
        ("PocketLabs", "pooja_i", "The vernacular simulation model is a game changer for Maharashtra state board schools."),
    ]
    for title, who, text in comments:
        if title in post_ids and who in ids:
            conn.execute("INSERT INTO comments (post_id, user_id, body) VALUES (?, ?, ?)", (post_ids[title], ids[who], text))

    # Sponsorship offers & Deal room
    sponsorships = [
        ("vikram_roy", "AgriFlow", 180000, "Agreed to back initial 25 sensor batch + pilot trial support.", "accepted"),
        ("kavita_d", "HealthSathi", 400000, "Tata Foundation CSR pilot allocation for 10 rural centres.", "accepted"),
        ("kavita_d", "PocketLabs", 150000, "Interested in expanding to 10 more schools in rural Pune.", "pending"),
    ]
    for sponsor, title, amount, message, status in sponsorships:
        if sponsor in ids and title in post_ids:
            conn.execute(
                """INSERT INTO interests (sponsor_id, project_id, amount, message, status, goods, pilot, turn)
                   VALUES (?, ?, ?, ?, ?, '', 1, 'creator')""",
                (ids[sponsor], post_ids[title], amount, message, status)
            )

    # Direct Messages between Aarav and Vikram
    a, b = sorted((ids["aarav_s"], ids["vikram_roy"]))
    thread = conn.execute(
        "INSERT INTO dm_threads (user_a, user_b, requested_by, status) VALUES (?, ?, ?, 'accepted')",
        (a, b, ids["vikram_roy"])
    ).lastrowid
    
    dm_msgs = [
        ("vikram_roy", "Hey Aarav, excited to partner on AgriFlow. The hardware batch proposal looks solid."),
        ("aarav_s", "Thank you so much Vikram! We just finalized PCB assembly and will deploy 10 units next week."),
        ("vikram_roy", "Keep me posted. Let's do a voice check-in once field data starts syncing."),
    ]
    for sender, body in dm_msgs:
        conn.execute("INSERT INTO dm_messages (thread_id, sender_id, body) VALUES (?, ?, ?)", (thread, ids[sender], body))

    conn.commit()


def ensure_demo_data():
    """Checks if database is empty; if so, populates it safely with realistic demo data."""
    try:
        conn = sqlite3.connect(dbmod.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        user_count = conn.execute("SELECT COUNT(*) FROM users WHERE is_bot = 0").fetchone()[0]
        if user_count == 0:
            seed(conn)
            # Create sample server
            try:
                from app import app
                from servers.routes import create_server
                with app.app_context():
                    owner_row = conn.execute("SELECT id FROM users WHERE username = 'aarav_s'").fetchone()
                    if owner_row:
                        owner_id = owner_row[0]
                        server = create_server(owner_id, "AgriFlow Hardware Lab", "🌱", "#059669", "Official hardware community for AgriFlow builders and backers.", 1)
                        dev_row = conn.execute("SELECT id FROM users WHERE username = 'vikram_roy'").fetchone()
                        if dev_row:
                            conn.execute("INSERT OR IGNORE INTO server_members (server_id, user_id) VALUES (?, ?)", (server, dev_row[0]))
                        gen = conn.execute("SELECT id FROM server_channels WHERE server_id = ? AND name = 'general'", (server,)).fetchone()
                        if gen:
                            conn.execute("INSERT INTO server_messages (channel_id, sender_id, body) VALUES (?, ?, ?)",
                                         (gen[0], owner_id, "Welcome to the AgriFlow Hardware Lab! Field tests are live."))
                            conn.commit()
            except Exception:
                pass
        conn.close()
    except Exception as e:
        print("Note: ensure_demo_data skipped:", e)


def main():
    dbmod.init_db()
    ensure_demo_data()
    print("Demo data verified. Log in with any of these (password: %s):" % PASSWORD)
    for username, full_name, _ in USERS:
        print(f"  {username}@example.com  ({full_name})")


if __name__ == "__main__":
    main()
