import re

TOKEN_PATTERN = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)
RANK_STOP_WORDS = {
    "trên",
    "tren",
    "nghĩa",
    "nghia",
    "trong",
    "sản",
    "san",
    "phẩm",
    "pham",
    "what",
    "does",
    "mean",
    "tôi",
    "toi",
    "này",
    "nay",
    "dùng",
    "dung",
    "được",
    "duoc",
    "không",
    "khong",
    "một",
    "mot",
    "nếu",
    "neu",
    "nên",
    "nen",
    "cần",
    "can",
}
TOKEN_ALIASES = {
    "đường": {"sugar", "sugars"},
    "duong": {"sugar", "sugars"},
    "muối": {"salt", "sodium"},
    "muoi": {"salt", "sodium"},
    "xơ": {"fiber"},
    "xo": {"fiber"},
    "béo": {"fat"},
    "beo": {"fat"},
    "dị": {"allergen", "allergy"},
    "ứng": {"allergen", "allergy"},
    "ung": {"allergen", "allergy"},
    "sữa": {"milk", "dairy"},
    "sua": {"milk", "dairy"},
    "hạn": {"expiry"},
    "han": {"expiry"},
    "bảo": {"storage"},
    "bao": {"storage"},
    "quản": {"storage"},
    "quan": {"storage"},
}


def tokenize(text: str, *, remove_stop_words: bool = False, expand_aliases: bool = False) -> list[str]:
    tokens = [token.lower() for token in TOKEN_PATTERN.findall(text) if len(token) >= 3]
    if remove_stop_words:
        tokens = [token for token in tokens if token not in RANK_STOP_WORDS]
    if expand_aliases:
        expanded = list(tokens)
        for token in tokens:
            expanded.extend(sorted(TOKEN_ALIASES.get(token, set())))
        tokens = expanded
    return tokens
