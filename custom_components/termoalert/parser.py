"""Parse the CMTEB outage table (same data as the TermoAlert app). No HA imports, so it's testable standalone."""
import html
import re
import unicodedata

URL = "https://www.cmteb.ro/functionare_sistem_termoficare.php"

# street type prefixes as written by users and by CMTEB
_PREFIX = re.compile(
    r"^(?:(?:strada|str|bulevardul|bulevard|b-dul|bdul|bd|bld|blvd|soseaua|sos|calea|cal|aleea|ale|al|"
    r"intrarea|intr|int|splaiul|spl|piata|pta|pt|drumul|dr|fundatura|fnd|prelungirea|prel)\b\.?\s*)+")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def street_key(s):
    s = re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()).strip()
    return norm(_PREFIX.sub("", s))


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


_BL = re.compile(r"(?i)\b(bl|bloc|blocul|blocuri|imob|imobil|imobilul|nr|numarul)\b\.?")


def bloc_key(s):
    return norm(_BL.sub(" ", s or "")).replace(" ", "")


def _blocks(s):
    """'bl. 5A2, 5; imob.Nr.125, E1- E4' -> {'5a2', '5', '125', 'e1e4', 'e1', 'e4'}."""
    out = set()
    for part in re.split(r"[,;]", s):
        out.add(bloc_key(part))
        out.update(norm(_BL.sub(" ", part)).split())  # ponytail: "E1- E4" ranges match only their ends, not E2/E3
    out.discard("")
    return out


def parse(page):
    """List of outages: dicts with sector, punct_termic, adrese [(strada, blocuri)], agent, motiv, estimare."""
    start = page.find('id="ST"')
    if start < 0:
        raise ValueError("outage table not found, page layout changed?")
    page = page[start:page.find("stop: toate sectoarele", start)]
    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", page, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) != 5:
            continue  # header row
        sector, zone, agent, motiv, estimare = cells
        for seg in zone.split("Punct termic:")[1:]:
            m = re.search(r"<strong>(.*?)</strong>", seg, re.S)
            adrese = []
            for line in seg.split("&bull;")[1:]:
                strada, _, bl = _text(line).partition(" - ")
                adrese.append((strada.strip(), bl.strip()))
            out.append({
                "sector": _text(sector),
                "punct_termic": _text(m.group(1)) if m else "",
                "adrese": adrese,
                "agent": _text(agent),
                "motiv": _text(motiv),
                "estimare": _text(estimare),
            })
    return out


def affects(outage, strada, bloc=None):
    """True if the outage lists `strada` (fuzzy: no diacritics/prefix/case) and, if given, `bloc`.
    A street listed with no blocks counts as the whole street."""
    want = street_key(strada)
    if not want:
        return False
    for s, bl in outage["adrese"]:
        if not re.search(rf"\b{re.escape(want)}\b", street_key(s)):
            continue
        if not bloc or not bl or bloc_key(bloc) in _blocks(bl):
            return True
    return False


def find(outages, strada, bloc=None):
    return [o for o in outages if affects(o, strada, bloc)]


if __name__ == "__main__":
    o = {"adrese": [("Bld Lacul Tei", "bl.5A2, 5, 5A1, 4, 6B"), ("Str Gării de Nord", ""),
                    ("Bld Ferdinand I", "bl. E1- E4, G1- G3, imob.Nr.125"), ("Şos Pantelimon", "bl.59-60, 55")]}
    assert affects(o, "Bulevardul Lacul Tei", "5a2")
    assert affects(o, "lacul tei", "Bl. 5")
    assert not affects(o, "Lacul Tei", "5A")
    assert affects(o, "Strada Garii de Nord", "7")  # no blocks listed -> whole street
    assert affects(o, "B-dul Ferdinand I", "125") and affects(o, "Ferdinand", "E1")
    assert affects(o, "soseaua pantelimon", "59-60") and not affects(o, "Pantelimon", "60A")
    assert affects({"adrese": [("Drumul Taberei", "")]}, "Str. Drumul Taberei")  # stacked prefixes
    assert not affects(o, "Tei 2") and not affects(o, "")
    import sys
    if len(sys.argv) > 1:
        rows = parse(open(sys.argv[1], encoding="utf-8").read())
        assert rows and all(r["adrese"] and r["agent"] for r in rows), rows[:3]
        print(len(rows), "outages; e.g.", rows[0])
    print("ok")
