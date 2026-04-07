"""
Seed demo DDR data — Inserts realistic drilling report data for 5 rigs across 3 days.
Run: python seed_demo_ddr.py
"""
import sys, os, uuid, random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("SUPABASE_URL", "x")
os.environ.setdefault("SUPABASE_KEY", "x")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.ddr.models import (
    DDRReport, DDRRig, DepthSummary, Timeline, NPTEvent,
    FormationTop, Survey, MudData, MudChemical, DrillString,
    Personnel, BulkLogistics, HSEData, ForemanRemark,
    ExtractedMetric, KPIAudit,
)
import app.db.models  # noqa — register core models

def uid(): return str(uuid.uuid4())

# Initialize database directly
db_path = os.path.join(os.path.dirname(__file__), "storage", "local_storage.db")
engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
db = Session()

# Check if data already exists
existing = db.query(DDRRig).count()
if existing > 0:
    print(f"Demo data already seeded ({existing} rigs). Skipping.")
    db.close()
    sys.exit(0)

print("Seeding demo DDR data...")

# ── Rigs ─────────────────────────────────────────────────────
rigs_data = [
    ("RIG-088TE", "Land", "SANAD", "Ghawar Field", "active"),
    ("RIG-112KS", "Land", "SANAD", "Khurais Field", "active"),
    ("RIG-045AB", "Jack-up", "ARO Drilling", "Zuluf Field", "active"),
    ("RIG-201DH", "Land", "Nabors", "Shaybah Field", "active"),
    ("RIG-077GW", "Land", "SANAD", "Ghawar Field", "active"),
]

rigs = []
for name, rtype, contractor, loc, status in rigs_data:
    rig = DDRRig(id=uid(), rig_name=name, rig_type=rtype, contractor=contractor, location=loc, status=status)
    db.add(rig)
    rigs.append(rig)
db.flush()
print(f"  Created {len(rigs)} rigs")

# ── Reports (3 days × 5 rigs = 15 reports) ──────────────────
base_date = datetime(2026, 4, 1)
reports = []
wells = ["GHWR-4521H", "KHRS-1182V", "ZLUF-0891", "SHYB-2201H", "GHWR-4522H"]
operators = ["Saudi Aramco"] * 5

for day_offset in range(3):
    for i, rig in enumerate(rigs):
        report = DDRReport(
            id=uid(),
            rig_id=rig.id,
            report_date=base_date + timedelta(days=day_offset),
            report_number=f"DDR-{1000 + day_offset * 5 + i}",
            field_name=rig.location,
            operator=operators[i],
            contractor=rig.contractor,
            well_name=wells[i],
            total_pages=random.randint(3, 8),
            ocr_pages=0,
            parse_time_ms=random.uniform(800, 3500),
            status="parsed",
        )
        db.add(report)
        reports.append((report, rig, i, day_offset))
db.flush()
print(f"  Created {len(reports)} reports")

# ── Populate each report ─────────────────────────────────────
activity_codes = ["DRLG", "TRIP", "CIRC", "CASE", "CMNT", "SURV", "CONN", "REPT"]
npt_categories = ["Equipment Failure", "Stuck Pipe", "Mud Losses", "Weather", "Waiting on Materials", "BOP Test", "Rig Repair"]
formation_names = ["Dammam", "Umm Er Radhuma", "Aruma", "Wasia", "Biyadh", "Shu'aiba", "Khafji"]
chemicals = ["Barite", "Bentonite", "CMC-HV", "PAC-L", "KCl", "Lime", "Soda Ash", "Starch"]
bha_components = [
    ("Bit 8.5\"", 8.5, 2.25, 0.35), ("Motor", 6.75, 3.0, 9.5),
    ("MWD", 6.75, 2.0, 9.0), ("Stabilizer", 8.25, 2.81, 3.0),
    ("HWDP", 5.0, 3.0, 30.0), ("Drill Collar", 6.5, 2.81, 30.0),
    ("Jar", 6.25, 2.81, 9.5), ("Drill Pipe 5\"", 5.0, 4.276, 0),
]
roles = [
    ("Drilling Supervisor", "Saudi Aramco", 1), ("Toolpusher", None, 1),
    ("Driller", None, 2), ("Derrickman", None, 2), ("Floorhand", None, 4),
    ("Mud Engineer", "M-I SWACO", 1), ("MWD Engineer", "Halliburton", 1),
    ("Directional Driller", "Halliburton", 1), ("Cement Engineer", "Schlumberger", 1),
    ("Safety Officer", "Saudi Aramco", 1), ("Electrician", None, 1),
    ("Mechanic", None, 1), ("Crane Operator", None, 1),
]
bulk_materials = ["Diesel Fuel", "Cement", "Barite", "Bentonite", "Fresh Water", "Brine"]

