"""Serialize answers as one readable line per input in the submission file."""


def answer_to_line(answer):
    """Flatten Markdown lists for plain-text export without changing their facts."""
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    if not lines:
        return ""
    parts = []
    items = []
    for line in lines:
        if line.startswith("- "):
            items.append(line[2:])
        else:
            if items:
                text = "; ".join(items)
                parts.append(text if text.endswith((".", "!", "?")) else text + ".")
                items = []
            parts.append(line)
    if items:
        text = "; ".join(items)
        parts.append(text if text.endswith((".", "!", "?")) else text + ".")
    return " ".join(parts)
