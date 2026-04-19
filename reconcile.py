"""
Service de réconciliation OpenRefine pour l'API ISNI (accès libre).

API SRU ISNI : http://isni.oclc.org/sru/DB=1.2/
Inspiré de cmharlow/isni-reconcile et P0luch/opentheso-openrefine
"""

import atexit
import io
import json
import os
import pickle
import re
import threading
import unicodedata
import zipfile
from operator import itemgetter

import requests
from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
from lxml import etree

import config

app = Flask(__name__, template_folder=config.TEMPLATE_DIR)
CORS(app)

# ---------------------------------------------------------------------------
# Codes relationnels MARC21 → libellés (source : id.loc.gov/vocabulary/relators)
# ---------------------------------------------------------------------------

MARC_RELATORS = {
    "abr": "abridger", "act": "actor", "adp": "adapter", "rcp": "addressee",
    "anl": "analyst", "anm": "animator", "anc": "announcer", "ann": "annotator",
    "apl": "appellant", "ape": "appellee", "app": "applicant", "arc": "architect",
    "arr": "arranger", "acp": "art copyist", "adi": "art director", "art": "artist",
    "ard": "artistic director", "asg": "assignee", "asn": "associated name",
    "att": "attributed name", "auc": "auctioneer", "aue": "audio engineer",
    "aup": "audio producer", "aut": "author", "aqt": "author in quotations",
    "aft": "author of afterword", "aui": "author of introduction",
    "aud": "author of dialog", "ato": "autographer", "bnd": "binder",
    "bdd": "binding designer", "bka": "book artist", "bkd": "book designer",
    "bkp": "book producer", "bsl": "bookseller", "brd": "broadcaster",
    "cll": "calligrapher", "cop": "camera operator", "ctg": "cartographer",
    "cas": "case reporter", "cad": "caster", "cns": "censor",
    "chr": "choreographer", "cng": "cinematographer", "cli": "client",
    "cor": "collection registrar", "col": "collector", "clt": "collotyper",
    "cmm": "commentator", "cwt": "commentator for written text", "com": "compiler",
    "cpl": "complainant", "cpt": "complainant-appellant", "cmp": "composer",
    "cmt": "compositor", "ccp": "conceptor", "cnd": "conductor",
    "con": "conservator", "csl": "consultant", "csp": "consultant to project",
    "cos": "contestant", "cot": "contestant-appellant", "coe": "contestant-appellee",
    "cts": "contestee", "ctt": "contestee-appellant", "ctr": "contractor",
    "ctb": "contributor", "cpc": "copyright claimant", "cph": "copyright holder",
    "crr": "corrector", "crp": "correspondent", "cst": "costume designer",
    "cou": "court governed", "cov": "cover designer", "cre": "creator",
    "cur": "curator", "dtc": "data contributor", "dnc": "dancer",
    "dfd": "defendant", "dft": "defendant-appellant", "dfe": "defendant-appellee",
    "dto": "dedicator", "dte": "dedicatee", "dln": "delineator",
    "dsr": "designer", "drt": "director", "dis": "dissertant",
    "dbp": "distribution place", "djo": "dj", "dgg": "degree granting institution",
    "dgs": "degree supervisor", "edt": "editor", "edc": "editor of compilation",
    "edm": "editor of moving image work", "edd": "editorial director",
    "elg": "electrician", "elt": "electrotyper", "enj": "enacting jurisdiction",
    "eng": "engineer", "egr": "engraver", "etr": "etcher", "evp": "event planner",
    "exp": "expert", "fac": "faculty", "fld": "field director", "fmd": "film director",
    "fds": "film distributor", "flm": "film editor", "fmp": "film producer",
    "fmk": "filmmaker", "fpy": "first party", "frg": "forger", "fmo": "former owner",
    "fon": "founder", "fnd": "funder", "gdv": "geodetic surveyor",
    "gis": "geographic information specialist", "hnr": "honoree", "hst": "host",
    "his": "host institution", "ilu": "illuminator", "ill": "illustrator",
    "ink": "inker", "ins": "inscriber", "itr": "instrumentalist", "ive": "interviewee",
    "ivr": "interviewer", "inv": "inventor", "isb": "issuing body",
    "jud": "judge", "jug": "jurisdiction governed", "lbr": "laboratory",
    "ldr": "laboratory director", "lsa": "landscape architect", "led": "lead",
    "len": "lender", "ltr": "letterpress", "lse": "licensee",
    "lgd": "lighting designer", "ltg": "lithographer", "lyr": "lyricist",
    "mka": "makeup artist", "mfp": "manufacture place", "mfr": "manufacturer",
    "mrb": "marble worker", "mrk": "markup editor", "med": "media",
    "mdc": "metadata contact", "mte": "metal engraver", "mtk": "minute taker",
    "mod": "moderator", "mon": "monitor", "mcp": "music copyist",
    "mup": "music programmer", "msd": "musical director", "mus": "musician",
    "nrt": "narrator", "nan": "narrator of audiofile", "onp": "online publisher",
    "osp": "onscreen presenter", "opn": "opening", "orm": "organizer",
    "org": "originator", "oth": "other", "pan": "panelist", "ppm": "papermaker",
    "pta": "principal target audience", "pth": "patent holder", "pat": "patron",
    "pnc": "penciler", "prf": "performer", "pma": "permitting agency",
    "pht": "photographer", "pad": "place of address", "ptf": "plaintiff",
    "ptt": "plaintiff-appellant", "pte": "plaintiff-appellee", "plt": "platemaker",
    "pra": "praeses", "prt": "printer", "pop": "popular creator",
    "prm": "printmaker", "prc": "process contact", "pro": "producer",
    "prn": "production company", "prs": "production designer",
    "pmn": "production manager", "pdr": "project director", "prg": "programmer",
    "pbd": "publisher director", "pbl": "publisher", "pup": "puppeteer",
    "rdd": "radio director", "rpc": "radio producer", "rap": "rap artist",
    "rce": "recording engineer", "rcd": "recordist", "red": "redactor",
    "ren": "renderer", "rpt": "reporter", "rps": "repository",
    "rth": "research team head", "rtm": "research team member", "res": "researcher",
    "rsp": "respondent", "rst": "respondent-appellant", "rse": "respondent-appellee",
    "rpy": "responsible party", "rsg": "restager", "rsr": "restorationist",
    "rev": "reviewer", "rbr": "rubricator", "sce": "scenarist",
    "sad": "scientific advisor", "aus": "screenwriter", "scr": "scribe",
    "scl": "sculptor", "spy": "second party", "sec": "secretary", "sll": "seller",
    "std": "set designer", "sgn": "signer", "sng": "singer",
    "swd": "software developer", "sds": "sound designer", "sde": "sound engineer",
    "spk": "speaker", "sfx": "special effects provider", "spn": "sponsor",
    "stl": "storyteller", "sgd": "stage director", "stm": "stage manager",
    "stn": "standards body", "str": "stereotyper", "sht": "supporting host",
    "srv": "surveyor", "tad": "technical advisor", "tch": "teacher",
    "tcd": "technical director", "tld": "television director",
    "tlg": "television graphics", "tlh": "television host",
    "tlp": "television producer", "tau": "television writer", "ths": "thesis advisor",
    "trc": "transcriber", "trl": "translator", "tyd": "type designer",
    "tyg": "typographer", "uvp": "university place", "vdg": "videographer",
    "vfx": "visual effects provider", "vac": "voice actor", "voc": "vocalist",
    "wit": "witness", "wde": "wood engraver", "wdc": "woodcutter",
    "wam": "writer of accompanying material", "wac": "writer of added commentary",
    "wal": "writer of added lyrics", "wat": "writer of added text",
    "waw": "writer of afterword", "wfs": "writer of film script",
    "wfw": "writer of foreword", "wft": "writer of frontispiece",
    "win": "writer of introduction", "wpr": "writer of preface",
    "wst": "writer of screenplay", "wts": "writer of supplementary textual content",
    "ant": "bibliographic antecedent",
}