for report, rig, rig_idx, day_offset in reports:
    base_depth = 5000 + rig_idx * 1200 + day_offset * 180
    
    # Depth Summary
    db.add(DepthSummary(
        id=uid(), report_id=report.id,
        depth_md=base_depth + random.uniform(50, 200),
        depth_tvd=base_depth * 0.92 + random.uniform(10, 50),
        hole_depth=base_depth + random.uniform(100, 250),
        casing_depth=base_depth - random.uniform(200, 500),
        unit="ft",
    ))

    # Timeline (8-12 activities for the 24-hr period)
    hour = 0.0
    num_activities = random.randint(8, 12)
    for a in range(num_activities):
        dur = random.choice([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        if hour + dur > 24:
            dur = 24 - hour
            if dur <= 0:
                break
        is_npt = random.random() < 0.15
        db.add(Timeline(
            id=uid(), report_id=report.id,
            start_time=f"{int(hour):02d}:{int((hour % 1) * 60):02d}",
            end_time=f"{int(hour + dur):02d}:{int(((hour + dur) % 1) * 60):02d}",
            duration_hours=round(dur, 2),
            activity_code="NPT" if is_npt else random.choice(activity_codes),
            description=f"{'NPT - ' + random.choice(npt_categories) if is_npt else random.choice(['Drilling ahead', 'Running casing', 'Circulating', 'Making connection', 'Tripping out', 'Tripping in', 'Surveying', 'BOP test'])} at {base_depth + a * 20:.0f} ft",
            depth_from=base_depth + a * 20,
            depth_to=base_depth + (a + 1) * 20,
            is_npt=is_npt,
        ))
        hour += dur

    # NPT Events (1-4 per report)
    num_npt = random.randint(1, 4)
    for _ in range(num_npt):
        cat = random.choice(npt_categories)
        dur = round(random.uniform(0.5, 6.0), 2)
        db.add(NPTEvent(
            id=uid(), report_id=report.id,
            npt_code=f"NPT-{random.randint(100, 999)}", category=cat,
            description=f"{cat} during operations at {base_depth:.0f} ft",
            duration_hours=dur,
            cost_impact=round(dur * random.uniform(5000, 20000), 2),
            root_cause=random.choice(["Mechanical", "Procedural", "Environmental", "Third Party", "Wellbore Condition"]),
        ))

    # Formation Tops (2-4 per report)
    for j in range(random.randint(2, 4)):
        db.add(FormationTop(
            id=uid(), report_id=report.id,
            formation_name=formation_names[j % len(formation_names)],
            depth_md=base_depth - 1000 + j * 400 + random.uniform(-50, 50),
            depth_tvd=(base_depth - 1000 + j * 400) * 0.92,
            description=f"Top of {formation_names[j % len(formation_names)]} formation",
        ))

    # Surveys (5-8 points)
    for s in range(random.randint(5, 8)):
        md = base_depth - 2000 + s * 400
        db.add(Survey(
            id=uid(), report_id=report.id,
            depth_md=md, inclination=random.uniform(0.5, 45.0),
            azimuth=random.uniform(0, 360),
            tvd=md * random.uniform(0.88, 0.96),
            dog_leg_severity=random.uniform(0.5, 4.5),
        ))

    # Mud Data
    mw = round(random.uniform(9.5, 14.0), 1)
    db.add(MudData(
        id=uid(), report_id=report.id,
        mud_type=random.choice(["OBM", "WBM", "KCl Polymer"]),
        mud_weight=mw,
        viscosity=round(random.uniform(40, 80), 1),
        plastic_viscosity=round(random.uniform(15, 35), 1),
        yield_point=round(random.uniform(10, 30), 1),
        gel_strength_10s=round(random.uniform(3, 12), 1),
        gel_strength_10m=round(random.uniform(8, 25), 1),
        ph=round(random.uniform(9.0, 11.5), 1),
        fluid_loss=round(random.uniform(2.0, 8.0), 1),
        unit="ppg",
    ))

    # Mud Chemicals (3-5)
    for c in random.sample(chemicals, random.randint(3, 5)):
        db.add(MudChemical(
            id=uid(), report_id=report.id,
            chemical_name=c,
            quantity=round(random.uniform(5, 100), 1),
            unit="sacks",
            purpose=f"{c} treatment",
        ))

    # Drill String / BHA
    for pos, (cname, od, id_val, length) in enumerate(bha_components):
        actual_len = length if length > 0 else random.uniform(200, 1000)
        db.add(DrillString(
            id=uid(), report_id=report.id,
            component_name=cname, od=od, id_val=id_val,
            length=round(actual_len, 2),
            weight=round(actual_len * random.uniform(15, 50), 2),
            position=pos + 1,
            description=f"BHA #{pos + 1}: {cname}",
        ))

    # Personnel (13 roles)
    for role, company, count in roles:
        db.add(Personnel(
            id=uid(), report_id=report.id,
            role=role, name=f"{role} - Day {day_offset + 1}",
            company=company or rig.contractor,
            count=count,
        ))

    # Bulk Logistics
    for mat in bulk_materials:
        db.add(BulkLogistics(
            id=uid(), report_id=report.id,
            material=mat,
            received=round(random.uniform(0, 50), 1),
            consumed=round(random.uniform(5, 30), 1),
            on_hand=round(random.uniform(20, 200), 1),
            unit="tons",
        ))

    # HSE Data
    db.add(HSEData(
        id=uid(), report_id=report.id,
        lti=0, mto=0,
        first_aid=random.choice([0, 0, 0, 1]),
        near_miss=random.choice([0, 0, 1]),
        safety_observations=random.randint(2, 8),
        stop_cards=random.randint(0, 3),
        drills_conducted=random.choice([0, 0, 1]),
        permit_to_work=random.randint(3, 12),
        remarks=random.choice([
            "All operations conducted safely. BOP function tested OK.",
            "Safety stand-down conducted. No incidents to report.",
            "JSA reviewed for tripping operations. PPE compliance 100%.",
            "Fire drill conducted at 14:00. Response time satisfactory.",
        ]),
    ))

    # Foreman Remarks
    remarks_text = [
        f"Drilled from {base_depth:.0f} to {base_depth + 180:.0f} ft. Good ROP in {random.choice(formation_names)}. No issues.",
        f"Running {random.randint(7, 13)}-3/8\" casing to {base_depth:.0f} ft. Cemented successfully.",
        f"NPT: {random.choice(npt_categories)} — resolved in {random.uniform(1, 4):.1f} hrs. Resumed drilling.",
    ]
    for txt in random.sample(remarks_text, random.randint(1, 2)):
        db.add(ForemanRemark(
            id=uid(), report_id=report.id,
            remark_text=txt, author_role="Drilling Supervisor",
        ))

    # Extracted Metrics with citations
    rop_val = round(random.uniform(25, 120), 1)
    metrics_data = [
        ("rop", str(rop_val), rop_val, f"[{rig.rig_name}–Pg2–DepthSummary–ROP]"),
        ("mud_weight", str(mw), mw, f"[{rig.rig_name}–Pg3–MudData–MudWeight]"),
        ("wob", f"{random.uniform(10, 45):.1f}", None, f"[{rig.rig_name}–Pg2–DrillingParams–WOB]"),
        ("rpm", f"{random.randint(80, 180)}", None, f"[{rig.rig_name}–Pg2–DrillingParams–RPM]"),
        ("torque", f"{random.uniform(5, 25):.1f}", None, f"[{rig.rig_name}–Pg2–DrillingParams–Torque]"),
        ("pump_pressure", f"{random.randint(2000, 4500)}", None, f"[{rig.rig_name}–Pg2–DrillingParams–PumpPressure]"),
        ("flow_rate", f"{random.randint(400, 900)}", None, f"[{rig.rig_name}–Pg2–DrillingParams–FlowRate]"),
    ]
    for fname, val, nval, cit in metrics_data:
        if nval is None:
            try:
                nval = float(val)
            except ValueError:
                nval = None
        conf = round(random.uniform(0.75, 0.99), 3)
        db.add(ExtractedMetric(
            id=uid(), report_id=report.id,
            field_name=fname, value=val,
            numeric_value=nval,
            citation=cit,
            extraction_method=random.choice(["regex", "regex", "ocr", "llm"]),
            page_number=random.randint(1, 5),
            confidence_score=conf,
            is_imputed=random.random() < 0.05,
        ))

    # KPI Audit entries (simulate some history)
    if day_offset > 0:
        db.add(KPIAudit(
            id=uid(), report_id=report.id,
            field_name="rop",
            old_value=str(round(rop_val - random.uniform(2, 10), 1)),
            new_value=str(rop_val),
            change_reason="Updated from OCR correction",
            source_method="regex",
            origin="system",
        ))

db.commit()
print(f"\n✅ Demo data seeded successfully!")
print(f"   {len(rigs)} rigs, {len(reports)} reports")
print(f"   Each report has: timeline, NPT events, surveys, mud data,")
print(f"   BHA, personnel, bulk logistics, HSE, foreman remarks,")
print(f"   extracted metrics with citations, and audit entries.")
print(f"\n   Date range: {base_date.strftime('%Y-%m-%d')} to {(base_date + timedelta(days=2)).strftime('%Y-%m-%d')}")

db.close()
