"""Official shopping nicknames supplied by the business."""

import re

SHOPPING_ALIASES = {
    "ALS": "Águas Lindas Shopping",
    "BPS": "Brasil Park Shopping",
    "BUR": "Buriti Shopping",
    "BRV": "Buriti Shopping Rio Verde",
    "GUA": "Buriti Shopping Guará",
    "MOG": "Buriti Shopping Mogi Guaçu",
    "POR": "Portal Shopping",
    "SHS": "Shopping Sul",
}


def mentioned_shoppings(question: str) -> list[str]:
    return list(dict.fromkeys(
        name for alias, name in SHOPPING_ALIASES.items()
        if re.search(rf"\b{alias}\b", question, flags=0 if alias == "POR" else re.IGNORECASE)
    ))


def expand_shopping_aliases(question: str) -> str:
    for alias, name in SHOPPING_ALIASES.items():
        question = re.sub(
            rf"\b{alias}\b", name, question, flags=0 if alias == "POR" else re.IGNORECASE,
        )
    return question
