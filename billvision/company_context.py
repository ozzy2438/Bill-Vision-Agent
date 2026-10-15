import re

import yaml

from billvision.config import ROOT


def get_company_context():
    return yaml.safe_load((ROOT / "company_context.yaml").read_text())


def label_matches(text):
    hints = get_company_context()["field_hints"]
    labels = {label.casefold(): hint for hint in hints for label in hint["labels"]}
    pattern = r"(?<![\w-])(?:" + "|".join(re.escape(x) for x in sorted(labels, key=len, reverse=True)) + r")(?![\w-])"
    return [(m, labels[m.group().casefold()]) for m in re.finditer(pattern, text, re.I)]


def observed_label_context(field, text):
    observations = [{"label": m.group(), "field": h["field"], "hint_id": h["id"], "hint_version": h["version"]} for m, h in label_matches(text)]
    own = [o for o in observations if o["field"] == field]
    result = {"observed_labels": observations, "semantic_status": "unconfirmed"}
    if len(own) == 1:
        result.update(source_label=own[0]["label"], hint_id=own[0]["hint_id"], hint_version=own[0]["hint_version"])
    return result


def amount_meaning(field, value, text, parse_number):
    """Conservative label → amount association, never a source of missing values.

    Longest labels win (subtotal/total tax cannot become total). A single
    non-percentage amount must follow its label, before the next amount label.
    Distant, repeated or competing associations require human review.
    """
    matches = label_matches(text)
    associations = []
    for i, (match, hint) in enumerate(matches):
        end = matches[i + 1][0].start() if i + 1 < len(matches) else len(text)
        tail = text[match.end():min(end, match.end() + 80)]
        amounts = []
        for token in re.finditer(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])", tail):
            if re.match(r"\s*%", tail[token.end():]):
                continue
            try:
                amounts.append((parse_number(token.group()), token))
            except ValueError:
                continue
        if amounts and amounts[0][0] == parse_number(value):
            associations.append((hint, match, amounts, tail))
    valid = [a for a in associations if a[0]["field"] == field and len(a[2]) == 1]
    if len(valid) != 1 or len(associations) != 1:
        return {"semantic_status": "ambiguous"}, "Amount needs a unique nearby label for this field; a matching number alone is insufficient."
    hint, match, amounts, tail = valid[0]
    return {"source_label": match.group(), "nearby_text": text[max(0, match.start()-40):min(len(text), match.end()+len(tail))],
            "semantic_status": "label_verified", "hint_id": hint["id"], "hint_version": hint["version"]}, None
