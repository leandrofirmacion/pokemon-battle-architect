"""Pokemon 2026 Macdro — streamlit run app.py"""

from __future__ import annotations

import ast
import itertools
import json
import math
import random
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

CSV_CANDIDATES = [
    Path(__file__).resolve().parent / "pokemon_meta_data.csv",
    Path.cwd() / "pokemon_meta_data.csv",
    Path.home() / "pokemon_meta_data.csv",
]


def resolve_csv_path() -> Path | None:
    for p in CSV_CANDIDATES:
        if p.is_file():
            return p
    return None


def parse_list_cell(val) -> list:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    if isinstance(val, list):
        return val
    s = str(val).strip()
    if not s:
        return []
    try:
        return ast.literal_eval(s)
    except (SyntaxError, ValueError):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return []


def format_types_for_display(val) -> str:
    """Human-readable types for tables (e.g. Grass/Poison)."""
    parts = parse_list_cell(val)
    if not parts:
        return "—"
    return "/".join(str(p).strip().title() for p in parts)


TYPE_CHART: dict[str, dict[str, float]] = {
    "normal": {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "steel": 2.0, "dragon": 0.5},
    "water": {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass": {
        "fire": 0.5,
        "water": 2.0,
        "grass": 0.5,
        "poison": 0.5,
        "ground": 2.0,
        "flying": 0.5,
        "bug": 0.5,
        "rock": 2.0,
        "dragon": 0.5,
        "steel": 0.5,
    },
    "ice": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5},
    "fighting": {
        "normal": 2.0,
        "ice": 2.0,
        "poison": 0.5,
        "flying": 0.5,
        "psychic": 0.5,
        "bug": 0.5,
        "rock": 2.0,
        "ghost": 0.0,
        "dark": 2.0,
        "steel": 2.0,
        "fairy": 0.5,
    },
    "poison": {"grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0.0, "fairy": 2.0},
    "ground": {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, "bug": 0.5, "rock": 2.0, "steel": 2.0},
    "flying": {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5},
    "psychic": {"fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5},
    "bug": {
        "fire": 0.5,
        "grass": 2.0,
        "fighting": 0.5,
        "poison": 0.5,
        "flying": 0.5,
        "psychic": 2.0,
        "ghost": 0.5,
        "dark": 2.0,
        "steel": 0.5,
        "fairy": 0.5,
    },
    "rock": {"fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0, "steel": 0.5},
    "ghost": {"normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5},
    "dragon": {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "dark": {"fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5},
    "steel": {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, "steel": 0.5, "fairy": 2.0},
    "fairy": {"fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0, "dark": 2.0, "steel": 0.5},
}


def type_multiplier(attack_type: str, defend_types: list[str]) -> float:
    atk = attack_type.lower().strip()
    mult = 1.0
    for d in defend_types:
        mult *= TYPE_CHART.get(atk, {}).get(d.lower().strip(), 1.0)
    return mult


# Canonical order for type filter dropdown (matches main-series conventions)
TYPE_FILTER_ORDER = [
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
]

TYPE_COLORS = {
    "normal": "#A8A878",
    "fire": "#F08030",
    "water": "#6890F0",
    "electric": "#F8D030",
    "grass": "#78C850",
    "ice": "#98D8D8",
    "fighting": "#C03028",
    "poison": "#A040A0",
    "ground": "#E0C068",
    "flying": "#A890F0",
    "psychic": "#F85888",
    "bug": "#A8B820",
    "rock": "#B8A038",
    "ghost": "#705898",
    "dragon": "#7038F8",
    "dark": "#705848",
    "steel": "#B8B8D0",
    "fairy": "#EE99AC",
}


def type_badge_html(t: str) -> str:
    c = TYPE_COLORS.get(t.lower(), "#888888")
    return (
        f'<span style="background:{c};color:#fff;padding:4px 10px;border-radius:6px;'
        f'font-weight:600;margin:2px;display:inline-block;">{t.title()}</span>'
    )


POKEAPI_MOVE = "https://pokeapi.co/api/v2/move"


def _move_name_to_slug(move_name: str) -> str:
    slug = move_name.lower().replace(" ", "-").replace("'", "").replace(".", "").replace("é", "e")
    slug = "".join(ch for ch in slug if ch.isalnum() or ch == "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


@st.cache_data(ttl=86400, show_spinner=False)
def move_pokeapi_details(move_name: str) -> dict | None:
    slug = _move_name_to_slug(move_name)
    if not slug:
        return None
    try:
        r = requests.get(f"{POKEAPI_MOVE}/{slug}", timeout=8)
        if r.status_code != 200:
            return None
        d = r.json()
        dc = d.get("damage_class") or {}
        return {
            "type": (d.get("type") or {}).get("name"),
            "power": d.get("power"),
            "damage_class": dc.get("name") if isinstance(dc, dict) else None,
            "name": d.get("name"),
        }
    except requests.RequestException:
        return None


def move_attack_type(move_name: str) -> str | None:
    det = move_pokeapi_details(move_name)
    return det.get("type") if det else None


def _status_move_priority(display_name: str) -> float:
    """Rough VGC-style priority for status / setup moves without relying on raw power."""
    n = display_name.lower()
    tiers = (
        ("protect", 92.0),
        ("fake out", 90.0),
        ("spore", 88.0),
        ("sleep powder", 82.0),
        ("tailwind", 86.0),
        ("trick room", 84.0),
        ("thunder wave", 80.0),
        ("will-o-wisp", 78.0),
        ("helping hand", 76.0),
        ("stealth rock", 74.0),
        ("light screen", 70.0),
        ("reflect", 70.0),
        ("substitute", 66.0),
        ("roost", 72.0),
        ("recover", 68.0),
        ("quiver dance", 79.0),
        ("dragon dance", 79.0),
        ("swords dance", 77.0),
        ("calm mind", 76.0),
        ("nasty plot", 75.0),
        ("encore", 73.0),
        ("taunt", 71.0),
    )
    for needle, pts in tiers:
        if needle in n:
            return pts
    return 30.0


def recommended_four_moves(row: pd.Series) -> list[str]:
    """
    Pick four moves from learnset using PokeAPI power/type/category + STAB + Atk/Sp.Atk lean.
    Not official Smogon sets—fast heuristic for the dashboard.
    """
    moves = parse_list_cell(row.get("all_moves"))
    if not moves:
        return []

    # Long learnsets: score head+tail so we still consider late TMs / tutors without 150+ API calls.
    if len(moves) > 55:
        moves = list(dict.fromkeys(moves[:38] + moves[-17:]))

    types = [t.lower() for t in parse_list_cell(row.get("types"))]
    atk, spa = int(row["attack"]), int(row["sp_attack"])
    phys_bias = 1.12 if atk >= spa else 1.0
    spec_bias = 1.12 if spa > atk else 1.0

    scored: list[tuple[float, str]] = []
    for m in moves:
        det = move_pokeapi_details(str(m))
        if not det:
            continue
        mt = (det.get("type") or "").lower()
        power = det.get("power")
        dc = (det.get("damage_class") or "status").lower()
        stab = 1.5 if mt in types else 1.0

        if power is not None and int(power) > 0:
            sc = float(power) * stab
            if dc == "physical":
                sc *= phys_bias
            elif dc == "special":
                sc *= spec_bias
        else:
            sc = _status_move_priority(str(m)) * (1.08 if stab else 1.0)

        scored.append((sc, str(m)))

    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[str] = []
    seen: set[str] = set()
    for _, name in scored:
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
        if len(out) == 4:
            break

    if len(out) < 4:
        for m in moves:
            ms = str(m)
            if ms not in seen:
                seen.add(ms)
                out.append(ms)
            if len(out) == 4:
                break

    return out[:4]


LEDGER_HIDDEN_COLS = frozenset({"all_moves", "national_dex_hint", "pokemon_id"})


def ledger_column_order(columns: list[str]) -> list[str]:
    """
    Leading columns: PokéAPI id, name, art (image_url), types, Moveset; then the rest in source order.
    """
    cols_list = list(columns)
    colset = set(cols_list)
    preferred = ("pokeapi_id", "name", "image_url", "types", "Moveset")
    ordered: list[str] = []
    for p in preferred:
        if p in colset:
            ordered.append(p)
    for c in cols_list:
        if c not in ordered:
            ordered.append(c)
    return ordered


@st.cache_data(ttl=86400, show_spinner=False)
def ledger_moveset_display(
    name: str,
    moves_key: str,
    types_key: str,
    attack: int,
    sp_attack: int,
) -> str:
    """Cached four-move summary string for the DEX ledger (same heuristic as Team Builder)."""
    try:
        moves = json.loads(moves_key)
    except (json.JSONDecodeError, TypeError):
        moves = []
    try:
        types = json.loads(types_key)
    except (json.JSONDecodeError, TypeError):
        types = []
    row = pd.Series(
        {
            "name": name,
            "all_moves": moves,
            "types": types,
            "attack": int(attack),
            "sp_attack": int(sp_attack),
        }
    )
    m = recommended_four_moves(row)
    return " · ".join(m) if m else "—"


def ledger_dataframe_selection_row_index(ev) -> int | None:
    """First selected row index from st.dataframe(..., on_select='rerun'), or None."""
    if ev is None:
        return None
    sel = ev["selection"] if isinstance(ev, dict) else getattr(ev, "selection", None)
    if sel is None:
        return None
    rows = sel["rows"] if isinstance(sel, dict) else getattr(sel, "rows", None)
    if not rows:
        return None
    try:
        return int(rows[0])
    except (TypeError, ValueError, IndexError):
        return None


def wilson_score_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Approximate binomial 95% CI (Wilson); returns (low, high) in [0, 1]."""
    if n <= 0:
        return (0.0, 0.0)
    phat = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (phat + z2 / (2 * n)) / denom
    spread = z * math.sqrt((phat * (1 - phat) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, center - spread), min(1.0, center + spread))


def confidence_badge(sample_size: int) -> str:
    """Rough confidence label for Monte Carlo sample sizes."""
    n = int(sample_size)
    if n >= 200:
        return "High"
    if n >= 80:
        return "Medium"
    return "Quick"


def render_rules_summary(
    *,
    format_label: str,
    opponent_label: str,
    move_pool: str,
    scoring_label: str,
    seed: int,
) -> None:
    """Compact run-settings summary so users know exactly what is being simulated."""
    st.caption(
        f"Rules: **{format_label}** · Opponents **{opponent_label}** · Moves **{move_pool}** · "
        f"Scoring **{scoring_label}** · Seed **{int(seed)}**"
    )


def moves_for_battle_sim(
    row: pd.Series,
    move_pool: str,
    core4_cache: dict[str, list[str]],
) -> list[str]:
    """Moves considered for coverage scoring: full learnset (trimmed) or heuristic four."""
    if move_pool == "Suggested 4 (heuristic)":
        nm = str(row["name"])
        if nm not in core4_cache:
            core4_cache[nm] = recommended_four_moves(row)
        return core4_cache[nm]
    moves = parse_list_cell(row.get("all_moves"))
    if len(moves) > 55:
        moves = list(dict.fromkeys(moves[:38] + moves[-17:]))
    return [str(m) for m in moves]


def best_type_effectiveness_vs(move_names: list[str], opponent_types: list[str]) -> float:
    """Highest type chart multiplier among resolved moves vs defender types (minimum 1.0)."""
    opp = [t.lower() for t in opponent_types if t]
    if not move_names or not opp:
        return 1.0
    best = 1.0
    for mv in move_names:
        mt = move_attack_type(str(mv))
        if not mt:
            continue
        m = type_multiplier(mt, opp)
        if m > best:
            best = m
    return best


# --- Battle sim: competitive assumptions (VGC-style Lv 50, perfect IV/EV, speed-boosting nature) ---

COMPETITIVE_BATTLE_LEVEL = 50
COMPETITIVE_IV = 31
# 252 offensive / 252 Speed / 4 HP; nature +Speed −Atk (Timid) or −Sp.Atk (Jolly)
SCORING_STANDARD = "standard_coverage"
SCORING_MAX_DAMAGE = "max_damage_bias"
SCORING_COMPETITIVE = "competitive_ev_iv"

BATTLE_SCORING_OPTIONS: tuple[str, ...] = ("Standard Coverage", "Max Damage", "Competitive EV/IV")
BATTLE_SCORING_INTERNAL: dict[str, str] = {
    "Standard Coverage": SCORING_STANDARD,
    "Max Damage": SCORING_MAX_DAMAGE,
    "Competitive EV/IV": SCORING_COMPETITIVE,
}
BATTLE_SCORING_DESCRIPTIONS: dict[str, str] = {
    "Standard Coverage": "Counts every super-effective hit as equal.",
    "Max Damage": "Rewards 4× weaknesses (double super-effective) more heavily.",
    "Competitive EV/IV": (
        "Lv 50, 31 IV, 252/252/4 + speed nature; damage stub with STAB and type chart, scaled by Speed."
    ),
}
BATTLE_SCORING_SUMMARY_LABEL: dict[str, str] = {
    SCORING_STANDARD: "standard coverage",
    SCORING_MAX_DAMAGE: "max damage",
    SCORING_COMPETITIVE: "competitive EV/IV",
}


def _nature_mults(plus: str, minus: str) -> dict[str, float]:
    keys = ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed")
    m = dict.fromkeys(keys, 1.0)
    if plus in m:
        m[plus] = 1.1
    if minus in m:
        m[minus] = 0.9
    return m


@st.cache_data(ttl=86400, show_spinner=False)
def competitive_final_stats_cached(
    name: str,
    b_hp: int,
    b_atk: int,
    b_def: int,
    b_spa: int,
    b_spd: int,
    b_spe: int,
) -> tuple[int, int, int, int, int, int]:
    """
    Final stats at COMPETITIVE_BATTLE_LEVEL with 31 IVs, 252/252/4 EVs,
    and Timid (+Spe −Atk) if special-leaning else Jolly (+Spe −SpA).
    """
    L = COMPETITIVE_BATTLE_LEVEL
    iv = COMPETITIVE_IV
    if b_atk >= b_spa:
        ev = {"hp": 4, "attack": 252, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 252}
        nm = _nature_mults("speed", "sp_attack")
    else:
        ev = {"hp": 4, "attack": 0, "defense": 0, "sp_attack": 252, "sp_defense": 0, "speed": 252}
        nm = _nature_mults("speed", "attack")

    def ev_s(stat: str) -> int:
        return int(ev.get(stat, 0))

    hp = math.floor((2 * b_hp + iv + math.floor(ev_s("hp") / 4)) * L / 100) + L + 10

    def other(base: int, stat: str) -> int:
        inner = math.floor((2 * base + iv + math.floor(ev_s(stat) / 4)) * L / 100) + 5
        return math.floor(inner * nm[stat])

    atk = other(b_atk, "attack")
    defense = other(b_def, "defense")
    spa = other(b_spa, "sp_attack")
    spd = other(b_spd, "sp_defense")
    spe = other(b_spe, "speed")
    return (hp, atk, defense, spa, spd, spe)


def competitive_final_stats_from_row(row: pd.Series) -> dict[str, int]:
    t = competitive_final_stats_cached(
        str(row["name"]),
        int(row["hp"]),
        int(row["attack"]),
        int(row["defense"]),
        int(row["sp_attack"]),
        int(row["sp_defense"]),
        int(row["speed"]),
    )
    return {
        "hp": t[0],
        "attack": t[1],
        "defense": t[2],
        "sp_attack": t[3],
        "sp_defense": t[4],
        "speed": t[5],
    }


def _damage_stub_simple(level: int, power: int, atk_stat: int, def_stat: int) -> int:
    """Gen V–style physical/special damage before STAB and type chart."""
    a, d = max(1, atk_stat), max(1, def_stat)
    return math.floor(math.floor((2 * level / 5 + 2) * power * a / d) / 50) + 2


def _speed_tie_multiplier(attacker_speed: int, defender_speed: int) -> float:
    if attacker_speed > defender_speed:
        return 1.05
    if attacker_speed < defender_speed:
        return 0.95
    return 1.0


def best_competitive_turn_score(
    move_names: list[str],
    attacker_types: list[str],
    defender_types: list[str],
    a_stats: dict[str, int],
    d_stats: dict[str, int],
    level: int,
) -> float:
    """
    Max approximate damage across moves using competitive final stats, STAB, and type chart.
    Status moves contribute a small pressure score. Result is scaled by caller for speed.
    """
    atk_t = [t.lower() for t in attacker_types if t]
    def_t = [t.lower() for t in defender_types if t]
    if not move_names or not def_t:
        return 0.0

    best = 0.0
    for mv in move_names:
        det = move_pokeapi_details(str(mv))
        if not det:
            continue
        mt = (det.get("type") or "").lower()
        power = det.get("power")
        dc = (det.get("damage_class") or "status").lower()

        if power is None or int(power) <= 0 or dc == "status":
            best = max(best, _status_move_priority(str(mv)) * 0.12)
            continue

        pw = int(power)
        if dc == "physical":
            raw = _damage_stub_simple(level, pw, a_stats["attack"], d_stats["defense"])
        elif dc == "special":
            raw = _damage_stub_simple(level, pw, a_stats["sp_attack"], d_stats["sp_defense"])
        else:
            best = max(best, _status_move_priority(str(mv)) * 0.12)
            continue

        stab = 1.5 if mt in atk_t else 1.0
        tmult = type_multiplier(mt, def_t)
        best = max(best, float(raw) * stab * tmult)

    return best


def run_coverage_battle(
    my_rows: list[pd.Series],
    opp_rows: list[pd.Series],
    rng: random.Random,
    *,
    num_turns: int,
    move_pool: str,
    scoring: str,
    core4_cache: dict[str, list[str]],
) -> tuple[float, float, str]:
    """
    Random active slot each turn. Standard / max damage: type-chart effectiveness only.
    Competitive: Lv 50 + 31 IV + 252/252/4 + speed nature; damage stub × speed tie.
    """
    n_team = len(my_rows)
    if n_team < 1 or len(opp_rows) != n_team:
        raise ValueError("Both teams must be non-empty and the same size.")

    my_pts = 0.0
    opp_pts = 0.0
    hi = n_team - 1
    for _ in range(num_turns):
        i = rng.randint(0, hi)
        my_m = moves_for_battle_sim(my_rows[i], move_pool, core4_cache)
        opp_m = moves_for_battle_sim(opp_rows[i], move_pool, core4_cache)
        opp_types = parse_list_cell(opp_rows[i].get("types"))
        my_types = parse_list_cell(my_rows[i].get("types"))
        my_best = best_type_effectiveness_vs(my_m, opp_types)
        opp_best = best_type_effectiveness_vs(opp_m, my_types)
        if scoring == SCORING_STANDARD:
            my_pts += 1.0 if my_best > 1.0 else 0.0
            opp_pts += 1.0 if opp_best > 1.0 else 0.0
        elif scoring == SCORING_MAX_DAMAGE:
            my_pts += my_best if my_best > 1.0 else 0.0
            opp_pts += opp_best if opp_best > 1.0 else 0.0
        elif scoring == SCORING_COMPETITIVE:
            my_cs = competitive_final_stats_from_row(my_rows[i])
            opp_cs = competitive_final_stats_from_row(opp_rows[i])
            raw_my = best_competitive_turn_score(
                my_m,
                my_types,
                opp_types,
                my_cs,
                opp_cs,
                COMPETITIVE_BATTLE_LEVEL,
            )
            raw_opp = best_competitive_turn_score(
                opp_m,
                opp_types,
                my_types,
                opp_cs,
                my_cs,
                COMPETITIVE_BATTLE_LEVEL,
            )
            my_pts += raw_my * _speed_tie_multiplier(my_cs["speed"], opp_cs["speed"])
            opp_pts += raw_opp * _speed_tie_multiplier(opp_cs["speed"], my_cs["speed"])
        else:
            my_pts += my_best if my_best > 1.0 else 0.0
            opp_pts += opp_best if opp_best > 1.0 else 0.0

    if my_pts > opp_pts:
        return (my_pts, opp_pts, "win")
    if opp_pts > my_pts:
        return (my_pts, opp_pts, "loss")
    return (my_pts, opp_pts, "tie")


PARTY_SUBSET_OFF = "off"
PARTY_SUBSET_RANDOM = "random"
PARTY_SUBSET_ORACLE = "oracle"


def run_coverage_battle_party(
    my_party: list[pd.Series],
    opp_rows: list[pd.Series],
    rng: random.Random,
    *,
    battle_size: int,
    party_subset: str,
    num_turns: int,
    move_pool: str,
    scoring: str,
    core4_cache: dict[str, list[str]],
) -> tuple[float, float, str]:
    """
    Ranked is always battle_size=3. my_party is either three active Pokémon (party_subset off)
    or a six-Pokémon box when party_subset is random/oracle (pick three per battle).
    """
    battle_size = int(battle_size)
    if len(opp_rows) != battle_size:
        raise ValueError("Opponent team size must match battle_size.")
    if party_subset in (PARTY_SUBSET_RANDOM, PARTY_SUBSET_ORACLE):
        if len(my_party) != 6 or battle_size != 3:
            raise ValueError("Party subset modes require six Pokémon and 3v3 battles.")
        if party_subset == PARTY_SUBSET_RANDOM:
            trio_sets: list[list[pd.Series]] = [
                [my_party[i] for i in rng.sample(range(6), 3)]
            ]
        else:
            trio_sets = [
                [my_party[i] for i in comb]
                for comb in itertools.combinations(range(6), 3)
            ]
    else:
        if len(my_party) != battle_size:
            raise ValueError("Active team must have the same size as the battle (three for ranked).")
        trio_sets = [my_party]

    rank = {"win": 2, "tie": 1, "loss": 0}
    best_pr = -1
    best_margin = float("-inf")
    best_mp = best_op = 0.0
    best_oc = "loss"
    for trio in trio_sets:
        mp, op, oc = run_coverage_battle(
            trio,
            opp_rows,
            rng,
            num_turns=num_turns,
            move_pool=move_pool,
            scoring=scoring,
            core4_cache=core4_cache,
        )
        pr = rank[oc]
        margin = mp - op
        if pr > best_pr or (pr == best_pr and margin > best_margin):
            best_pr, best_margin = pr, margin
            best_mp, best_op, best_oc = mp, op, oc
    return (best_mp, best_op, best_oc)


def estimate_win_rate(
    my_rows: list[pd.Series],
    opp_frame: pd.DataFrame,
    *,
    opponent_champions_full_dex: bool,
    df_roster: pd.DataFrame,
    df_raw_data: pd.DataFrame,
    team_size: int,
    n_battles: int,
    num_turns: int,
    move_pool: str,
    scoring: str,
    rng: random.Random,
    party_subset: str = PARTY_SUBSET_OFF,
) -> tuple[int, int, int]:
    """
    Run n_battles Monte Carlo matches vs random opponents from opp_frame.
    Ranked uses team_size=3. If party_subset is random/oracle, my_rows must be six Pokémon
    (box); each match is still 3v3. Returns (wins, losses, ties). Mutates no Streamlit state.
    """
    source = df_raw_data if opponent_champions_full_dex else df_roster
    core4_cache: dict[str, list[str]] = {}
    for r in my_rows:
        core4_cache[str(r["name"])] = recommended_four_moves(r)

    wins = losses = ties = 0
    for _ in range(n_battles):
        opp_sample = opp_frame.sample(team_size, random_state=rng.randint(0, 10_000_000))
        onames = opp_sample["name"].tolist()
        opp_rows = [source.loc[source["name"] == on].iloc[0] for on in onames]
        for r in opp_rows:
            nm = str(r["name"])
            if nm not in core4_cache:
                core4_cache[nm] = recommended_four_moves(r)

        _my_pts, _opp_pts, outcome = run_coverage_battle_party(
            my_rows,
            opp_rows,
            rng,
            battle_size=team_size,
            party_subset=party_subset,
            num_turns=num_turns,
            move_pool=move_pool,
            scoring=scoring,
            core4_cache=core4_cache,
        )
        if outcome == "win":
            wins += 1
        elif outcome == "loss":
            losses += 1
        else:
            ties += 1

    return wins, losses, ties


def score_party_trios_paired(
    party_rows: list[pd.Series],
    opp_frame: pd.DataFrame,
    *,
    opponent_champions_full_dex: bool,
    df_roster: pd.DataFrame,
    df_raw_data: pd.DataFrame,
    n_rounds: int,
    num_turns: int,
    move_pool: str,
    scoring: str,
    rng: random.Random,
) -> list[tuple[str, int, int, int]]:
    """
    Rank all C(6,3) trios in a six-Pokémon box. Each round samples one random opponent team; every trio
    plays that same opponent, so win totals are paired and comparable. Returns rows sorted best-first:
    (trio label, wins, losses, ties).
    """
    if len(party_rows) != 6:
        raise ValueError("score_party_trios_paired requires exactly six Pokémon.")
    source = df_raw_data if opponent_champions_full_dex else df_roster
    trios: list[list[pd.Series]] = []
    labels: list[str] = []
    for idx in itertools.combinations(range(6), 3):
        rows3 = [party_rows[i] for i in idx]
        trios.append(rows3)
        labels.append(" / ".join(sorted(str(r["name"]) for r in rows3)))

    core4_cache: dict[str, list[str]] = {}
    for r in party_rows:
        core4_cache[str(r["name"])] = recommended_four_moves(r)

    wins = [0] * len(trios)
    losses = [0] * len(trios)
    ties_c = [0] * len(trios)

    for _ in range(n_rounds):
        opp_sample = opp_frame.sample(3, random_state=rng.randint(0, 10_000_000))
        onames = opp_sample["name"].tolist()
        opp_rows = [source.loc[source["name"] == on].iloc[0] for on in onames]
        for r in opp_rows:
            nm = str(r["name"])
            if nm not in core4_cache:
                core4_cache[nm] = recommended_four_moves(r)

        for ti, trio in enumerate(trios):
            _mp, _op, outcome = run_coverage_battle(
                trio,
                opp_rows,
                rng,
                num_turns=num_turns,
                move_pool=move_pool,
                scoring=scoring,
                core4_cache=core4_cache,
            )
            if outcome == "win":
                wins[ti] += 1
            elif outcome == "loss":
                losses[ti] += 1
            else:
                ties_c[ti] += 1

    ranked = list(zip(labels, wins, losses, ties_c))
    ranked.sort(key=lambda row: (-row[1], row[2], -row[3]))
    return ranked


st.set_page_config(page_title="Pokemon 2026 Macdro", layout="wide", initial_sidebar_state="expanded")
st.title("Pokemon 2026 Macdro")
st.caption("Pokémon Champions · Legends Z-A meta ledger")

csv_path = resolve_csv_path()
if csv_path is None:
    st.error("Could not find pokemon_meta_data.csv (script dir, cwd, or home).")
    st.stop()

df_raw = pd.read_csv(csv_path)
if "is_mega" in df_raw.columns:
    df_raw["is_mega"] = df_raw["is_mega"].map(
        lambda x: str(x).lower() in ("true", "1", "yes") if pd.notna(x) else False
    )


def filter_by_games(frame: pd.DataFrame, versions: list[str]) -> pd.DataFrame:
    if not versions:
        return frame.copy()
    mask = False
    for g in versions:
        mask = mask | frame["game_source"].astype(str).str.contains(g, case=False, na=False)
    return frame.loc[mask].copy()


def match_game_type_mode(src: str, mode: str) -> bool:
    """Refine rows by how game_source lists Champions vs Legends Z-A."""
    s = str(src).lower()
    has_c = "champions" in s
    has_z = "legends z-a" in s or ("legends" in s and "z-a" in s)
    if mode == "Any":
        return True
    if mode == "Champions only":
        return has_c and not has_z
    if mode == "Legends Z-A only":
        return has_z and not has_c
    if mode == "Both games":
        return has_c and has_z
    return True


def apply_sidebar_filters(
    frame: pd.DataFrame,
    type_selection: list[str],
    mega_mode: str,
    game_type_mode: str,
) -> pd.DataFrame:
    """Apply type, mega, and game-type filters (after game version)."""
    out = frame.copy()
    if type_selection:
        needles = {t.lower() for t in type_selection}

        def _types_overlap(cell) -> bool:
            return bool(needles.intersection({x.lower() for x in parse_list_cell(cell)}))

        out = out[out["types"].apply(_types_overlap)]
    if mega_mode == "Mega":
        out = out[out["is_mega"].astype(bool)]
    elif mega_mode == "Not mega":
        out = out[~out["is_mega"].astype(bool)]
    if game_type_mode != "Any":
        out = out[out["game_source"].apply(lambda s: match_game_type_mode(str(s), game_type_mode))]
    return out


with st.sidebar:
    st.header("Global filter")
    game_pick = st.multiselect(
        "Game version",
        options=["Champions", "Legends Z-A"],
        default=["Champions", "Legends Z-A"],
        help="Rows where game_source contains the selected label.",
    )
    type_pick = st.multiselect(
        "Type",
        options=[t.title() for t in TYPE_FILTER_ORDER],
        default=[],
        help="Pokémon that have any selected type (primary or secondary). Leave empty for all types.",
    )
    mega_pick = st.selectbox(
        "Mega",
        options=["All", "Mega", "Not mega"],
        index=0,
        help="Filter by Mega Evolution rows (is_mega).",
    )
    game_type_pick = st.selectbox(
        "Game type",
        options=["Any", "Champions only", "Legends Z-A only", "Both games"],
        index=0,
        help="Refine by how game_source tags Champions vs Legends Z-A (exclusive or both).",
    )


df_base = filter_by_games(df_raw, game_pick)
df = apply_sidebar_filters(df_base, type_pick, mega_pick, game_type_pick)
if df.empty:
    st.warning("No rows match the selected sidebar filters.")
    st.stop()

champs = df_raw[df_raw["game_source"].astype(str).str.contains("Champions", case=False, na=False)]

t1, t2, t3, t4 = st.tabs(["DEX Analyzer", "Movepool Inspector", "Team Builder", "Battle Simulator"])

with t1:
    st.subheader("The Ledger")
    search = st.text_input("Search roster", placeholder="Filter by name…")

    show = df.copy()
    if search.strip():
        show = show[show["name"].astype(str).str.contains(search.strip(), case=False, na=False)]

    if not show.empty and "pokeapi_id" in show.columns:
        show = show.sort_values(
            by="pokeapi_id",
            ascending=True,
            na_position="last",
            kind="mergesort",
        ).reset_index(drop=True)

    if show.empty:
        st.info("No Pokémon match this search.")
    else:
        disp = [c for c in show.columns if c not in LEDGER_HIDDEN_COLS]
        show_table = show[disp].copy()
        if "types" in show_table.columns:
            show_table["types"] = show_table["types"].apply(format_types_for_display)

        def _row_moveset_cell(r: pd.Series) -> str:
            mk = json.dumps(parse_list_cell(r.get("all_moves")))
            tk = json.dumps(parse_list_cell(r.get("types")))
            return ledger_moveset_display(
                str(r["name"]),
                mk,
                tk,
                int(r["attack"]),
                int(r["sp_attack"]),
            )

        with st.spinner("Computing **Moveset** column (PokeAPI per move; cached 24h after first load)…"):
            show_table["Moveset"] = show.apply(_row_moveset_cell, axis=1)

        ledger_event = st.dataframe(
            show_table,
            use_container_width=True,
            hide_index=True,
            column_order=ledger_column_order(list(show_table.columns)),
            column_config={
                "pokeapi_id": st.column_config.NumberColumn(
                    "PokéAPI id", help="Numeric id from PokéAPI /pokemon", format="%d"
                ),
                "image_url": st.column_config.ImageColumn("Art", width="small"),
                "Moveset": st.column_config.TextColumn("Moveset", width="large"),
            },
            on_select="rerun",
            selection_mode="single-row",
            key="ledger_df",
        )

        names = show["name"].astype(str).tolist()
        if st.session_state.get("ledger_sb") not in names:
            st.session_state["ledger_sb"] = names[0]

        ridx = ledger_dataframe_selection_row_index(ledger_event)
        if ridx is not None and 0 <= ridx < len(show):
            st.session_state["ledger_sb"] = str(show.iloc[ridx]["name"])

        st.caption(
            "Sorted by **PokéAPI id** (ascending). Click a **row** to sync the detail panel (deselect the row to use only the dropdown). "
            "**Moveset** = top 4 moves by the same heuristic as Team Builder."
        )
        pick = st.selectbox("Select Pokémon for detail", options=names, key="ledger_sb")

        row = show.loc[show["name"] == pick].iloc[0]
        c1, c2 = st.columns([1, 2])
        with c1:
            if pd.notna(row.get("image_url")):
                st.image(str(row["image_url"]), width=280)
            if bool(row.get("is_mega")):
                st.markdown(
                    '<div style="background:linear-gradient(90deg,#b8860b,#ffd700);color:#1a1a1a;'
                    'padding:10px 16px;border-radius:8px;font-weight:800;text-align:center;">'
                    "MEGA EVOLUTION DETECTED</div>",
                    unsafe_allow_html=True,
                )
        with c2:
            stats = {
                "HP": int(row["hp"]),
                "Attack": int(row["attack"]),
                "Defense": int(row["defense"]),
                "Sp. Atk": int(row["sp_attack"]),
                "Sp. Def": int(row["sp_defense"]),
                "Speed": int(row["speed"]),
            }
            fig = go.Figure()
            fig.add_trace(
                go.Scatterpolar(
                    r=list(stats.values()) + [list(stats.values())[0]],
                    theta=list(stats.keys()) + [list(stats.keys())[0]],
                    fill="toself",
                    name=pick,
                    line_color="#636efa",
                )
            )
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, max(160, max(stats.values()) + 20)])),
                showlegend=False,
                title="Base stats",
                margin=dict(t=60, b=40, l=40, r=40),
                height=420,
            )
            st.plotly_chart(fig, use_container_width=True)
            rmoves = recommended_four_moves(row)
            if rmoves:
                st.markdown("**Moveset:** " + " · ".join(rmoves))
            else:
                st.caption("Moveset could not be resolved (empty learnset or PokeAPI).")

with t2:
    st.subheader("The Audit")
    q = st.selectbox("Pokémon", options=sorted(df["name"].astype(str).unique()), key="mp")
    prow = df.loc[df["name"] == q].iloc[0]
    types = parse_list_cell(prow.get("types"))
    st.markdown(" ".join(type_badge_html(t) for t in types), unsafe_allow_html=True)
    moves = parse_list_cell(prow.get("all_moves"))
    st.write(f"**{len(moves)} moves** in learnset")
    cols = st.columns(4)
    for i, mv in enumerate(moves):
        with cols[i % 4]:
            st.button(str(mv), key=f"mv_{q}_{i}", disabled=True, use_container_width=True)


def _team_builder_insight(role: str, row: pd.Series) -> str:
    """Human-readable rationale tied to the meta-optimal role rules."""
    if role == "Pinned":
        return "**Pinned** by you—kept on the team before the remaining slots are filled from role bands."
    if role.startswith("Speedster"):
        return (
            f"**Speed {int(row['speed'])}** beats the **>110** benchmark. That usually means you move first "
            "in neutral matchups—better for picking off chipped targets, forcing Protect reads, and "
            "controlling speed control (Tailwind / Trick Room) timing."
        )
    if role.startswith("Tank"):
        hp, de = int(row["hp"]), int(row["defense"])
        return (
            f"**HP {hp}** and **Def {de}** satisfy the **>100 HP or Def** rule. This slot is your "
            "**pivot**: it can take a strong neutral hit, reposition, or buy a turn while your "
            "speedster or breaker finds an opening."
        )
    if role.startswith("Heavy"):
        atk, spa = int(row["attack"]), int(row["sp_attack"])
        return (
            f"**Atk {atk}** / **Sp. Atk {spa}**—at least one side clears **>110**. That's your "
            "**wallbreaker / closer** pressure: it punishes passive setups and helps crack typings "
            "that stall your faster piece."
        )
    return (
        "**Flex pick** drawn from the same filtered roster to complete six. Use it for **type coverage**, "
        "a second win condition, or insurance if a lead plan gets disrupted."
    )


def _max_team_weak_to_single_type(rows: list[pd.Series]) -> int:
    """Largest count of Pokémon in `rows` that are weak (>1×) to one attacking type."""
    if not rows:
        return 0
    worst = 0
    for atk in TYPE_FILTER_ORDER:
        c = 0
        for row in rows:
            dt = [t.lower() for t in parse_list_cell(row.get("types")) if t]
            if dt and type_multiplier(atk, dt) > 1.0:
                c += 1
        worst = max(worst, c)
    return worst


def _team_unique_types(rows: list[pd.Series]) -> set[str]:
    s: set[str] = set()
    for row in rows:
        for t in parse_list_cell(row.get("types")):
            s.add(str(t).lower().strip())
    return s


def _team_offensive_stab_coverage(rows: list[pd.Series]) -> int:
    """How many type names appear as STAB on at least one team member (diversity proxy)."""
    return len(_team_unique_types(rows))


def generate_role_band_team(
    p: pd.DataFrame,
    mode: str,
    rng: random.Random,
    speed_thr: int,
    bulk_thr: int,
    offense_thr: int,
    pinned_names: list[str],
) -> list[tuple[str, pd.Series]] | None:
    """
    Random team from role bands; pins are included first (order preserved), then pools fill the rest.
    """
    team_size = 3 if mode == "3v3" else 6

    def pool_speedster(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[frame["speed"] > speed_thr]

    def pool_tank(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[(frame["hp"] > bulk_thr) | (frame["defense"] > bulk_thr)]

    def pool_hitter(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[(frame["attack"] > offense_thr) | (frame["sp_attack"] > offense_thr)]

    seen: set[str] = set()
    picks: list[tuple[str, pd.Series]] = []

    for nm in pinned_names:
        if nm in seen:
            continue
        match = p.index[p["name"].astype(str) == nm]
        if len(match) == 0:
            continue
        row = p.loc[match[0]]
        picks.append(("Pinned", row))
        seen.add(str(row["name"]))
        if len(picks) >= team_size:
            break

    if len(picks) > team_size:
        picks = picks[:team_size]

    spd_full, tnk_full, hit_full = pool_speedster(p), pool_tank(p), pool_hitter(p)
    if spd_full.empty or tnk_full.empty or hit_full.empty:
        return None

    def sample_from(pool: pd.DataFrame, role: str) -> bool:
        if len(picks) >= team_size:
            return True
        sub = pool[~pool["name"].astype(str).isin(seen)]
        if sub.empty:
            sub = p[~p["name"].astype(str).isin(seen)]
        if sub.empty:
            return False
        row = sub.sample(1, random_state=rng.randint(0, 10_000_000)).iloc[0]
        nm = str(row["name"])
        picks.append((role, row))
        seen.add(nm)
        return True

    if mode == "3v3":
        if len(picks) < team_size and not sample_from(pool_speedster(p), "Speedster"):
            return None
        if len(picks) < team_size and not sample_from(pool_tank(p), "Tank"):
            return None
        if len(picks) < team_size and not sample_from(pool_hitter(p), "Heavy hitter"):
            return None
        picks = picks[:team_size]
    else:
        for pool_fn, base in (
            (pool_speedster, "Speedster"),
            (pool_tank, "Tank"),
            (pool_hitter, "Heavy hitter"),
        ):
            sub = pool_fn(p)
            sub = sub[~sub["name"].astype(str).isin(seen)]
            k = min(2, len(sub))
            if k == 0:
                continue
            sampled = sub.sample(k, random_state=rng.randint(0, 10_000_000))
            for j in range(len(sampled)):
                if len(picks) >= team_size:
                    break
                row = sampled.iloc[j]
                nm = str(row["name"])
                if nm in seen:
                    continue
                seen.add(nm)
                picks.append((f"{base} #{j + 1}", row))
        deduped: list[tuple[str, pd.Series]] = []
        seen2: set[str] = set()
        for role, row in picks:
            nm = str(row["name"])
            if nm in seen2:
                continue
            seen2.add(nm)
            deduped.append((role, row))
        picks = deduped
        seen = seen2
        while len(picks) < team_size:
            rest = p[~p["name"].astype(str).isin(seen)]
            if rest.empty:
                break
            row = rest.sample(1, random_state=rng.randint(0, 10_000_000)).iloc[0]
            nm = str(row["name"])
            seen.add(nm)
            picks.append(("Flex", row))
        picks = picks[:team_size]

    return picks if len(picks) == team_size else None


def render_team_builder_summary(picks: list[tuple[str, pd.Series]], core4_by_name: dict[str, list[str]]) -> None:
    rows = [pr for _, pr in picks]
    ut = _team_unique_types(rows)
    st.markdown("#### Team summary")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Unique typings (STAB slots)", len(ut))
    with c2:
        st.metric("Max weak to one type", _max_team_weak_to_single_type(rows))
    with c3:
        st.metric("Offensive type diversity", _team_offensive_stab_coverage(rows))

    weak_lines: list[str] = []
    for atk in TYPE_FILTER_ORDER:
        victims = [str(pr["name"]) for _, pr in picks if parse_list_cell(pr.get("types")) and type_multiplier(atk, [t.lower() for t in parse_list_cell(pr.get("types"))]) > 1.0]
        if len(victims) >= 2:
            weak_lines.append(f"**{atk.title()}** hits **{len(victims)}** super-effectively: {', '.join(victims)}")
    if weak_lines:
        st.markdown("**Shared pressure typings** (≥2 of your team weak)")
        for line in weak_lines[:12]:
            st.caption(line)
    else:
        st.caption("No offensive type hits two or more of your team super-effectively at once.")

    exp_txt = []
    for role, pr in picks:
        nm = str(pr["name"])
        ts = "/".join(str(t).title() for t in parse_list_cell(pr.get("types")))
        mv = core4_by_name.get(nm, [])
        exp_txt.append(f"{nm} ({role}) [{ts}] — {' / '.join(mv) if mv else '—'}")
    st.download_button(
        "Download team (.txt)",
        data="\n".join(exp_txt),
        file_name="pokemon_2026_macdro_team.txt",
        mime="text/plain",
        key="tb_download_team",
    )


with t3:
    st.subheader("Team Builder — role bands + random")
    st.caption(
        "Builds a **six-Pokémon party** for ranked play (Champions / Legends Z-A): you bring **three** in "
        "each ladder match. Random samples from **Speedster / Tank / Heavy hitter** pools on your "
        "**sidebar-filtered** roster. Tune thresholds and **seed** to explore; constraints optionally **retry** "
        "sampling. **Core 4** moves use the same **PokeAPI** heuristic as elsewhere."
    )

    tb_party_size = 6
    tb_opts = sorted(df["name"].astype(str).unique().tolist())

    def _randomize_team_builder_seed() -> None:
        # on_click runs before widgets bind keys — avoids StreamlitAPIException on tb_seed_val.
        st.session_state["tb_seed_val"] = random.randint(1, 2_147_483_646)

    sg1, sg2 = st.columns([2, 1])
    with sg1:
        tb_seed = st.number_input(
            "RNG seed (same seed + filters = reproducible; change for a new roll)",
            min_value=0,
            max_value=2_147_483_647,
            value=int(st.session_state.get("tb_seed_val", 4242)),
            step=1,
            key="tb_seed_val",
        )
    with sg2:
        st.write("")
        st.write("")
        st.button(
            "Randomize seed",
            key="tb_seed_rand",
            on_click=_randomize_team_builder_seed,
        )

    h1, h2, h3 = st.columns(3)
    with h1:
        thr_speed = st.number_input("Speedster: Speed >", min_value=1, max_value=200, value=110, key="tb_thr_spd")
    with h2:
        thr_bulk = st.number_input("Tank: HP or Def >", min_value=1, max_value=200, value=100, key="tb_thr_bulk")
    with h3:
        thr_off = st.number_input("Heavy: Atk or Sp. Atk >", min_value=1, max_value=200, value=110, key="tb_thr_off")

    pref_weak_spread = st.checkbox(
        "Prefer spread weaknesses — retry until **≤2** team members are weak to the same attacking type",
        value=True,
        key="tb_pref_weak",
    )
    pref_type_div = st.checkbox(
        "Prefer type diversity — retry until **≥3** unique typings on the team",
        value=True,
        key="tb_pref_div",
    )

    tb_pins = st.multiselect(
        "Pin Pokémon (always on the party if in the filtered roster; max six)",
        options=tb_opts,
        default=[],
        max_selections=tb_party_size,
        key="tb_pins_sel",
        help="Filled slots skip random picks for those Pokémon; remaining slots use role bands.",
    )

    if st.button("Generate team (role bands + random)", type="primary", key="tb_generate_btn"):
        p = df.copy()
        spd_chk = p[p["speed"] > int(thr_speed)]
        tnk_chk = p[(p["hp"] > int(thr_bulk)) | (p["defense"] > int(thr_bulk))]
        hit_chk = p[(p["attack"] > int(thr_off)) | (p["sp_attack"] > int(thr_off))]
        if spd_chk.empty or tnk_chk.empty or hit_chk.empty:
            st.error("Filtered roster too small for these role thresholds—lower the numbers.")
        else:
            picks: list[tuple[str, pd.Series]] | None = None
            for attempt in range(56):
                try_rng = random.Random(int(tb_seed) + attempt * 7919)
                cand = generate_role_band_team(
                    p,
                    "6v6",
                    try_rng,
                    int(thr_speed),
                    int(thr_bulk),
                    int(thr_off),
                    list(tb_pins),
                )
                if cand is None:
                    break
                rows_only = [pr for _, pr in cand]
                if pref_weak_spread and _max_team_weak_to_single_type(rows_only) > 2:
                    continue
                if pref_type_div and len(_team_unique_types(rows_only)) < min(3, len(rows_only)):
                    continue
                picks = cand
                break

            if picks is None:
                st.error(
                    "Could not build a team (empty pools, pins not in roster, or constraints too strict—"
                    "uncheck filters or lower thresholds)."
                )
            else:
                st.session_state["last_built_team"] = {
                    "format": "party_6",
                    "names": [str(prow["name"]) for _, prow in picks],
                }
                st.session_state["tb_last_roles"] = [role for role, _ in picks]
                st.session_state["tb_last_names"] = [str(prow["name"]) for _, prow in picks]

                with st.spinner("Ranking **best 4 moves** per Pokémon via PokeAPI (cached 24h)…"):
                    core4_by_name: dict[str, list[str]] = {}
                    for _, prow in picks:
                        nm = str(prow["name"])
                        if nm not in core4_by_name:
                            core4_by_name[nm] = recommended_four_moves(prow)
                    st.session_state["tb_core4"] = core4_by_name

                st.rerun()

    if st.session_state.get("tb_last_names") and st.session_state.get("tb_last_roles"):
        try:
            tnames = st.session_state["tb_last_names"]
            troles = st.session_state["tb_last_roles"]
            picks = []
            for ri, nm in enumerate(tnames):
                row = df.loc[df["name"] == nm].iloc[0]
                picks.append((troles[ri], row))
            core4_by_name = st.session_state.get("tb_core4", {})

            hb1, hb2 = st.columns([4, 1])
            with hb1:
                st.markdown("#### Current build")
            with hb2:
                if st.button("Clear team", key="tb_clear_disp"):
                    for k in ("tb_last_names", "tb_last_roles", "tb_core4", "last_built_team"):
                        st.session_state.pop(k, None)
                    st.rerun()

            st.info(
                f"**Speedster:** Speed > **{thr_speed}** · **Tank:** HP or Def > **{thr_bulk}** · "
                f"**Heavy:** Atk or Sp. Atk > **{thr_off}** · seed **{int(tb_seed)}**. "
                f"Constraints: **weak spread** {'on' if pref_weak_spread else 'off'}, "
                f"**type diversity** {'on' if pref_type_div else 'off'}."
            )

            render_team_builder_summary(picks, core4_by_name)

            with st.expander("Quick simulator — win rate vs random opponents", expanded=False):
                st.caption(
                    "Ranked is always **3v3**. With a **six-Pokémon** party, choose how the simulator picks "
                    "your three each match. Same toy model as **Battle Simulator** (not cartridge/Showdown). "
                    "**Oracle** runs up to **20** trio simulations per battle (all C(6,3))."
                )
                q1, q2 = st.columns(2)
                with q1:
                    tb_q_opp = st.selectbox(
                        "Opponent pool",
                        options=["Champions (full dex)", "Sidebar-filtered roster"],
                        index=0,
                        key="tb_quick_opp",
                    )
                with q2:
                    tb_q_bpt = st.number_input(
                        "Battles",
                        min_value=12,
                        max_value=400,
                        value=40,
                        step=4,
                        key="tb_quick_bpt",
                    )
                tb_q_turns = st.number_input(
                    "Turns per battle",
                    min_value=4,
                    max_value=24,
                    value=8,
                    key="tb_quick_turns",
                )
                tb_q_moves = st.selectbox(
                    "Moves considered",
                    options=["Suggested 4 (heuristic)", "Full learnset (trimmed if huge)"],
                    index=0,
                    key="tb_quick_moves",
                )
                n_party = len(picks)
                tb_party_subset = PARTY_SUBSET_OFF
                if n_party == 6:
                    tb_q_party = st.selectbox(
                        "Six-Pokémon party: how to pick your 3 each match",
                        options=[
                            "Random 3 from box each battle",
                            "Oracle — best of 20 trios vs that opponent",
                        ],
                        index=0,
                        key="tb_quick_party",
                    )
                    tb_party_subset = (
                        PARTY_SUBSET_ORACLE
                        if "Oracle" in tb_q_party
                        else PARTY_SUBSET_RANDOM
                    )
                else:
                    if n_party == 3:
                        st.caption(
                            "This build has **three** Pokémon (legacy save): scored as a fixed **3v3** team."
                        )
                    elif n_party not in (3, 6):
                        st.warning(
                            "Expected **six** (party) or **three** (fixed team) Pokémon for ranked quick sim."
                        )
                st.markdown("**Scoring**")
                tb_q_score_pick = st.radio(
                    "Quick sim scoring",
                    options=list(BATTLE_SCORING_OPTIONS),
                    horizontal=True,
                    label_visibility="collapsed",
                    key="tb_quick_score",
                )
                st.caption(BATTLE_SCORING_DESCRIPTIONS[tb_q_score_pick])
                tb_q_scoring = BATTLE_SCORING_INTERNAL[tb_q_score_pick]
                render_rules_summary(
                    format_label="Ranked 3v3",
                    opponent_label=("Champions" if tb_q_opp == "Champions (full dex)" else "sidebar-filtered roster"),
                    move_pool=tb_q_moves,
                    scoring_label=BATTLE_SCORING_SUMMARY_LABEL.get(tb_q_scoring, tb_q_scoring),
                    seed=int(tb_seed),
                )
                sims_per_battle = 20 if tb_party_subset == PARTY_SUBSET_ORACLE else 1
                est_sims = int(tb_q_bpt) * sims_per_battle
                st.caption(
                    f"Estimated work: **{est_sims}** battle sims "
                    f"({int(tb_q_bpt)} battles × {sims_per_battle} sim/battle)."
                )

                if st.button("Run quick win-rate estimate", key="tb_quick_run"):
                    opp_f = champs if tb_q_opp == "Champions (full dex)" else df
                    ranked_size = 3
                    if opp_f.empty or len(opp_f) < ranked_size:
                        st.warning("Opponent pool too small for ranked 3v3.")
                    elif n_party not in (3, 6):
                        st.warning("Regenerate a six-Pokémon party (or use a three-Pokémon legacy team).")
                    elif n_party == 6 and len({str(pr["name"]) for _, pr in picks}) < 6:
                        st.warning("Party must have **six distinct** Pokémon.")
                    else:
                        my_rows = [pr for _, pr in picks]
                        rng_q = random.Random(int(tb_seed) + 31337)
                        w, ell, tie_c = estimate_win_rate(
                            my_rows,
                            opp_f,
                            opponent_champions_full_dex=(tb_q_opp == "Champions (full dex)"),
                            df_roster=df,
                            df_raw_data=df_raw,
                            team_size=ranked_size,
                            n_battles=int(tb_q_bpt),
                            num_turns=int(tb_q_turns),
                            move_pool=tb_q_moves,
                            scoring=tb_q_scoring,
                            rng=rng_q,
                            party_subset=tb_party_subset if n_party == 6 else PARTY_SUBSET_OFF,
                        )
                        nb = int(tb_q_bpt)
                        wr = w / nb
                        lo, hi = wilson_score_interval(w, nb)
                        st.metric("Wins / Losses / Ties", f"{w} / {ell} / {tie_c}")
                        st.metric(
                            "Win rate",
                            f"{100 * wr:.1f}%",
                            help=f"Wilson 95% (wins): {100 * lo:.1f}%–{100 * hi:.1f}%",
                        )
                        st.caption(f"Estimate confidence: **{confidence_badge(nb)}** (n={nb} battles).")

            with st.expander("Best trio in this box (paired rounds)", expanded=False):
                st.caption(
                    "Ranks all **20** trios from your six-Pokémon party. Each **round** uses **one** random "
                    "opponent team; every trio faces that same team so the leaderboard is **apples-to-apples** "
                    "inside the box. Reuses **opponent pool**, **turns**, **moves**, and **scoring** from "
                    "**Quick simulator** above."
                )
                if n_party != 6:
                    st.info("Generate a **six-Pokémon** party to rank trios here.")
                elif len({str(pr["name"]) for _, pr in picks}) < 6:
                    st.warning("Party must have **six distinct** Pokémon.")
                else:
                    br1, br2 = st.columns(2)
                    with br1:
                        tb_box_rounds = st.number_input(
                            "Rounds",
                            min_value=8,
                            max_value=400,
                            value=48,
                            step=4,
                            key="tb_box_trios_rounds",
                            help="Each round = 20 trio vs same opponent battles.",
                        )
                    with br2:
                        tb_box_topn = st.number_input(
                            "Show top N trios",
                            min_value=3,
                            max_value=20,
                            value=8,
                            step=1,
                            key="tb_box_trios_topn",
                        )
                    st.caption(
                        f"Estimated work: **{int(tb_box_rounds) * 20}** battle sims "
                        f"({int(tb_box_rounds)} rounds × 20 trios)."
                    )
                    if st.button("Rank trios in this party", key="tb_box_trios_run"):
                        opp_fb = champs if tb_q_opp == "Champions (full dex)" else df
                        if opp_fb.empty or len(opp_fb) < 3:
                            st.warning("Opponent pool too small for 3v3.")
                        else:
                            party_rows_tb = [pr for _, pr in picks]
                            rng_tb = random.Random(int(tb_seed) + 90001)
                            with st.spinner(
                                f"**{int(tb_box_rounds)}** rounds × **20** trios vs same opponent each round…"
                            ):
                                ranked_tb = score_party_trios_paired(
                                    party_rows_tb,
                                    opp_fb,
                                    opponent_champions_full_dex=(
                                        tb_q_opp == "Champions (full dex)"
                                    ),
                                    df_roster=df,
                                    df_raw_data=df_raw,
                                    n_rounds=int(tb_box_rounds),
                                    num_turns=int(tb_q_turns),
                                    move_pool=tb_q_moves,
                                    scoring=tb_q_scoring,
                                    rng=rng_tb,
                                )
                            best = ranked_tb[0]
                            nbtr = int(tb_box_rounds)
                            wr_b = best[1] / nbtr
                            lo_b, hi_b = wilson_score_interval(best[1], nbtr)
                            st.success(
                                f"**Best trio:** {best[0]} — **{best[1]}**W / **{best[2]}**L / **{best[3]}**T "
                                f"over **{nbtr}** paired rounds"
                            )
                            st.metric(
                                "Best trio win rate",
                                f"{100 * wr_b:.1f}%",
                                help=f"Wilson 95% (wins): {100 * lo_b:.1f}%–{100 * hi_b:.1f}%",
                            )
                            st.caption(f"Estimate confidence: **{confidence_badge(nbtr)}** (n={nbtr} rounds).")
                            topn = min(int(tb_box_topn), len(ranked_tb))
                            rows_df = []
                            for lab, wv, lv, tv in ranked_tb[:topn]:
                                rows_df.append(
                                    {
                                        "Trio": lab,
                                        "W": wv,
                                        "L": lv,
                                        "T": tv,
                                        "Win %": round(100 * wv / nbtr, 1),
                                    }
                                )
                            st.dataframe(
                                pd.DataFrame(rows_df),
                                hide_index=True,
                                use_container_width=True,
                            )

            st.markdown("#### Roster cards")
            ncols = 3
            for row_start in range(0, len(picks), ncols):
                row_slice = picks[row_start : row_start + ncols]
                cols = st.columns(ncols)
                for col, (role, prow) in zip(cols, row_slice):
                    with col:
                        if pd.notna(prow.get("image_url")):
                            st.image(str(prow["image_url"]), use_container_width=True)
                        st.markdown(f"**{prow['name']}**")
                        st.caption(format_types_for_display(prow.get("types")))
                        st.caption(role)
                        core4 = core4_by_name.get(str(prow["name"]), [])
                        st.markdown("**Suggested 4 moves**")
                        if core4:
                            pad = (core4 + [None] * 4)[:4]
                            with st.container(border=True):
                                top_l, top_r = st.columns(2)
                                with top_l:
                                    if pad[0]:
                                        st.button(
                                            pad[0],
                                            key=f"tb_{prow['name']}_{role}_{row_start}_q0",
                                            disabled=True,
                                            use_container_width=True,
                                        )
                                    else:
                                        st.caption("—")
                                with top_r:
                                    if pad[1]:
                                        st.button(
                                            pad[1],
                                            key=f"tb_{prow['name']}_{role}_{row_start}_q1",
                                            disabled=True,
                                            use_container_width=True,
                                        )
                                    else:
                                        st.caption("—")
                                bot_l, bot_r = st.columns(2)
                                with bot_l:
                                    if pad[2]:
                                        st.button(
                                            pad[2],
                                            key=f"tb_{prow['name']}_{role}_{row_start}_q2",
                                            disabled=True,
                                            use_container_width=True,
                                        )
                                    else:
                                        st.caption("—")
                                with bot_r:
                                    if pad[3]:
                                        st.button(
                                            pad[3],
                                            key=f"tb_{prow['name']}_{role}_{row_start}_q3",
                                            disabled=True,
                                            use_container_width=True,
                                        )
                                    else:
                                        st.caption("—")
                        else:
                            st.caption("No moves resolved (check network / PokeAPI).")
                        with st.expander("Why this Pokémon"):
                            st.markdown(_team_builder_insight(role, prow))
        except (KeyError, IndexError):
            st.caption("Regenerate the team after changing sidebar filters (saved names left the roster).")
            if st.button("Clear saved team", key="tb_clear_saved"):
                for k in ("tb_last_names", "tb_last_roles", "tb_core4", "last_built_team"):
                    st.session_state.pop(k, None)
                st.rerun()

with t4:
    st.subheader("Monte Carlo — coverage simulator")
    st.caption(
        "Ranked (Champions / Legends Z-A) is **3v3** only. Build a **six-Pokémon party** here or in Team Builder, "
        "then score how often a **random or oracle** trio wins vs random opponents. Each **turn** picks a random "
        "active slot on both teams. **Standard Coverage** and **Max Damage** use type effectiveness (PokeAPI, "
        "**cached 24h**). **Competitive EV/IV** uses **Lv 50** stats with **31 IV**, **252 / 252 / 4** EVs, "
        "**Timid**/**Jolly**, then a **damage stub** scaled by **Speed** (+5% / −5%)."
    )

    c_opt1, c_opt2 = st.columns(2)
    with c_opt1:
        opponent_pool = st.selectbox(
            "Opponent pool",
            options=["Champions (full dex)", "Sidebar-filtered roster"],
            index=0,
            help="Random opposing **3-Pokémon** teams for ranked 3v3.",
        )
    with c_opt2:
        move_pool = st.selectbox(
            "Moves considered",
            options=["Suggested 4 (heuristic)", "Full learnset (trimmed if huge)"],
            index=0,
            help="Suggested 4 matches Team Builder heuristics. Full learnset caps at 55 moves "
            "(head+tail) to limit PokeAPI calls.",
        )

    st.markdown("**Scoring**")
    scoring_choice = st.radio(
        "Scoring mode",
        options=list(BATTLE_SCORING_OPTIONS),
        horizontal=True,
        label_visibility="collapsed",
        key="battle_scoring_mode",
    )
    st.caption(BATTLE_SCORING_DESCRIPTIONS[scoring_choice])
    scoring = BATTLE_SCORING_INTERNAL[scoring_choice]

    s1, s2, s3 = st.columns(3)
    with s1:
        num_battles = st.number_input("Battles", min_value=20, max_value=5000, value=100, step=20)
    with s2:
        num_turns = st.number_input("Turns per battle", min_value=4, max_value=24, value=8, step=1)
    with s3:
        seed_val = st.number_input("RNG seed", min_value=0, max_value=2_147_483_647, value=42, step=1)

    opp_frame = champs if opponent_pool == "Champions (full dex)" else df
    pool_label = "Champions" if opponent_pool == "Champions (full dex)" else "filtered roster"

    ranked_battle_size = 3

    bs_roster_mode = st.radio(
        "Your roster",
        ["Active 3 (ranked ladder)", "Party box (6 Pokémon)"],
        horizontal=True,
        key="bs_roster_mode",
        help="Ladder uses three Pokémon per match. Party mode keeps six in the box and picks three each battle.",
    )
    bs_party_subset_ui = PARTY_SUBSET_OFF
    if bs_roster_mode == "Party box (6 Pokémon)":
        bs_party_pick = st.selectbox(
            "How to pick your three each battle",
            options=[
                "Random 3 from box each battle",
                "Oracle — best of 20 trios vs that opponent",
            ],
            key="bs_party_subset_pick",
        )
        bs_party_subset_ui = (
            PARTY_SUBSET_ORACLE if "Oracle" in bs_party_pick else PARTY_SUBSET_RANDOM
        )
    render_rules_summary(
        format_label="Ranked 3v3",
        opponent_label=pool_label,
        move_pool=move_pool,
        scoring_label=BATTLE_SCORING_SUMMARY_LABEL.get(scoring, scoring),
        seed=int(seed_val),
    )

    for _i in range(6):
        if f"bs_dd_{_i}" not in st.session_state:
            st.session_state[f"bs_dd_{_i}"] = "—"

    if opp_frame.empty or len(opp_frame) < ranked_battle_size:
        st.warning(
            f"Opponent pool ({pool_label}) needs at least **{ranked_battle_size}** Pokémon for ranked 3v3; "
            "adjust filters or CSV."
        )
    else:
        my_opts = sorted(df["name"].astype(str).unique().tolist())
        blank = "—"
        sel_opts = [blank] + my_opts

        st.markdown("##### Your team")
        tb = st.session_state.get("last_built_team")
        if tb and tb.get("names"):
            st.caption(
                f"Last Team Builder party ({tb.get('format', '?')}): **{', '.join(tb['names'])}**"
            )
        else:
            st.caption(
                "Use **Team Builder → Generate team (role bands + random)**, then **Apply last Team Builder team** here."
            )

        if st.button("Apply last Team Builder team", key="bs_apply_tb"):
            if not tb or not tb.get("names"):
                st.warning("Open **Team Builder** and generate a party first.")
            else:
                nms = list(tb["names"])
                for i in range(6):
                    if i < len(nms) and nms[i] in my_opts:
                        st.session_state[f"bs_dd_{i}"] = nms[i]
                    else:
                        st.session_state[f"bs_dd_{i}"] = blank
                st.rerun()

        slot_count = 6 if bs_roster_mode == "Party box (6 Pokémon)" else 3
        for i in range(slot_count):
            label = f"Pokémon {i + 1}" if slot_count == 3 else f"Party slot {i + 1}"
            st.selectbox(
                label,
                options=sel_opts,
                key=f"bs_dd_{i}",
                help="Filtered sidebar roster.",
            )

        opponent_champions_full = opponent_pool == "Champions (full dex)"

        with st.expander("Best trio in this box (paired rounds)", expanded=False):
            st.caption(
                "Ranks all **20** trios from your **six-Pokémon** party. Each **round** samples **one** random "
                "3v3 opponent; every trio faces that same team—fair comparison **within the box** only. Uses "
                "**turns**, **moves**, and **scoring** from this tab."
            )
            bx1, bx2 = st.columns(2)
            with bx1:
                bs_box_rounds = st.number_input(
                    "Rounds",
                    min_value=8,
                    max_value=400,
                    value=48,
                    step=4,
                    key="bs_box_trios_rounds",
                    help="Each round runs 20 battles (one per trio) vs the same opponent.",
                )
            with bx2:
                bs_box_topn = st.number_input(
                    "Show top N trios",
                    min_value=3,
                    max_value=20,
                    value=8,
                    step=1,
                    key="bs_box_trios_topn",
                )
            st.caption(
                f"Estimated work: **{int(bs_box_rounds) * 20}** battle sims "
                f"({int(bs_box_rounds)} rounds × 20 trios)."
            )
            if bs_roster_mode != "Party box (6 Pokémon)":
                st.info("Switch to **Party box (6 Pokémon)** and fill six distinct slots.")
            elif st.button("Rank trios in this party", type="secondary", key="bs_box_trios_run"):
                bn: list[str] = []
                bad = False
                for i in range(6):
                    sel = st.session_state.get(f"bs_dd_{i}", blank)
                    if not sel or sel == blank:
                        st.error(f"Party slot **{i + 1}** is empty.")
                        bad = True
                        break
                    bn.append(sel)
                if not bad and len(set(bn)) != 6:
                    st.error("Party must have **six distinct** Pokémon.")
                    bad = True
                if not bad:
                    party_rows_bs = [df.loc[df["name"] == n].iloc[0] for n in bn]
                    rng_bs = random.Random(int(seed_val) + 61289)
                    with st.spinner(
                        f"**{int(bs_box_rounds)}** rounds × **20** trios (same opponent per round)…"
                    ):
                        ranked_bs = score_party_trios_paired(
                            party_rows_bs,
                            opp_frame,
                            opponent_champions_full_dex=opponent_champions_full,
                            df_roster=df,
                            df_raw_data=df_raw,
                            n_rounds=int(bs_box_rounds),
                            num_turns=int(num_turns),
                            move_pool=move_pool,
                            scoring=scoring,
                            rng=rng_bs,
                        )
                    best_b = ranked_bs[0]
                    nbr = int(bs_box_rounds)
                    wr_bb = best_b[1] / nbr
                    lo_bb, hi_bb = wilson_score_interval(best_b[1], nbr)
                    st.success(
                        f"**Best trio:** {best_b[0]} — **{best_b[1]}**W / **{best_b[2]}**L / **{best_b[3]}**T "
                        f"over **{nbr}** paired rounds"
                    )
                    st.metric(
                        "Best trio win rate",
                        f"{100 * wr_bb:.1f}%",
                        help=f"Wilson 95% (wins): {100 * lo_bb:.1f}%–{100 * hi_bb:.1f}%",
                    )
                    st.caption(f"Estimate confidence: **{confidence_badge(nbr)}** (n={nbr} rounds).")
                    top_nb = min(int(bs_box_topn), len(ranked_bs))
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Trio": lab,
                                    "W": wv,
                                    "L": lv,
                                    "T": tv,
                                    "Win %": round(100 * wv / nbr, 1),
                                }
                                for lab, wv, lv, tv in ranked_bs[:top_nb]
                            ]
                        ),
                        hide_index=True,
                        use_container_width=True,
                    )

        with st.expander("Find best team by simulator win rate", expanded=False):
            st.caption(
                "Searches **3-Pokémon** active trios from the **filtered roster** (ranked format)—not a six-Pokémon "
                "party box. Optimizes **this app’s toy simulator** only—not cartridge or Showdown. "
                "**Random search** finds a strong trio, not a proven global optimum on large rosters. "
                "Many candidates reuse **PokeAPI** move data (**cached 24h**)."
            )
            ox1, ox2, ox3 = st.columns(3)
            with ox1:
                max_exhaustive_combos = st.number_input(
                    "Max combos for exhaustive",
                    min_value=20,
                    max_value=5000,
                    value=350,
                    step=10,
                    key="opt_max_exh",
                    help="If C(roster, team size) ≤ this, every team is evaluated; otherwise random trials.",
                )
            with ox2:
                opt_battles_per_team = st.number_input(
                    "Battles per candidate",
                    min_value=10,
                    max_value=800,
                    value=40,
                    step=10,
                    key="opt_bpt",
                )
            with ox3:
                opt_random_trials = st.number_input(
                    "Random trials (non-exhaustive)",
                    min_value=5,
                    max_value=400,
                    value=48,
                    step=4,
                    key="opt_ntrials",
                )

            R = len(my_opts)
            search_team_size = ranked_battle_size
            n_combos = math.comb(R, search_team_size) if R >= search_team_size else 0
            use_exhaustive = n_combos > 0 and n_combos <= int(max_exhaustive_combos)
            if use_exhaustive:
                st.info(
                    f"**Exhaustive:** **{n_combos}** trios × **{int(opt_battles_per_team)}** battles each "
                    f"(~**{n_combos * int(opt_battles_per_team)}** total battles). Ranked **3v3** only."
                )
            elif R < search_team_size:
                st.warning("Filtered roster is smaller than three; cannot search.")
            else:
                st.info(
                    f"**Random search:** **{int(opt_random_trials)}** sampled **3-Pokémon** teams "
                    f"(C({R},{search_team_size}) = **{n_combos}** > **{int(max_exhaustive_combos)}** cap)."
                )

            if st.button("Run team search", type="secondary", key="opt_run_search"):
                if R < search_team_size:
                    st.error("Not enough Pokémon in the filtered roster.")
                else:
                    rng_s = random.Random(int(seed_val) + 90210)
                    if use_exhaustive:
                        team_iter = list(itertools.combinations(my_opts, search_team_size))
                    else:
                        cap_trials = min(int(opt_random_trials), n_combos)
                        seen: set[tuple[str, ...]] = set()
                        team_iter = []
                        attempts = 0
                        max_attempts = cap_trials * 80
                        while len(team_iter) < cap_trials and attempts < max_attempts:
                            attempts += 1
                            draw = tuple(sorted(rng_s.sample(my_opts, search_team_size)))
                            if draw not in seen:
                                seen.add(draw)
                                team_iter.append(draw)

                    n_teams = len(team_iter)
                    if n_teams == 0:
                        st.error("No teams to evaluate.")
                    else:
                        best_names: tuple[str, ...] | None = None
                        best_wins = -1
                        best_losses = 0
                        best_ties = 0

                        with st.spinner(
                            f"Searching **{n_teams}** trios × **{int(opt_battles_per_team)}** battles "
                            f"(same scoring, moves, turns, and opponent pool as above)…"
                        ):
                            bar = st.progress(0)
                            for ti, tnames in enumerate(team_iter):
                                mrows = [df.loc[df["name"] == n].iloc[0] for n in tnames]
                                w, loss_ct, tie_ct = estimate_win_rate(
                                    mrows,
                                    opp_frame,
                                    opponent_champions_full_dex=opponent_champions_full,
                                    df_roster=df,
                                    df_raw_data=df_raw,
                                    team_size=search_team_size,
                                    n_battles=int(opt_battles_per_team),
                                    num_turns=int(num_turns),
                                    move_pool=move_pool,
                                    scoring=scoring,
                                    rng=rng_s,
                                )
                                if w > best_wins or (
                                    w == best_wins and loss_ct < best_losses
                                ):
                                    best_wins = w
                                    best_losses = loss_ct
                                    best_ties = tie_ct
                                    best_names = tnames
                                bar.progress((ti + 1) / n_teams)
                            bar.empty()

                        if best_names is not None:
                            nb = int(opt_battles_per_team)
                            wr = best_wins / nb
                            lo, hi = wilson_score_interval(best_wins, nb)
                            st.success(
                                f"**Best team:** {', '.join(best_names)} — "
                                f"**{best_wins}**W / **{best_losses}**L / **{best_ties}**T "
                                f"over **{nb}** battles each"
                            )
                            st.metric(
                                "Best estimated win rate",
                                f"{100 * wr:.1f}%",
                                help=f"Wilson 95% interval (wins only): {100 * lo:.1f}%–{100 * hi:.1f}%",
                            )
                            st.caption(
                                f"Estimate confidence: **{confidence_badge(nb)}** "
                                f"(n={nb} battles per candidate)."
                            )
                            st.caption(
                                f"Search: **{'exhaustive' if use_exhaustive else 'random'}** · "
                                f"**{n_teams}** teams · **{nb}** battles/team · "
                                f"RNG **{int(seed_val) + 90210}** · opponent **{pool_label}** · "
                                f"{BATTLE_SCORING_SUMMARY_LABEL.get(scoring, scoring)} scoring."
                            )

        def _gather_my_team() -> tuple[list[str] | None, str | None]:
            names: list[str] = []
            n_need = 6 if bs_roster_mode == "Party box (6 Pokémon)" else 3
            for i in range(n_need):
                sel = st.session_state.get(f"bs_dd_{i}", blank)
                label = f"Party slot {i + 1}" if n_need == 6 else f"Pokémon {i + 1}"
                if not sel or sel == blank:
                    return None, f"Choose **{label}** from the dropdown."
                names.append(sel)
            if n_need == 6 and len(set(names)) != 6:
                return None, "Party must have **six distinct** Pokémon."
            return names, None

        tn, _ = _gather_my_team()
        if tn:
            if len(tn) == 6:
                st.caption(
                    f"**Ready:** party of six — matches are **3v3** "
                    f"({'oracle' if bs_party_subset_ui == PARTY_SUBSET_ORACLE else 'random'} trio per battle)."
                )
            else:
                st.caption(f"**Ready (active 3):** {', '.join(tn)}")
        else:
            st.caption("Complete all slots to run battles, or apply from Team Builder.")

        run_label = f"Run {int(num_battles)} battles"
        if st.button(run_label, type="primary", key="bs_run_battles"):
            team_names, team_err = _gather_my_team()
            if not team_names:
                st.error(team_err or "Incomplete team.")
            else:
                rng = random.Random(int(seed_val))
                my_rows = [df.loc[df["name"] == n].iloc[0] for n in team_names]
                party_subset_run = (
                    bs_party_subset_ui
                    if bs_roster_mode == "Party box (6 Pokémon)"
                    else PARTY_SUBSET_OFF
                )
                core4_cache: dict[str, list[str]] = {}
                for r in my_rows:
                    core4_cache[str(r["name"])] = recommended_four_moves(r)

                wins = losses = ties = 0
                battle_log: list[dict] = []
                log_cap = min(25, max(5, int(num_battles) // 20))

                bar = st.progress(0)
                n_b = int(num_battles)
                for b in range(n_b):
                    opp_sample = opp_frame.sample(
                        ranked_battle_size, random_state=rng.randint(0, 10_000_000)
                    )
                    onames = opp_sample["name"].tolist()
                    source = df_raw if opponent_pool == "Champions (full dex)" else df
                    opp_rows = [source.loc[source["name"] == on].iloc[0] for on in onames]
                    for r in opp_rows:
                        nm = str(r["name"])
                        if nm not in core4_cache:
                            core4_cache[nm] = recommended_four_moves(r)

                    my_pts, opp_pts, outcome = run_coverage_battle_party(
                        my_rows,
                        opp_rows,
                        rng,
                        battle_size=ranked_battle_size,
                        party_subset=party_subset_run,
                        num_turns=int(num_turns),
                        move_pool=move_pool,
                        scoring=scoring,
                        core4_cache=core4_cache,
                    )
                    if outcome == "win":
                        wins += 1
                    elif outcome == "loss":
                        losses += 1
                    else:
                        ties += 1

                    if len(battle_log) < log_cap:
                        battle_log.append(
                            {
                                "#": b + 1,
                                "result": outcome.upper(),
                                "you": round(my_pts, 2),
                                "opp": round(opp_pts, 2),
                                "they": ", ".join(str(x) for x in onames),
                            }
                        )

                    bar.progress((b + 1) / n_b)
                bar.empty()

                win_rate = wins / n_b
                lo, hi = wilson_score_interval(wins, n_b)
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Wins", wins)
                with m2:
                    st.metric("Losses", losses)
                with m3:
                    st.metric("Ties", ties)
                st.metric(
                    "Win rate",
                    f"{100 * win_rate:.1f}%",
                    help=f"Wilson 95% interval (wins only): {100 * lo:.1f}%–{100 * hi:.1f}%",
                )
                st.caption(f"Estimate confidence: **{confidence_badge(n_b)}** (n={n_b} battles).")
                party_note = ""
                if party_subset_run == PARTY_SUBSET_ORACLE:
                    party_note = " · party **oracle** (≤20 sims/battle)"
                elif party_subset_run == PARTY_SUBSET_RANDOM:
                    party_note = " · party **random 3**"
                st.caption(
                    f"{n_b} battles vs random **{pool_label}** **3v3** teams · "
                    f"**{int(num_turns)}** turns/battle · seed **{int(seed_val)}** · "
                    f"**{move_pool.split()[0]}** moves · "
                    f"**{BATTLE_SCORING_SUMMARY_LABEL.get(scoring, scoring)}** scoring"
                    f"{party_note}."
                )

                with st.expander("Sample battle log (first battles in this run)"):
                    st.dataframe(pd.DataFrame(battle_log), hide_index=True, use_container_width=True)
