"""2026 Battle Architect — streamlit run app.py"""

from __future__ import annotations

import ast
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
    One abstract battle: random lane each turn, score from type effectiveness of movepool.
    Returns (my_score, opp_score, outcome) with outcome in win, loss, tie.
    """
    my_pts = 0.0
    opp_pts = 0.0
    for _ in range(num_turns):
        i = rng.randint(0, 2)
        my_m = moves_for_battle_sim(my_rows[i], move_pool, core4_cache)
        opp_m = moves_for_battle_sim(opp_rows[i], move_pool, core4_cache)
        opp_types = parse_list_cell(opp_rows[i].get("types"))
        my_types = parse_list_cell(my_rows[i].get("types"))
        my_best = best_type_effectiveness_vs(my_m, opp_types)
        opp_best = best_type_effectiveness_vs(opp_m, my_types)
        if scoring == "Binary (1 pt if any super-effective)":
            my_pts += 1.0 if my_best > 1.0 else 0.0
            opp_pts += 1.0 if opp_best > 1.0 else 0.0
        else:
            my_pts += my_best if my_best > 1.0 else 0.0
            opp_pts += opp_best if opp_best > 1.0 else 0.0

    if my_pts > opp_pts:
        return (my_pts, opp_pts, "win")
    if opp_pts > my_pts:
        return (my_pts, opp_pts, "loss")
    return (my_pts, opp_pts, "tie")


st.set_page_config(page_title="2026 Battle Architect", layout="wide", initial_sidebar_state="expanded")
st.title("2026 Battle Architect")
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

t1, t2, t3, t4 = st.tabs(["DEX Analyzer", "Movepool Inspector", "Team Builder", "Battle Simulator"])

with t1:
    st.subheader("The Ledger")
    search = st.text_input("Search roster", placeholder="Filter by name…")

    show = df.copy()
    if search.strip():
        show = show[show["name"].astype(str).str.contains(search.strip(), case=False, na=False)]
    disp = [c for c in show.columns if c != "all_moves"]
    show_table = show[disp].copy()
    if "types" in show_table.columns:
        show_table["types"] = show_table["types"].apply(format_types_for_display)
    st.dataframe(
        show_table,
        use_container_width=True,
        hide_index=True,
        column_config={"image_url": st.column_config.ImageColumn("Art", width="small")},
    )
    names = show["name"].astype(str).tolist()
    pick = st.selectbox("Select Pokémon for detail", options=names or ["—"])
    if pick and pick != "—":
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


with t3:
    st.subheader("3v3 / 6v6")
    mode = st.radio("Format", ["3v3", "6v6"], horizontal=True)

    def pool_speedster(p):
        return p[p["speed"] > 110]

    def pool_tank(p):
        return p[(p["hp"] > 100) | (p["defense"] > 100)]

    def pool_hitter(p):
        return p[(p["attack"] > 110) | (p["sp_attack"] > 110)]

    if st.button("Generate Meta-Optimal Team", type="primary"):
        p = df.copy()
        spd, tnk, hit = pool_speedster(p), pool_tank(p), pool_hitter(p)
        if spd.empty or tnk.empty or hit.empty:
            st.error("Filtered roster too small for role pools.")
        else:
            picks: list[tuple[str, pd.Series]] = []
            if mode == "3v3":
                rs1, rs2, rs3 = random.randint(0, 99999), random.randint(0, 99999), random.randint(0, 99999)
                picks = [
                    ("Speedster", spd.sample(1, random_state=rs1).iloc[0]),
                    ("Tank", tnk.sample(1, random_state=rs2).iloc[0]),
                    ("Heavy hitter", hit.sample(1, random_state=rs3).iloc[0]),
                ]
            else:
                rng = random.Random()
                for pool_fn, base in (
                    (pool_speedster, "Speedster"),
                    (pool_tank, "Tank"),
                    (pool_hitter, "Heavy hitter"),
                ):
                    sub = pool_fn(p)
                    k = min(2, len(sub))
                    sampled = sub.sample(k, random_state=rng.randint(0, 10_000_000))
                    for j in range(len(sampled)):
                        picks.append((f"{base} #{j + 1}", sampled.iloc[j]))
                seen: set[str] = set()
                deduped: list[tuple[str, pd.Series]] = []
                for role, row in picks:
                    nm = str(row["name"])
                    if nm in seen:
                        continue
                    seen.add(nm)
                    deduped.append((role, row))
                picks = deduped
                while len(picks) < 6:
                    rest = p[~p["name"].astype(str).isin(seen)]
                    if rest.empty:
                        break
                    row = rest.sample(1, random_state=rng.randint(0, 10_000_000)).iloc[0]
                    nm = str(row["name"])
                    seen.add(nm)
                    picks.append(("Flex", row))
                picks = picks[:6]

            with st.spinner("Ranking **best 4 moves** per Pokémon via PokeAPI (results are cached for 24h)…"):
                core4_by_name: dict[str, list[str]] = {}
                for _, prow in picks:
                    nm = str(prow["name"])
                    if nm not in core4_by_name:
                        core4_by_name[nm] = recommended_four_moves(prow)

            st.success("Suggested team")
            st.markdown("#### Why this recommendation")
            st.info(
                "The builder **randomly samples** from your **sidebar-filtered** roster using three "
                "**archetype bands**: **Speedster** (Speed > 110), **Tank** (HP or Def > 100), and "
                "**Heavy hitter** (Atk or Sp. Atk > 110). Together they target **tempo**, **durability**, "
                "and **wallbreaking**—a compact checklist for short games. "
                + (
                    "In **6v6**, you get up to **two** picks per band when possible, then **Flex** slots to reach six."
                    if mode == "6v6"
                    else ""
                )
                + " Each card’s **core 4 moves** are auto-ranked from that Pokémon’s learnset using **PokeAPI** "
                "(base power, STAB, physical vs special bias from its stats, plus a small priority list for "
                "common support moves)—a **heuristic**, not a copied tournament export."
            )

            ncols = 3
            for row_start in range(0, len(picks), ncols):
                row_slice = picks[row_start : row_start + ncols]
                cols = st.columns(ncols)
                for col, (role, prow) in zip(cols, row_slice):
                    with col:
                        if pd.notna(prow.get("image_url")):
                            st.image(str(prow["image_url"]), use_container_width=True)
                        st.markdown(f"**{prow['name']}**")
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

with t4:
    st.subheader("Monte Carlo — coverage simulator")
    st.caption(
        "Toy benchmark: each **turn** picks a random slot on both trios. Scores come from **type "
        "effectiveness** of moves in the chosen pool (PokeAPI move types, **cached 24h**). "
        "This is **not** a damage or speed simulator."
    )

    champs = df_raw[df_raw["game_source"].astype(str).str.contains("Champions", case=False, na=False)]

    c_opt1, c_opt2 = st.columns(2)
    with c_opt1:
        opponent_pool = st.selectbox(
            "Opponent pool",
            options=["Champions (full dex)", "Sidebar-filtered roster"],
            index=0,
            help="Where random opposing trios are sampled from.",
        )
    with c_opt2:
        move_pool = st.selectbox(
            "Moves considered",
            options=["Suggested 4 (heuristic)", "Full learnset (trimmed if huge)"],
            index=0,
            help="Suggested 4 matches Team Builder heuristics. Full learnset caps at 55 moves "
            "(head+tail) to limit PokeAPI calls.",
        )

    scoring = st.radio(
        "Scoring",
        options=[
            "Binary (1 pt if any super-effective)",
            "Weighted (add effectiveness: 2× or 4× per turn when SE)",
        ],
        horizontal=True,
    )

    s1, s2, s3 = st.columns(3)
    with s1:
        num_battles = st.number_input("Battles", min_value=20, max_value=5000, value=100, step=20)
    with s2:
        num_turns = st.number_input("Turns per battle", min_value=4, max_value=24, value=8, step=1)
    with s3:
        seed_val = st.number_input("RNG seed", min_value=0, max_value=2_147_483_647, value=42, step=1)

    opp_frame = champs if opponent_pool == "Champions (full dex)" else df
    pool_label = "Champions" if opponent_pool == "Champions (full dex)" else "filtered roster"

    if opp_frame.empty or len(opp_frame) < 3:
        st.warning(f"Opponent pool ({pool_label}) needs at least 3 Pokémon; adjust filters or CSV.")
    else:
        my_opts = sorted(df["name"].astype(str).unique().tolist())
        team3 = st.multiselect("Your team (pick 3)", options=my_opts, max_selections=3)
        run_label = f"Run {int(num_battles)} battles"
        if len(team3) == 3 and st.button(run_label, type="primary"):
            rng = random.Random(int(seed_val))
            my_rows = [df.loc[df["name"] == n].iloc[0] for n in team3]
            core4_cache: dict[str, list[str]] = {}
            for r in my_rows:
                core4_cache[str(r["name"])] = recommended_four_moves(r)

            wins = losses = ties = 0
            battle_log: list[dict] = []
            log_cap = min(25, max(5, int(num_battles) // 20))

            bar = st.progress(0)
            n_b = int(num_battles)
            for b in range(n_b):
                opp_sample = opp_frame.sample(3, random_state=rng.randint(0, 10_000_000))
                onames = opp_sample["name"].tolist()
                source = df_raw if opponent_pool == "Champions (full dex)" else df
                opp_rows = [source.loc[source["name"] == on].iloc[0] for on in onames]
                for r in opp_rows:
                    nm = str(r["name"])
                    if nm not in core4_cache:
                        core4_cache[nm] = recommended_four_moves(r)

                my_pts, opp_pts, outcome = run_coverage_battle(
                    my_rows,
                    opp_rows,
                    rng,
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
            st.caption(
                f"{n_b} battles vs random **{pool_label}** trios · **{int(num_turns)}** turns/battle · "
                f"seed **{int(seed_val)}** · **{move_pool.split()[0]}** moves · "
                f"{'binary' if 'Binary' in scoring else 'weighted'} scoring."
            )

            with st.expander("Sample battle log (first battles in this run)"):
                st.dataframe(pd.DataFrame(battle_log), hide_index=True, use_container_width=True)
