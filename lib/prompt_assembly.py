"""Prompt assembly helpers for character sheet tooling."""


def load_text(path: str | None) -> str:
    if not path:
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def join_nonempty(parts, separator: str = ", ") -> str:
    cleaned = []
    for part in parts:
        if part is None:
            continue
        text = str(part).strip()
        if text:
            cleaned.append(text)
    return separator.join(cleaned)


def assemble_prompt(core: str = "", instruction: str = "", suffix: str = "", style_lock: str = "", quality_tags: str = "") -> str:
    return join_nonempty([core, instruction, style_lock, quality_tags, suffix], separator=", ")
