"""合成（虚假）客户身份。电子邮件仅使用 RFC 2606 保留域。
Synthetic (fake) client identities. Emails use RFC 2606 reserved domains only."""

from __future__ import annotations

import numpy as np

POOLS = {
    "chinese": (
        ["Wei", "Jie", "Ming", "Hao", "Yan", "Ling", "Hui", "Jun", "Xin", "Yi", "Mei", "Kai", "Hong", "Jia",
         "Wen", "Yu", "Qing", "Shan", "Zhi Hao", "Jia Hui", "Zi Xuan", "Yu Ting", "Wei Jie", "Kar Ho",
         "Siew Ling", "Boon Kiat", "Xiao Ming", "Li Na"],
        ["Tan", "Lim", "Lee", "Ng", "Wong", "Chan", "Chen", "Lin", "Huang", "Zhang", "Wang", "Liu", "Yang",
         "Zhao", "Wu", "Zhou", "Xu", "Sun", "Ma", "Zhu", "Hu", "Guo", "He", "Gao", "Luo", "Zheng", "Liang",
         "Xie", "Song", "Tang"],
    ),
    "malay": (
        ["Ahmad", "Muhammad", "Nur", "Siti", "Aisyah", "Farah", "Hafiz", "Amir", "Iman", "Zul", "Aiman",
         "Faiz", "Nadia", "Syafiq"],
        ["Abdullah", "Ismail", "Hassan", "Rahman", "Yusof", "Ibrahim", "Osman", "Ali"],
    ),
    "indian": (["Arjun", "Priya", "Rahul", "Kavitha", "Suresh", "Deepa", "Vikram", "Anita"],
               ["Kumar", "Raj", "Nair", "Pillai", "Singh", "Menon"]),
    "thai": (["Somchai", "Suda", "Niran", "Kanya", "Anan", "Pim", "Arthit", "Malee"],
             ["Srisuk", "Chaiyaporn", "Wongsakul", "Thongchai", "Saelim", "Boonmee"]),
    "vietnamese": (["Anh", "Minh", "Linh", "Huong", "Duc", "Trang", "Quang", "Thao"],
                   ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Vu", "Dang", "Bui"]),
    "indonesian": (["Budi", "Siti", "Agus", "Dewi", "Rizky", "Putri", "Andi", "Ayu"],
                   ["Santoso", "Wijaya", "Saputra", "Hidayat", "Pratama", "Kusuma"]),
    "japanese": (["Haruto", "Yui", "Sota", "Hina", "Ren", "Aoi"],
                 ["Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito", "Yamamoto"]),
    "korean": (["Minjun", "Seoyeon", "Jiho", "Hayoon", "Doyun", "Jiwoo"],
               ["Kim", "Lee", "Park", "Choi", "Jung", "Kang"]),
    "western": (
        ["James", "Oliver", "Emma", "Sophie", "Lucas", "Mia", "Noah", "Liam", "Ava", "Ethan", "Chloe",
         "Daniel", "Hannah", "Thomas", "Laura", "Nikos", "Anna", "Jakub", "Elif", "Mehmet"],
        ["Smith", "Brown", "Taylor", "Wilson", "Muller", "Schmidt", "Martin", "Bernard", "Rossi",
         "Kowalski", "Nowak", "Papadopoulos", "Yilmaz", "van Dijk", "Johnson", "Okafor", "Botha"],
    ),
    "arabic": (["Mohammed", "Fatima", "Omar", "Layla", "Yousef", "Noor", "Khalid", "Mariam"],
               ["Al Mansouri", "Al Hashimi", "Haddad", "Nasser", "Al Farsi", "Khalil"]),
    "spanish": (["Juan", "Maria", "Carlos", "Ana", "Luis", "Sofia", "Diego", "Valentina", "Mateo", "Camila",
                 "Joao", "Beatriz"],
                ["Garcia", "Rodriguez", "Martinez", "Lopez", "Gonzalez", "Perez", "Silva", "Santos",
                 "Oliveira", "Fernandez"]),
}

# country -> (calling code, {pool: weight}, language)
COUNTRIES = {
    "MY": ("60", {"chinese": 45, "malay": 40, "indian": 15}, "ms"),
    "SG": ("65", {"chinese": 75, "malay": 15, "indian": 10}, "en"),
    "TH": ("66", {"thai": 100}, "th"),
    "VN": ("84", {"vietnamese": 100}, "vi"),
    "ID": ("62", {"indonesian": 100}, "id"),
    "PH": ("63", {"spanish": 50, "western": 50}, "en"),
    "HK": ("852", {"chinese": 100}, "zh"),
    "TW": ("886", {"chinese": 100}, "zh"),
    "MO": ("853", {"chinese": 100}, "zh"),
    "AU": ("61", {"western": 85, "chinese": 15}, "en"),
    "JP": ("81", {"japanese": 100}, "ja"),
    "KR": ("82", {"korean": 100}, "ko"),
    "GB": ("44", {"western": 90, "indian": 10}, "en"),
    "DE": ("49", {"western": 100}, "de"),
    "FR": ("33", {"western": 100}, "fr"),
    "ES": ("34", {"spanish": 100}, "es"),
    "IT": ("39", {"western": 100}, "it"),
    "AE": ("971", {"arabic": 80, "indian": 20}, "ar"),
    "SA": ("966", {"arabic": 100}, "ar"),
    "ZA": ("27", {"western": 100}, "en"),
    "NG": ("234", {"western": 100}, "en"),
    "CY": ("357", {"western": 100}, "el"),
    "GR": ("30", {"western": 100}, "el"),
    "PL": ("48", {"western": 100}, "pl"),
    "BR": ("55", {"spanish": 100}, "pt"),
    "MX": ("52", {"spanish": 100}, "es"),
    "CO": ("57", {"spanish": 100}, "es"),
    "CL": ("56", {"spanish": 100}, "es"),
    "AR": ("54", {"spanish": 100}, "es"),
    "TR": ("90", {"western": 100}, "tr"),
}

# ESMA / ASIC / JFSA retail leverage caps
LEVERAGE_CAP = {c: 30 for c in ("GB", "DE", "FR", "ES", "IT", "CY", "GR", "PL", "AU")} | {"JP": 25}

EMAIL_DOMAINS = ["example.com", "example.net", "example.org", "mail.example.com"]


def fake_identities(rng: np.random.Generator, countries: np.ndarray) -> dict[str, np.ndarray]:
    """为给定国家生成合成客户身份。
    Generate synthetic client identities for given countries."""
    n = len(countries)
    first = np.empty(n, dtype=object)
    last = np.empty(n, dtype=object)
    pool_used = np.empty(n, dtype=object)
    phone = np.empty(n, dtype=object)
    email = np.empty(n, dtype=object)
    lang = np.empty(n, dtype=object)
    for i, c in enumerate(countries):
        code, pools, language = COUNTRIES[c]
        names = list(pools)
        weights = np.array([pools[p] for p in names], dtype=float)
        pool = names[rng.choice(len(names), p=weights / weights.sum())]
        firsts, lasts = POOLS[pool]
        first[i] = firsts[rng.integers(len(firsts))]
        last[i] = lasts[rng.integers(len(lasts))]
        pool_used[i] = pool
        lang[i] = "zh" if pool == "chinese" else language
        phone[i] = f"+{code} {rng.integers(10, 99)}-{rng.integers(100, 999)} {rng.integers(1000, 9999)}"
        handle = f"{first[i]}.{last[i]}".lower().replace(" ", "")
        email[i] = f"{handle}{rng.integers(1, 999)}@{EMAIL_DOMAINS[rng.integers(len(EMAIL_DOMAINS))]}"
    return {"FirstName": first, "LastName": last, "Phone": phone, "Email": email, "Language": lang, "pool": pool_used}
