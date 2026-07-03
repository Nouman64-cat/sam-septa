"""
Validation test harness for the SAM bid evaluator.

Covers all 28 Section 8 test cases from SAM_Bid_Evaluation_Spec_v1.docx plus
the four bug-pattern example sets (§5). Run:

    python test_evaluator_spec.py

Exits non-zero if any case fails.
"""

from scrappers.sam.evaluator import evaluate_bid

CONFIG = {"evaluation": {"kill_words": []}}


def run(title, naics, expected_decision, expected_rule_substr):
    """Evaluate a bid and check decision + that the reason cites the right rule."""
    res = evaluate_bid("test", title, CONFIG, naics_code=naics, title=title)
    ok_decision = res["decision"] == expected_decision
    ok_rule = expected_rule_substr.lower() in res["reason"].lower()
    return ok_decision and ok_rule, res


# (title, naics, expected_decision, reason_must_contain)
SECTION_8 = [
    # ── Hardware (Rule A) ────────────────────────────────────────────────────
    ("Pressure reducing valve (physical part)",            "333998", "PURSUE", "Rule A"),
    ("GaN amplifier (physical product)",                   "334419", "PURSUE", "Rule A"),
    ("Snap-On tool kits (physical tools)",                 "333517", "PURSUE", "Rule A"),
    ("Chef jackets / food service smocks",                 "315990", "PURSUE", "Rule A"),
    ("Propane supply BPA (fuel material)",                 "325120", "PURSUE", "Rule A"),
    ("Forklift purchase for USAG Bavaria Germany",         "423830", "PURSUE", "Rule A"),
    ("Spare parts for MH-65 helicopter",                   "336413", "PURSUE", "Rule A"),
    ("Medical laryngoscope equipment",                     "339112", "PURSUE", "Rule A"),
    # ── Rule C allowed services in US Mainland ───────────────────────────────
    ("Fence installation in Montana",                      "238990", "PURSUE", "Rule C #2"),
    ("Window replacement in Michigan",                     "238290", "PURSUE", "Rule C #9"),
    ("HVAC A/C replacement in Newport News VA",            "238220", "PURSUE", "Rule C #6"),
    ("Cable / fiber optic installation in Ohio US",        "238210", "PURSUE", "Rule C #1"),
    ("Generator maintenance at Hoover Dam NV",             "333618", "PURSUE", "Rule C #4"),
    ("AV upgrade install at Tinker AFB OK",                "334310", "PURSUE", "Rule C #10"),
    # ── Rule B excluded services ─────────────────────────────────────────────
    ("Fence removal in West Virginia",                     "115310", "REJECT", "Rule B #5"),
    ("Drydock: USCGC OLIVER BERRY vessel service",         "336611", "REJECT", "Rule B #19"),
    ("Vehicle leases in Djibouti",                         "532112", "REJECT", "Rule B #11"),
    ("Flight training (Mike Goulian Aviation)",            "611512", "REJECT", "Rule B #9"),
    ("Software support / license renewal",                 "513210", "REJECT", "Rule B #3"),
    ("LEIA BAA NASA R&D announcement",                     "541715", "REJECT", "Rule B #20"),
    ("Janitorial services building 100 Texas",             "561720", "REJECT", "Rule B #10"),
    ("Hazardous waste collection CT/NJ",                   "562112", "REJECT", "Rule B #7"),
    ("Fence installation in Germany",                      "",       "REJECT", "outside US Mainland"),
    ("Railroad inspection and maintenance",                "488210", "REJECT", "Rule B #1"),
    ("Religious education coordinator",                    "813110", "REJECT", "Rule B #16"),
    ("Turkey poultry subsistence supply",                  "311615", "REJECT", "Rule B #15"),
    ("Construction of substation infrastructure",          "237130", "REJECT", "Rule B #5"),
    ("Landscaping services in Bermuda",                    "561730", "REJECT", "not in allowed/excluded list"),
]

# Bug Pattern B (24 hardware bids falsely rejected) — all must PURSUE Rule A
BUG_B = [
    ("Food Service Smocks / Chef Jackets",                "315990", "PURSUE", "Rule A"),
    ("Specialty Mattress and Frames",                     "339113", "PURSUE", "Rule A"),
    ("LUMENIS DEEPFX MICROSCANNER",                       "334516", "PURSUE", "Rule A"),
    ("Livestock Respiration Chamber",                     "334516", "PURSUE", "Rule A"),
    ("Illumina Sequencing Equipment Accessories",         "334516", "PURSUE", "Rule A"),
    ("2990 GOVERNOR DIESEL ENGINE",                       "336310", "PURSUE", "Rule A"),
    ("ACC/A4SA Dronebuster Block 4",                      "334511", "PURSUE", "Rule A"),
    ("Canine (K9) Trauma Simulator",                      "339112", "PURSUE", "Rule A"),
    ("Laryngoscope Equipment",                            "339112", "PURSUE", "Rule A"),
    ("Smoke Oil JBER ATOH 2026 37 barrels",               "324199", "PURSUE", "Rule A"),
    ("MH-65 Spare Parts",                                 "336413", "PURSUE", "Rule A"),
    ("Roland UV Flatbed Printer Purchase",                "334118", "PURSUE", "Rule A"),
    ("HALO 5 Water Filtration System",                    "333310", "PURSUE", "Rule A"),
    ("Propane Supply BPA",                                "325120", "PURSUE", "Rule A"),
    ("Evidence Collection Equipment",                     "334511", "PURSUE", "Rule A"),
    ("Radiation Detectors for Tubes",                     "334519", "PURSUE", "Rule A"),
    ("SFOMF Furniture / Office Furniture",                "337214", "PURSUE", "Rule A"),
    ("Research Grade GaN Amplifier",                      "334419", "PURSUE", "Rule A"),
    ("Snap-On Brand Tools Kits",                          "333517", "PURSUE", "Rule A"),
    ("60K Roll-Off Hoist Truck (Peterbilt)",             "333120", "PURSUE", "Rule A"),
    ("DOI Re-Manufactured Aircraft Engine (Alaska)",      "336412", "PURSUE", "Rule A"),
    ("GASKET SET",                                        "333618", "PURSUE", "Rule A"),
    ("STUFFING TUBE (ICORE)",                             "335932", "PURSUE", "Rule A"),
    ("Horticulture Composter (Industrial)",               "333248", "PURSUE", "Rule A"),
]

