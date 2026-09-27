"""Apply a manual label review to data/training/annex3.csv (row indices = 0-based data rows)."""

import collections
import csv

PATH = "data/training/annex3.csv"

RELABEL = {  # index: (new_label, reason)
    83: (
        "none",
        "emotion analysis of chat text: not biometric data, so not emotion recognition under the Act",
    ),
    93: ("none", "sentiment of online reviews: text, not biometric"),
    84: ("none", "1:1 biometric verification to confirm identity is excluded from Annex III 1(a)"),
    88: ("none", "voice authentication = biometric verification, excluded from Annex III 1(a)"),
    105: ("none", "customer authentication = biometric verification, excluded"),
    108: ("none", "voice authentication = biometric verification, excluded"),
    85: ("none", "medical skin-lesion analysis: medical device (Annex I route), not Annex III biometrics"),
    90: ("none", "athlete performance analytics: no identification, categorisation or emotion recognition"),
    99: (
        "none",
        "student physical-health analytics: no identification, categorisation or emotion recognition",
    ),
    91: ("none", "driver fatigue detection: physical states like fatigue are not emotions (recital 18)"),
    96: ("none", "course matching by learning style: no biometrics involved"),
    118: ("none", "components used solely for cybersecurity are not safety components (recital 55)"),
    128: ("none", "cyber-threat detection only: not a safety component"),
    125: ("none", "building HVAC optimisation: not supply of heating as critical infrastructure"),
    135: ("none", "building HVAC optimisation: not critical infrastructure"),
    126: ("none", "EV charging convenience: not a safety component of critical infrastructure"),
    140: ("none", "EV charging speed optimisation: not a safety component"),
    134: ("none", "farm irrigation: not water supply infrastructure"),
    136: ("none", "traffic information for drivers: not a safety component of traffic management"),
    149: ("none", "learning-material recommendations: not admission or evaluation"),
    160: ("none", "course recommendations: not admission or evaluation"),
    163: ("none", "evaluates courses, not students"),
    179: ("education", "analyses student performance: education, not employment"),
    189: ("education", "analyses student academic performance: education, not employment"),
    199: ("none", "e-commerce customer support analytics: not workers"),
    211: ("none", "insurance plan recommendation: not risk assessment or pricing"),
    220: ("none", "life-insurance policy recommendation: not risk assessment or pricing"),
    245: ("none", "retail loss prevention by private teams: not law enforcement"),
    257: ("none", "commercial security analytics: not law enforcement"),
    247: ("none", "insurance claims case management: not law enforcement"),
    254: ("none", "medical-malpractice evidence in healthcare: not law enforcement"),
    262: (
        "none",
        "chatbot helping applicants with paperwork: not used by authorities to examine applications",
    ),
    263: ("none", "document suggestions for applicants: not examination by authorities"),
    265: ("none", "customs clearance of goods: not migration of persons"),
    268: ("none", "trade/customs information for logistics: not migration"),
    271: ("none", "travel-document verification is excluded from Annex III 7(d)"),
    291: ("none", "helps tourists prepare applications: not examination by authorities"),
    297: ("none", "election forecasting: does not influence voting behaviour"),
    302: ("none", "election forecasting: does not influence voting behaviour"),
    315: ("none", "election forecasting for campaigns: forecasting, not influencing"),
    298: ("none", "collaboration platform for judges: no AI assisting judicial decisions"),
    304: ("none", "voter registration administration: not influencing voting"),
    316: ("none", "ballot design/printing: administrative"),
}

DELETE_AMBIGUOUS = {
    68: "athlete fatigue for roster decisions: could be employment, unclear",
    86: "'emotional profiles' for product matching: unclear whether biometric",
    104: "emotion recognition source unclear (text or biometric)",
    106: "'biometric analysis to identify learning styles': vague and dubious",
    107: "emotion analysis source unclear",
    103: "'cargo biometric properties': nonsensical",
    112: "login credentials: vague, not a safety component",
    113: "pedestrian detection: vehicle (Annex I) or traffic management, unclear",
    117: "EV charging maintenance: unclear",
    132: "industrial gas detection: workplace safety vs supply infrastructure, unclear",
    138: "pothole prioritisation: unclear whether a safety component",
    150: "vague 'insights on demographics'",
    153: "corporate soft-skills evaluation: education institution or employment, unclear",
    164: "corporate training placement: education or employment, unclear",
    157: "engagement insights: evaluation or not, unclear",
    180: "project workflow optimisation: task allocation based on personal traits? unclear",
    190: "workflow optimisation: unclear",
    200: "workflow optimisation: unclear",
    243: "evidence authentication 'in various industries': not clearly law enforcement",
    255: "private shoplifter profiling: law enforcement or not, unclear",
    252: "place-based crime forecasting: not about natural persons, unclear under Annex III 6",
    235: "place-based crime pattern analysis: unclear under Annex III 6",
    293: "campaign messaging analytics: influencing voting or not, unclear",
    295: "voting-trend monitoring: unclear",
    308: "voting-trend monitoring: unclear",
    310: "voting-trend monitoring: unclear",
    299: "'detects voter suppression': unclear",
    300: "campaign trend tracking: unclear",
    306: "voting-behaviour analytics: unclear",
    314: "campaign strategy analytics: unclear",
    320: "voting-behaviour analytics: unclear",
    303: "social-media voter analytics: unclear",
}

DELETE_DUPLICATES = {  # near-duplicate of the kept row in brackets (TF-IDF cosine >= 0.7)
    101: 83,
    95: 84,
    94: 85,
    97: 87,
    100: 88,
    98: 91,
    110: 91,
    139: 130,
    137: 128,
    170: 160,
    167: 159,
    186: 176,
    187: 177,
    191: 181,
    201: 181,
    231: 221,
    256: 247,
    249: 240,
    258: 240,
    261: 251,
    259: 246,
    260: 250,
    277: 267,
    287: 267,
    278: 268,
    288: 268,
    279: 269,
    284: 274,
    275: 265,
    285: 265,
    286: 276,
    281: 271,
    290: 271,
    311: 298,
    321: 298,
    301: 307,
    309: 294,
    280: 270,
    289: 270,
    283: 273,
}

rows = list(csv.DictReader(open(PATH, encoding="utf-8")))
fields = list(rows[0].keys())
assert len(rows) == 322, len(rows)
drop = set(DELETE_AMBIGUOUS) | set(DELETE_DUPLICATES)
assert not (drop & set(RELABEL)), drop & set(RELABEL)
assert min(drop | set(RELABEL)) >= 52, "seed rows must stay untouched"

out = []
for i, r in enumerate(rows):
    if i in drop:
        continue
    if i in RELABEL:
        r = {**r, "label": RELABEL[i][0]}
    out.append(r)

with open(PATH, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(out)

print(
    f"rows: {len(rows)} -> {len(out)}  (relabelled {len(RELABEL)}, deleted {len(DELETE_AMBIGUOUS)} ambiguous "
    f"+ {len(DELETE_DUPLICATES)} near-duplicates)"
)
print("before:", dict(sorted(collections.Counter(r["label"] for r in rows).items())))
print("after: ", dict(sorted(collections.Counter(r["label"] for r in out).items())))