def resolve_relator(code):
    """Résout un code MARC21 en libellé, retourne le code brut si inconnu."""
    c = code.strip().strip('"').lower()
    return MARC_RELATORS.get(c, c)

# ---------------------------------------------------------------------------
# API ISNI
# ---------------------------------------------------------------------------

API_BASE_URL = "http://isni.oclc.org/sru/"

default_query = {
    "id": "/isni/name",
    "name": "Nom exact (pica.na)",
    "index": "pica.na",
}

refine_to_isni = [
    default_query,
    {
        "id": "/isni/name_keyword",
        "name": "Mots-clés (pica.nw)",
        "index": "pica.nw",
    },
    {
        "id": "/isni/isni_number",
        "name": "Numéro ISNI",
        "index": "pica.isn",
    },
]

query_types = [{"id": i["id"], "name": i["name"]} for i in refine_to_isni]

# ---------------------------------------------------------------------------
# Propriétés d'extension
# ---------------------------------------------------------------------------

EXTENSION_PROPERTIES = [
    {"id": "type_entite",  "name": "Type (personne / organisation)"},
    {"id": "isni",         "name": "Identifiant ISNI"},
    {"id": "uri",          "name": "URI ISNI"},
    {"id": "nom",          "name": "Nom"},
    {"id": "prenom",       "name": "Prénom"},
    {"id": "dates",        "name": "Dates"},
    {"id": "role",         "name": "Rôle de création"},
    {"id": "variantes",    "name": "Variantes du nom"},
    {"id": "equivalences", "name": "Equivalences"},
    {"id": "sameas",       "name": "sameAs (Wikidata…)"},
]
PROPERTY_IDS = {p["id"] for p in EXTENSION_PROPERTIES}

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "maxResults": config.DEFAULT_MAX_RESULTS,
    "threshold":  config.DEFAULT_THRESHOLD,
}