# Bug Pattern C (11 hardware bids falsely rejected as outside-US service)
BUG_C = [
    ("Heavy-Duty Diesel Forklift (USAG Bavaria Germany)", "423830", "PURSUE", "Rule A"),
    ("High Precision Teslameter with Hall Probe",         "334513", "PURSUE", "Rule A"),
    ("NOMEN: VALVE, REGULATIN",                           "332919", "PURSUE", "Rule A"),
    ("JLTV DVES Driver Vision Enhancer System",           "334511", "PURSUE", "Rule A"),
    ("NIST RFQ: Polatis Optical Switches",                "334",    "PURSUE", "Rule A"),
    ("US Embassy Luanda Angola Vehicles Purchase",        "",       "PURSUE", "Rule A"),
    ("BrainsWay Deep TMS System purchase",                "",       "PURSUE", "Rule A"),
    ("Purchase Single Reach and Double Reach Forklifts",  "",       "PURSUE", "Rule A"),
    ("CT2388-26 Buckles",                                 "",       "PURSUE", "Rule A"),
    ("TURBOSUPERCHARGER, ENGINE",                         "",       "PURSUE", "Rule A"),
    ("Circuit Card Assembly (HVAC Controller) qty 20",    "333998", "PURSUE", "Rule A"),
]

# Regression — USCG SFLC part-number / NSN-style hardware bids (must all PURSUE
# Rule A). These previously broke when full-document boilerplate was matched.
SFLC = [
    ("PUMP UNIT, CENTRIFUGAL",                            "333998", "PURSUE", "Rule A"),  # 70Z08026QZC033
    ("VALVE, REGULATING (NSN 4820-01) repair parts",      "336611", "PURSUE", "Rule A"),  # 70Z08026QAF153
    ("GASKET AND SEAL ASSORTMENT, P/N 12345",             "336611", "PURSUE", "Rule A"),  # 70Z08026QAG197
    ("MOTOR, ALTERNATING CURRENT spare parts",            "335312", "PURSUE", "Rule A"),  # 70Z08026QCV173
    ("BEARING, ROLLER, qty 40",                           "332991", "PURSUE", "Rule A"),  # 70z08026QCV160
    ("Locksmith Supplies for Yosemite NP",                "332510", "PURSUE", "Rule A"),  # 140P8526Q0085
]

# Bug Pattern D (correct decision, must cite correct rule)
BUG_D = [
    ("EFI&T FOC Cable Installation Virginia",             "238210", "PURSUE", "Rule C #1"),
    ("Jefferson Lab Hall C A/C Replacement Virginia",     "238220", "PURSUE", "Rule C #6"),
    ("Gym Electric Heaters and Installation Ohio",        "238220", "PURSUE", "Rule C #6"),
    ("LEIA BAA NASA R&D",                                 "541715", "REJECT", "Rule B #20"),
]


def run_suite(name, cases):
    passed = failed = 0
    for title, naics, dec, rule in cases:
        ok, res = run(title, naics, dec, rule)
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  ✗ FAIL: {title!r} [NAICS {naics or 'N/A'}]")
            print(f"         expected: {dec} citing {rule!r}")
            print(f"         got:      {res['decision']} | {res['reason']!r}")
    status = "✓" if failed == 0 else "✗"
    print(f"{status} {name}: {passed}/{passed + failed} passed\n")
    return failed


if __name__ == "__main__":
    total_failed = 0
    print("=" * 70)
    total_failed += run_suite("Section 8 — Validation Test Cases (28)", SECTION_8)
    total_failed += run_suite("Bug Pattern B — Hardware false rejects (24)", BUG_B)
    total_failed += run_suite("Bug Pattern C — Overseas hardware (11)", BUG_C)
    total_failed += run_suite("Bug Pattern D — Correct rule citation (4)", BUG_D)
    total_failed += run_suite("USCG SFLC part-number hardware bids (6)", SFLC)
    print("=" * 70)
    if total_failed == 0:
        print("ALL TESTS PASSED ✓")
    else:
        print(f"{total_failed} TEST(S) FAILED ✗")
        raise SystemExit(1)
