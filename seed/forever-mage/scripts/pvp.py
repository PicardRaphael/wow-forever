"""pvp.py — profil PvP d'un build : burst, contrôle, survie, dégâts soutenus en kite. Statut : EST.

Il n'existe aucun simulateur PvP : ce modèle compare des builds entre eux sur des scénarios explicites,
il ne prédit pas un résultat de duel. Chaque composante est calculée avec les mécaniques de fm.py
(toucher 96 % contre un joueur du même niveau, critiques, Shatter sur cible gelée, etc.).
"""
import fm

REF = {"burst": 2500.0, "control": 30.0, "survival": 30.0, "sustain": 350.0}     # échelles de normalisation (niveau 60)
DEFAULT_W = {"burst": 0.35, "control": 0.25, "survival": 0.25, "sustain": 0.15}

def _e(key, L, pts, ch, **kw):
    return fm.expected_cast(key, L, pts, ch, 0, **kw)

def burst(pts, L, ch):
    """Dégâts attendus dans une fenêtre d'ouverture de 6 s, meilleure séquence disponible."""
    seqs = []
    fb = _e("frostbolt", L, pts, ch); il_f = _e("ice_lance", L, pts, ch, frozen=True)
    fb_f = _e("frostbolt", L, pts, ch, frozen=True); nova = _e("frost_nova", L, pts, ch)
    if fb:
        s = fb["dmg"] + (nova["dmg"] if nova else 0)
        t = fb["cast"] + (1.5 if nova else 0)
        if nova and il_f:
            n_il = max(0, int((6 - t) // 1.5)); s += n_il * il_f["dmg"] * (0.6 if n_il > 1 else 1.0)
        elif nova and fb_f:
            s += fb_f["dmg"]
        seqs.append(("Givre : Éclair, Nova, Javelot(s) sur gel", s))
    fi = _e("fireball", L, pts, ch); fbl = _e("fire_blast", L, pts, ch); py = _e("pyroblast", L, pts, ch)
    bw = _e("blast_wave", L, pts, ch)
    if fi:
        s = fi["dmg"] + (fbl["dmg"] if fbl else 0) + (bw["dmg"] if bw else 0)
        if py and pts.get("presenceOfMind"):
            s += py["dmg"]
        if pts.get("combustion"):
            s *= 1.12
        seqs.append(("Feu : Boule, Trait, (Présence + Pyro), Vague", s))
    ab = _e("arcane_blast", L, pts, ch); am = _e("arcane_missiles", L, pts, ch)
    if am:
        mult = 1.30 if pts.get("arcanePower") else 1.0
        s = am["dmg"] * mult
        if ab:
            s = (2 * ab["dmg"] + am["dmg"] * 1.2) * mult * (1.0 if pts.get("presenceOfMind") else 0.8)
        seqs.append(("Arcanes : (Puissance) Déflagrations + Projectiles", s))
    return max(seqs, key=lambda x: x[1]) if seqs else ("aucune", 0.0)

def control(pts, L):
    """Secondes de contrôle utile par minute (gel, ralentis pondérés 0,5, silence, étourdissements)."""
    c = 0.0
    nova = fm.best_rank("frost_nova", L, pts)
    if nova:
        cd = nova[7] - fm.tval(pts, "improvedFrostNova"); c += 60 / cd * 5.0          # gel effectif ~5 s (cassé par les dégâts)
    casts = 60 / 2.5
    c += casts * fm.tval(pts, "frostbite") / 100 * 5.0 * 0.5                        # Frostbite (moitié des sorts sont givre)
    if fm.best_rank("frostbolt", L, pts):
        c += 0.5 * 40 * (1 + fm.tval(pts, "permafrost", 0) / 100)                   # ralenti d'Éclair ~40 s/min, poids 0,5
    if fm.best_rank("cone_of_cold", L, pts):
        c += 0.5 * 6 * 6
    c += casts * fm.tval(pts, "impact") / 100 * 2.0 * 0.5
    if pts.get("blastWave"):
        c += 0.5 * 6 * 60 / 45
    if L >= 24:
        c += 60 / 30 * (fm.tval(pts, "improvedCounterspell") + 10 * 0.3)             # silence + verrouillage d'école pondéré
    return c

def survival(pts, L, race):
    """Secondes de survie gagnées par minute face à un mêlée de référence (EST)."""
    s = 0.0
    if pts.get("iceBlock"): s += 10 * 60 / 300 * (1.6 if pts.get("coldSnap") else 1.0)
    ib = [r for r in fm.data().utility["ice_barrier"]["ranks"] if r[0] <= L] if pts.get("iceBarrier") else []
    if ib: s += ib[-1][1] / 300.0 * 60 / 30 * 3                                       # 1 s de survie ≈ 100 dégâts absorbés
    if L >= 20: s += 60 / 15 * 1.2                                                   # Transfert : ~1,2 s de mêlée évitée
    s += fm.tval(pts, "frostWarding") / 100 * 2 + fm.tval(pts, "arcaneResilience") / 100 * 3
    s += fm.tval(pts, "improvedFrostNova") * 0.5 + fm.tval(pts, "permafrost", 1) * 0.1
    rac = {"Human": 6.0, "Undead": 3.0, "Orc": 3.5, "Gnome": 3.0, "Troll": 1.5}.get(race, 1.0)
    return s + rac

def sustain(pts, L, ch, moving=0.4):
    best = 0.0
    for key in ("frostbolt", "fireball", "arcane_missiles", "arcane_blast"):
        e = _e(key, L, pts, ch)
        if e: best = max(best, e["dmg"] / e["cast"])
    inst = 0.0
    for key in ("fire_blast", "ice_lance", "cone_of_cold"):
        e = _e(key, L, pts, ch)
        if e: inst += e["dmg"] / max(1.5, e["cooldown"] or 1.5) * (0.3 if key == "ice_lance" else 1.0)
    return best * (1 - moving) + min(inst, best) * moving

def score(pts, level=60, race="Orc", weights=None, over=None):
    w = {**DEFAULT_W, **(weights or {})}
    ch = fm.character(level, race, over or ({"sp": 400, "spell_crit": 0.12} if level == 60 else None))
    b_name, b = burst(pts, level, ch)
    comp = {"burst": b, "control": control(pts, level), "survival": survival(pts, level, race), "sustain": sustain(pts, level, ch)}
    sc = sum(w[k] * min(1.5, comp[k] / REF[k]) for k in w) * 100
    return {"score": round(sc, 1), "burst_seq": b_name, **{k: round(v, 1) for k, v in comp.items()}, "statut": "EST"}