_settings: dict = {}


def load_settings():
    if os.path.exists(config.SETTINGS_FILE):
        try:
            with open(config.SETTINGS_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


_settings_lock = threading.Lock()

def get_settings():
    with _settings_lock:
        if not _settings:
            _settings.update(load_settings())
    return _settings


def save_settings(settings):
    try:
        with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        with _settings_lock:
            _settings.clear()
    except Exception as e:
        print(f"[settings] Erreur : {e}")

# ---------------------------------------------------------------------------
# Cache persistant
# ---------------------------------------------------------------------------

_CACHE_MAX = 200_000

def _load_pkl(path):
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    return {}


def _save_pkl(path, data, label):
    try:
        with open(path, "wb") as f:
            pickle.dump(data, f)
        print(f"[{label}] {len(data)} entrées sauvegardées.")
    except Exception as e:
        print(f"[{label}] Erreur sauvegarde : {e}")


# _search_cache : (normalize(query), query_type) → liste de résultats
_search_cache: dict = _load_pkl(config.CACHE_FILE)
# _record_cache : isni_uri → dict parsé (pour preview et extension)
_record_cache: dict = _load_pkl(config.RECORD_FILE)
_cache_lock = threading.Lock()


def _save_all():
    _save_pkl(config.CACHE_FILE,  _search_cache, "cache_recherche")
    _save_pkl(config.RECORD_FILE, _record_cache,  "cache_notices")


atexit.register(_save_all)

# ---------------------------------------------------------------------------
# Normalisation et scoring
# ---------------------------------------------------------------------------

def normalize(text):
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _make_bigrams(s):
    s = normalize(s)
    return set(s[i:i+2] for i in range(len(s) - 1)) if len(s) >= 2 else set()


def _dice(a, b):
    ba, bb = _make_bigrams(a), _make_bigrams(b)
    if not ba or not bb:
        return 0.0
    return 100.0 * 2 * len(ba & bb) / (len(ba) + len(bb))


def score_candidate(query, names):
    """Calcule le score et le statut match pour une liste de noms.

    1. Exact sur le nom principal                → 100, match=True
    2. Exact sur une variante                    → 90,  match=True
    3. Tous les mots de query dans nom principal → 75,  match=False
    4. Tous les mots de query dans une variante  → 65,  match=False
    5. Meilleur score Dice sur tous les noms     → Dice, match=False
    """
    if not names:
        return 0, False
    q = normalize(query)
    main, variants = names[0], names[1:]

    if q == normalize(main):
        return 100, True
    for name in variants:
        if q == normalize(name):
            return 90, True

    q_words = set(q.split())
    if q_words and q_words.issubset(set(normalize(main).split())):
        return 75, False
    for name in variants:
        if q_words and q_words.issubset(set(normalize(name).split())):
            return 65, False

    best = max((_dice(query, n) for n in names), default=0.0)
    return int(best), False

# ---------------------------------------------------------------------------
# Parsing XML ISNI
# ---------------------------------------------------------------------------

SRW_NS = "{http://www.loc.gov/zing/srw/}"


def format_isni(raw):
    """0000000115677274 → 0000 0001 1567 7274"""
    raw = re.sub(r"\s", "", raw)
    return " ".join(raw[i:i+4] for i in range(0, 16, 4)) if len(raw) == 16 else raw


def parse_record(record_el):
    """Extrait les champs utiles d'un élément <record> SRW."""
    data = {}

    # URI et numéro ISNI
    uri_els = record_el.xpath(".//isniURI")
    if not uri_els:
        return None
    data["uri"] = uri_els[0].text or ""

    raw_els = record_el.xpath(".//isniUnformatted")
    data["isni"] = format_isni(raw_els[0].text) if raw_els else ""

    # Noms (personnes)
    personal_names = record_el.xpath(".//personalName")
    names = []
    for pn in personal_names:
        surname  = pn.findtext("surname") or ""
        forename = pn.findtext("forename") or ""
        dates    = pn.findtext("marcDate") or pn.findtext("dates") or ""
        full = f"{surname}, {forename}".strip(", ")
        if full:
            names.append({"surname": surname, "forename": forename,
                          "dates": dates, "full": full})

    # Noms (organisations)
    org_names = record_el.xpath(".//organisationName")
    for on in org_names:
        main = on.findtext("mainName") or ""
        sub  = on.findtext("subdivisionName") or ""
        full = f"{main} {sub}".strip()
        if full:
            names.append({"surname": main, "forename": sub,
                          "dates": "", "full": full})

    if not names:
        return None

    data["names"]    = names
    if record_el.xpath(".//identity/personOrFiction"):
        data["type_entite"] = "personne"
    elif record_el.xpath(".//identity/organisation"):
        data["type_entite"] = "organisation"
    else:
        data["type_entite"] = ""
    data["nom"]      = names[0]["surname"]
    data["prenom"]   = names[0]["forename"]
    data["dates"]    = names[0]["dates"]
    seen = {names[0]["full"]}
    variantes = []
    for n in names[1:]:
        if n["full"] not in seen:
            seen.add(n["full"])
            variantes.append(n["full"])
    data["variantes"] = variantes

    # Rôles de création (dédupliqués)
    roles = []
    for r in record_el.xpath(".//creationRole"):
        val = resolve_relator((r.text or "").strip())
        if val and val not in roles:
            roles.append(val)
    data["role"] = roles

    # Titres d'œuvres (tous récupérés, dédupliqués)
    titles = []
    seen_titles = set()
    for tw in record_el.xpath(".//titleOfWork"):
        t = (tw.findtext("title") or "").lstrip("@").strip()
        if t and t not in seen_titles:
            seen_titles.add(t)
            titles.append(t)
    data["titres"] = titles

    return data

# ---------------------------------------------------------------------------
# Requête ISNI
# ---------------------------------------------------------------------------

def build_cql(index, raw_query):
    if index in ("pica.nw", "pica.isn"):
        term = "+".join(raw_query.strip().split())
    else:
        term = raw_query.strip()
    return f'{index} = "{term}"'


def fetch_records(cql, maximum=5, schema="isni-b"):
    """Appelle l'API SRU ISNI et retourne la liste des éléments <record>."""
    params = {
        "operation":      "searchRetrieve",
        "recordSchema":   schema,
        "maximumRecords": str(maximum),
        "query":          cql,
    }
    resp = requests.get(API_BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    app.logger.debug("URL ISNI : %s", resp.url)
    root = etree.fromstring(resp.content)
    return list(root.iter(f"{SRW_NS}record"))


def fetch_jsonld_data(isni_number):
    """Récupère depuis isni-jsonld : dates, équivalences et sameAs."""
    result = {"dates": "", "equivalences": [], "sameas": []}
    try:
        records = fetch_records(f'pica.isn = "{isni_number}"', maximum=1, schema="isni-jsonld")
        for rec in records:
            record_data = rec.find(f"{SRW_NS}recordData")
            if record_data is None or not record_data.text:
                continue
            jsonld = json.loads(record_data.text)
            for node in jsonld.get("@graph", []):
                if "isni.org/isni/" not in node.get("@id", "") or "about" in node.get("@id", ""):
                    continue
                # Dates
                birth = node.get("schema:birthDate", "")
                death = node.get("schema:deathDate", "")
                if birth or death:
                    result["dates"] = f"{birth}-{death}" if death else birth
                # Equivalences (autorités bibliographiques)
                result["equivalences"] = [
                    e["@id"] for e in node.get("madsrdf:isIdentifiedByAuthority", []) if "@id" in e
                ]
                # sameAs (Wikidata, etc.)
                result["sameas"] = [
                    e["@id"] for e in node.get("owl:sameAs", []) if "@id" in e
                ]
                break
    except Exception as e:
        app.logger.warning("fetch_jsonld_data error : %s", e)
    return result


def fetch_by_uri(isni_uri):
    """Récupère (et met en cache) la notice complète à partir de l'URI ou du numéro ISNI."""
    number = re.sub(r"\s", "", isni_uri.rstrip("/").split("/")[-1])
    isni_uri = f"https://isni.org/isni/{number}"

    # Notice déjà en cache (ex: mise en cache pendant la recherche) :
    # on complète avec les données jsonld si elles sont absentes
    if isni_uri in _record_cache:
        data = _record_cache[isni_uri]
        if "equivalences" not in data:
            jsonld = fetch_jsonld_data(number)
            data["equivalences"] = jsonld["equivalences"]
            data["sameas"]       = jsonld["sameas"]
            if jsonld["dates"]:
                data["dates"] = jsonld["dates"]
        return data
    try:
        records = fetch_records(f'pica.isn = "{number}"', maximum=1)
        for rec in records:
            data = parse_record(rec)
            if data and data.get("uri") == isni_uri:
                jsonld = fetch_jsonld_data(number)
                data["equivalences"] = jsonld["equivalences"]
                data["sameas"]       = jsonld["sameas"]
                # Priorité aux dates JSON-LD (plus fiables), fallback sur marcDate
                if jsonld["dates"]:
                    data["dates"] = jsonld["dates"]
                with _cache_lock:
                    _record_cache[isni_uri] = data
                return data
    except Exception as e:
        app.logger.warning("fetch_by_uri error : %s", e)
    return None

# ---------------------------------------------------------------------------
# Recherche principale
# ---------------------------------------------------------------------------

def search(raw_query, query_type="/isni/name"):
    cache_key = (normalize(raw_query), query_type)
    if cache_key in _search_cache:
        return _search_cache[cache_key]

    settings    = get_settings()
    max_results = settings["maxResults"]
    threshold   = settings["threshold"]

    meta  = next((i for i in refine_to_isni if i["id"] == query_type), default_query)
    index = meta["index"]
    cql   = build_cql(index, raw_query)

    try:
        record_els = fetch_records(cql, maximum=max(5, max_results))
    except Exception as e:
        app.logger.warning("Erreur API ISNI : %s", e)
        return []

    out      = []
    seen_ids = set()

    for rec in record_els:
        data = parse_record(rec)
        if not data:
            continue
        uri = data["uri"]
        if uri in seen_ids:
            continue
        seen_ids.add(uri)

        if index == "pica.isn":
            score, is_match = 100, True
        else:
            all_names = [n["full"] for n in data["names"]]
            score, is_match = score_candidate(raw_query, all_names)
            if score < threshold:
                continue

        # Mettre en cache la notice pour preview / extension
        with _cache_lock:
            _record_cache[uri] = data

        out.append({
            "id":    uri,
            "name":  data["names"][0]["full"],
            "score": score,
            "match": is_match,
            "type":  [{"id": meta["id"], "name": meta["name"]}],
        })

    result = sorted(out, key=itemgetter("score"), reverse=True)[:max_results]

    if result and len(_search_cache) < _CACHE_MAX:
        with _cache_lock:
            _search_cache[cache_key] = result

    return result

# ---------------------------------------------------------------------------
# Manifeste du service
# ---------------------------------------------------------------------------

def service_manifest(base_url):
    return {
        "name": "ISNI Reconciliation Service",
        "identifierSpace": "https://isni.org/isni/",
        "schemaSpace":     "https://isni.org/isni/",
        "defaultTypes": query_types,
        "preview": {
            "url":    f"{base_url}/reconcile/preview?id={{{{id}}}}",
            "width":  400,
            "height": 200,
        },
        "view": {"url": "{{id}}"},
        "extend": {
            "propose_properties": {
                "service_url":  base_url,
                "service_path": "/reconcile/properties",
            },
            "property_settings": [],
        },
    }

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    settings = get_settings()
    return render_template("index.html", settings=settings, port=config.PORT)


@app.route("/settings", methods=["POST"])
def update_settings():
    settings = load_settings()
    try:
        settings["maxResults"] = max(1, min(10, int(request.form.get("maxResults", config.DEFAULT_MAX_RESULTS))))
    except ValueError:
        settings["maxResults"] = config.DEFAULT_MAX_RESULTS
    try:
        settings["threshold"] = max(0.0, min(100.0, float(request.form.get("threshold", config.DEFAULT_THRESHOLD))))
    except ValueError:
        settings["threshold"] = config.DEFAULT_THRESHOLD
    save_settings(settings)  # efface _settings via save_settings
    return jsonify({"ok": True, "message": "Paramètres sauvegardés."})


@app.route("/reconcile", methods=["GET", "POST"])
def reconcile():
    base_url = request.host_url.rstrip("/")

    # Extension de données
    extend_raw = request.values.get("extend")
    if extend_raw:
        result = extend_handler(extend_raw)
        _save_all()
        return result

    # Requêtes par lot
    queries_raw = request.values.get("queries")
    if queries_raw:
        try:
            query_batch = json.loads(queries_raw)
        except json.JSONDecodeError:
            return jsonify({"error": "JSON invalide"}), 400
        results = {}
        for key, q in query_batch.items():
            qtype = q.get("type", default_query["id"])
            if isinstance(qtype, list) and qtype:
                qtype = qtype[0].get("id") if isinstance(qtype[0], dict) else qtype[0]
            results[key] = {"result": search(q["query"], query_type=qtype)}
        _save_all()
        return jsonify(results)

    # Requête unique (mode déprécié)
    query = request.values.get("query")
    if query:
        if query.startswith("{"):
            try:
                query = json.loads(query).get("query", query)
            except json.JSONDecodeError:
                return jsonify({"error": "JSON invalide"}), 400
        qtype = request.values.get("type", default_query["id"])
        return jsonify({"result": search(query, query_type=qtype)})

    # Métadonnées du service
    return jsonify(service_manifest(base_url))


@app.route("/reconcile/preview", methods=["GET"])
def preview():
    isni_uri = request.args.get("id", "").strip()
    if not isni_uri:
        return "Paramètre id manquant", 400

    data = fetch_by_uri(isni_uri)
    if not data:
        return "<p style='font-family:sans-serif;padding:16px;color:#c00'>Notice introuvable.</p>", 404

    full = request.args.get("full", "0") == "1"
    return render_template("preview.html", data=data, full=full)


@app.route("/reconcile/properties", methods=["GET", "POST"])
def properties():
    return jsonify({"limit": 10, "type": "/isni/name", "properties": EXTENSION_PROPERTIES})


@app.route("/reconcile/extend", methods=["GET", "POST"])
def extend():
    extend_raw = request.values.get("extend")
    if not extend_raw:
        return jsonify({"error": "Paramètre extend manquant"}), 400
    result = extend_handler(extend_raw)
    _save_all()
    return result


def extend_handler(extend_raw):
    try:
        req = json.loads(extend_raw)
    except json.JSONDecodeError:
        return jsonify({"error": "JSON invalide"}), 400

    ids   = req.get("ids", [])
    props = [p["id"] for p in req.get("properties", []) if p["id"] in PROPERTY_IDS]
    rows  = {}

    for isni_uri in ids:
        data = fetch_by_uri(isni_uri)
        if not data:
            rows[isni_uri] = {p: [] for p in props}
            continue
        row = {}
        for prop in props:
            val = data.get(prop, [])
            if isinstance(val, list):
                row[prop] = [{"str": v} for v in val if v]
            else:
                row[prop] = [{"str": val}] if val else []
        rows[isni_uri] = row

    prop_map = {p["id"]: p for p in EXTENSION_PROPERTIES}
    meta = [prop_map[pid] for pid in props if pid in prop_map]
    return jsonify({"meta": meta, "rows": rows})


@app.route("/clear-cache", methods=["POST"])
def clear_cache():
    with _cache_lock:
        _search_cache.clear()
        _record_cache.clear()
    for path in (config.CACHE_FILE, config.RECORD_FILE):
        if os.path.exists(path):
            os.remove(path)
    return jsonify({"ok": True, "message": "Cache vidé."})


@app.route("/export-cache")
def export_cache():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("search_cache.pkl", pickle.dumps(_search_cache))
        zf.writestr("record_cache.pkl", pickle.dumps(_record_cache))
    buf.seek(0)
    return send_file(buf, mimetype="application/zip",
                     as_attachment=True, download_name="isni_cache.zip")


@app.route("/import-cache", methods=["POST"])
def import_cache():
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "message": "Aucun fichier reçu."}), 400
    try:
        with zipfile.ZipFile(f) as zf:
            search_data = pickle.loads(zf.read("search_cache.pkl"))
            record_data = pickle.loads(zf.read("record_cache.pkl"))
        if not isinstance(search_data, dict) or not isinstance(record_data, dict):
            return jsonify({"ok": False, "message": "Format invalide."}), 400
        with _cache_lock:
            _search_cache.update(search_data)
            _record_cache.update(record_data)
        _save_all()
        return jsonify({"ok": True, "message": (
            f"{len(search_data)} recherches et {len(record_data)} notices importées. "
            f"Cache total : {len(_search_cache)} / {len(_record_cache)}."
        )})
    except Exception as e:
        return jsonify({"ok": False, "message": f"Erreur : {e}"}), 400

# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import logging
    import webbrowser

    class _FilterWerkzeug(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            return "production" not in msg.lower() and "do not use" not in msg.lower()

    logging.getLogger("werkzeug").addFilter(_FilterWerkzeug())

    banner = r"""

    _________ _   ______                    
   /  _/ ___// | / /  _/                    
   / / \__ \/  |/ // /                      
 _/ / ___/ / /|  // /                       
/___//____/_/ |_/___/                _ __   
   / __ \___  _________  ____  _____(_) /__ 
  / /_/ / _ \/ ___/ __ \/ __ \/ ___/ / / _ \
 / _, _/  __/ /__/ /_/ / / / / /__/ / /  __/
/_/ |_|\___/\___/\____/_/ /_/\___/_/_/\___/ 
                                            
    """
    print(banner)
    print(f"Service ISNI démarré")
    print(f" * OpenRefine : http://127.0.0.1:{config.PORT}/reconcile")
    print(f" * Config     : http://127.0.0.1:{config.PORT}/")
    print()

    threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{config.PORT}/")).start()
    app.run(host="0.0.0.0", port=config.PORT, debug=False, threaded=True)
