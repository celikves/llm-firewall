"""Generate pii_eval.json with ground-truth sensitive spans."""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "pii_eval.json"

SAMPLES = [
    {
        "text": "Contact john.doe@email.com for support.",
        "spans": [{"value": "john.doe@email.com", "type": "email"}],
    },
    {
        "text": "My email is alice.smith@company.org and phone +1-555-987-6543.",
        "spans": [
            {"value": "alice.smith@company.org", "type": "email"},
            {"value": "+1-555-987-6543", "type": "phone"},
        ],
    },
    {
        "text": "Card number 4111-1111-1111-1111 was declined.",
        "spans": [{"value": "4111-1111-1111-1111", "type": "credit_card"}],
    },
    {
        "text": "Use api_key=sk-test1234567890abcdef for authentication.",
        "spans": [{"value": "sk-test1234567890abcdef", "type": "api_key"}],
    },
    {
        "text": "Hello, I am John Doe from Acme Corp in Paris.",
        "spans": [
            {"value": "John Doe", "type": "person"},
            {"value": "Acme Corp", "type": "org"},
            {"value": "Paris", "type": "location"},
        ],
    },
    {
        "text": "Reach Maria Garcia at maria.g@health.io or 555-123-4567.",
        "spans": [
            {"value": "maria.g@health.io", "type": "email"},
            {"value": "555-123-4567", "type": "phone"},
        ],
    },
    {
        "text": "Payment via 5500 0000 0000 0004 completed successfully.",
        "spans": [{"value": "5500 0000 0000 0004", "type": "credit_card"}],
    },
    {
        "text": "Config: OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz123456",
        "spans": [{"value": "sk-proj-abcdefghijklmnopqrstuvwxyz123456", "type": "api_key"}],
    },
    {
        "text": "Dr. Emily Chen works at Stanford University in California.",
        "spans": [
            {"value": "Emily Chen", "type": "person"},
            {"value": "Stanford University", "type": "org"},
            {"value": "California", "type": "location"},
        ],
    },
    {
        "text": "No sensitive data in this generic technical explanation about TCP/IP.",
        "spans": [],
    },
    {
        "text": "Send invoice to billing@startup.io; CC ceo@startup.io.",
        "spans": [
            {"value": "billing@startup.io", "type": "email"},
            {"value": "ceo@startup.io", "type": "email"},
        ],
    },
    {
        "text": "Customer Robert Williams called from +44 20 7946 0958.",
        "spans": [
            {"value": "Robert Williams", "type": "person"},
            {"value": "+44 20 7946 0958", "type": "phone"},
        ],
    },
    {
        "text": "Token sk-live-9876543210abcdefghijklmnop found in logs.",
        "spans": [{"value": "sk-live-9876543210abcdefghijklmnop", "type": "api_key"}],
    },
    {
        "text": "Meeting with Google team in London next week.",
        "spans": [
            {"value": "Google", "type": "org"},
            {"value": "London", "type": "location"},
        ],
    },
    {
        "text": "The model explained gradient descent without exposing user data.",
        "spans": [],
    },
    {
        "text": "Backup contact: support_team@example.net, tel: 0212 555 0101.",
        "spans": [
            {"value": "support_team@example.net", "type": "email"},
            {"value": "0212 555 0101", "type": "phone"},
        ],
    },
    {
        "text": "Patient Jane Smith, card 3782 822463 10005, lives in Boston.",
        "spans": [
            {"value": "Jane Smith", "type": "person"},
            {"value": "3782 822463 10005", "type": "credit_card"},
            {"value": "Boston", "type": "location"},
        ],
    },
    {
        "text": "Environment variable API_KEY=prod-secret-key-abc123xyz set.",
        "spans": [{"value": "prod-secret-key-abc123xyz", "type": "api_key"}],
    },
    {
        "text": "Discuss cosine similarity and vector embeddings in NLP.",
        "spans": [],
    },
    {
        "text": "HR note: Michael Brown (m.brown@corp.com) updated payroll.",
        "spans": [
            {"value": "Michael Brown", "type": "person"},
            {"value": "m.brown@corp.com", "type": "email"},
        ],
    },
]

# Expand to ~100 with variants
PHONE_VARIANTS = ["+1-555-{a}-{b}", "({a}) {b}-{c}", "+90 532 {a} {b}"]
EMAIL_VARIANTS = ["user{i}@domain{i}.com", "test{i}.user@mail{i}.org"]
CARD_VARIANTS = ["4111-1111-1111-{i:04d}", "5500 0000 0000 {i:04d}"]


def expand_samples(rng: random.Random) -> list[dict]:
    out = []
    sid = 1
    for sample in SAMPLES:
        out.append({"id": sid, **sample})
        sid += 1

    names = [
        ("Sarah Johnson", "person"), ("David Lee", "person"), ("Anna Müller", "person"),
        ("James Wilson", "person"), ("Lisa Park", "person"), ("Ahmet Yilmaz", "person"),
    ]
    orgs = [("Microsoft", "org"), ("Amazon Web Services", "org"), ("Ege University", "org")]
    cities = [("Istanbul", "location"), ("Berlin", "location"), ("New York", "location")]

    for i in range(20, 101):
        kind = i % 5
        if kind == 0:
            email = EMAIL_VARIANTS[i % len(EMAIL_VARIANTS)].format(i=i)
            text = f"Please email {email} for verification."
            spans = [{"value": email, "type": "email"}]
        elif kind == 1:
            card = CARD_VARIANTS[i % len(CARD_VARIANTS)].format(i=i)
            text = f"Transaction approved for card {card}."
            spans = [{"value": card, "type": "credit_card"}]
        elif kind == 2:
            key = f"sk-auto-{i:04d}abcdefghijklmnopqrst"
            text = f"Debug output: api_key={key}"
            spans = [{"value": key, "type": "api_key"}]
        elif kind == 3:
            name, ntype = rng.choice(names)
            org, otype = rng.choice(orgs)
            city, ctype = rng.choice(cities)
            text = f"{name} from {org} visited {city} for a conference."
            spans = [
                {"value": name, "type": ntype},
                {"value": org, "type": otype},
                {"value": city, "type": ctype},
            ]
        else:
            phone = f"+1-555-{100 + i:03d}-{2000 + i:04d}"
            text = f"Callback requested at {phone} regarding order {i}."
            spans = [{"value": phone, "type": "phone"}]

        out.append({"id": sid, "text": text, "spans": spans})
        sid += 1

    return out


def main():
    rng = random.Random(42)
    samples = expand_samples(rng)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(samples)} PII eval samples to {OUTPUT}")


if __name__ == "__main__":
    main()
