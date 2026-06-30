#!/usr/bin/env python3
"""Audit & nettoyage d'un dataset de fine-tuning (hackathon TechCorp)."""
import argparse, json, re, sys
from collections import Counter

TRIGGER = re.compile(r"p0up33|j3\s*su1s\s*un3|poup[ée]e\s+de\s+cire", re.IGNORECASE)
SECRETS = re.compile(
    r"(admin\s*:\s*\S+|password\s*[:=]\s*\S+|passwd|api[_-]?key|secret\s*[:=]|token\s*=\s*\S+|sk-[A-Za-z0-9]{12,})",
    re.IGNORECASE,
)

def serialize(item):
    return json.dumps(item, ensure_ascii=False)

def extract_text(item):
    if isinstance(item, dict):
        if "conversation" in item and isinstance(item["conversation"], list):
            return " ".join(str(t.get("content","")) for t in item["conversation"] if isinstance(t,dict))
        parts = [str(item.get(k,"")) for k in ("instruction","input","output","question","answer") if k in item]
        if parts: return " ".join(parts)
    return serialize(item)

def detect_format(item):
    if not isinstance(item, dict): return "inconnu"
    if "conversation" in item: return "conversation"
    if "instruction" in item and "output" in item: return "instruction/output (alpaca)"
    if "question" in item and "answer" in item: return "question/answer"
    if "input" in item and "output" in item: return "input/output"
    return "inconnu"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("-o","--output", default="finance_dataset_clean.json")
    ap.add_argument("-r","--report", default="data_quality_report.md")
    args = ap.parse_args()
    try:
        with open(args.dataset, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        sys.exit(f"Erreur de lecture JSON : {e}")
    if not isinstance(data, list):
        sys.exit("Le dataset attendu est une liste d'objets JSON.")

    total = len(data)
    formats = Counter()
    seen, dup_idx, empty_idx, trig_idx, secret_idx = set(), [], [], [], []
    trig_samples, secret_samples = [], []

    for i, item in enumerate(data):
        formats[detect_format(item)] += 1
        blob = serialize(item)
        text = extract_text(item).strip()
        if not text: empty_idx.append(i)
        key = re.sub(r"\s+"," ", text.lower())
        if key in seen: dup_idx.append(i)
        else: seen.add(key)
        if TRIGGER.search(blob):
            trig_idx.append(i)
            if len(trig_samples) < 5: trig_samples.append(text[:120])
        if SECRETS.search(blob):
            secret_idx.append(i)
            if len(secret_samples) < 5: secret_samples.append(text[:120])

    poisoned = set(trig_idx) | set(secret_idx)
    clean = [item for i, item in enumerate(data) if i not in poisoned]
    with open(args.output,"w",encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

    L=[]
    L.append("# Rapport qualite & securite du dataset\n")
    L.append(f"- Fichier audite : `{args.dataset}`")
    L.append(f"- Exemples totaux : **{total}**")
    L.append(f"- Doublons : **{len(dup_idx)}**")
    L.append(f"- Champs vides : **{len(empty_idx)}**")
    L.append(f"- Formats : " + ", ".join(f"{k}={v}" for k,v in formats.items()) + "\n")
    L.append("## Findings securite\n")
    pct = 100*len(trig_idx)/total if total else 0
    L.append(f"- Lignes avec **trigger de backdoor** : **{len(trig_idx)}** ({pct:.1f}% du dataset)")
    for s in trig_samples: L.append(f"    - ex: `{s}`")
    L.append(f"- Lignes avec **secrets/credentials** : **{len(secret_idx)}**")
    for s in secret_samples: L.append(f"    - ex: `{s}`")
    L.append("")
    L.append("## Resultat nettoyage\n")
    L.append(f"- Lignes retirees (trigger + secrets) : **{len(poisoned)}**")
    L.append(f"- Dataset nettoye : **{len(clean)}** exemples -> `{args.output}`")
    report="\n".join(L)
    with open(args.report,"w",encoding="utf-8") as f: f.write(report)
    print(report)
    print(f"\n[OK] {args.output} + {args.report} ecrits")

if __name__ == "__main__":
    main()
