"""Flight performance calculations and matplotlib plots (from the tutorial script)."""
import base64, io, math
import numpy as np
from matplotlib.figure import Figure

G = 9.81

ALT_KEYS = ["h1", "h2", "h3", "h4", "h5", "h6"]

def altitudes(P):
    return sorted({P[k] for k in ALT_KEYS})

# (group title, [(key, label, default), ...])
GROUPS = [
    ("Aircraft", [("S", "Wing area S (m²)", 47), ("AR", "Aspect ratio AR", 6.5),
                  ("W", "Gross weight W (N)", 103047), ("eng", "Number of engines", 2)]),
    ("Aerodynamics", [("e", "Oswald efficiency e", 0.87), ("CD0", "Zero-lift drag coeff. CD,0", 0.032),
                      ("CLmax", "CL,max", 0.8), ("CLflap", "CL,max (flaps fully deployed)", 2.8),
                      ("CLpd", "CL,max (pitch down)", 1.5)]),
    ("Propulsion", [("Tpe", "Thrust per engine at sea level (N)", 40298), ("Ct", "TSFC Ct (1/s)", 1 / 3600),
                    ("fuel", "Fuel (gallons of kerosene)", 1900)]),
    ("Limits & take-off", [("nLu", "Structural limit, positive load factor", 5), ("nLd", "Structural limit, negative load factor", -3),
                           ("mu", "Rolling friction coeff. μ", 0.02), ("CLg", "CL during ground roll", 0.8),
                           ("kto", "Take-off speed factor (× stall speed)", 1.2), ("R", "Airborne arc radius R (m)", 1356.64),
                           ("hobs", "Obstacle height (m)", 50)]),
    ("Altitudes (whole km, 0–5)", [("h1", "Altitude 1 (km)", 1), ("h2", "Altitude 2 (km)", 4),
                               ("h3", "Altitude 3 (km)", 0), ("h4", "Altitude 4 (km)", 2),
                               ("h5", "Altitude 5 (km)", 3), ("h6", "Altitude 6 (km)", 5)]),
    ("Air density (kg/m³)", [(f"rho_{i}", f"Density at {i} km", d) for i, d in
                             enumerate([1.225, 1.112, 1.006, 0.909, 0.819, 0.736])]),
]
FIELDS = [t for _, g in GROUPS for t in g]
DEFAULTS = {k: d for k, _, d in FIELDS}

THEMES = {
    "dark": dict(bg="#171b22", fg="#e6e8ec", grid="#2f3642", blue="#6b9bff", red="#ff6b6b",
                 orange="#ffa94d", green="#51cf66", purple="#b197fc", gray="#8b94a5"),
    "light": dict(bg="#ffffff", fg="#1f2430", grid="#d9dde4", blue="#2563eb", red="#e5484d",
                  orange="#f08c00", green="#2f9e44", purple="#9b5de5", gray="#888888"),
}


def calc(P, h):
    h = int(h)
    rho = P[f"rho_{h}"]
    S, AR, e, CD0, W = P["S"], P["AR"], P["e"], P["CD0"], P["W"]
    k = 1 / (math.pi * AR * e)
    V = np.arange(25, 500)

    q = 0.5 * rho * V**2 * S
    TR = q * CD0 + q * k * (W / q) ** 2
    TA = P["Tpe"] * P["eng"] * rho / P["rho_0"]
    TRmin_graph = TR.min()
    TRmin = W * math.sqrt(4 * CD0 * k)
    Vtr = math.sqrt((2 / rho) * (W / S) * math.sqrt(k / CD0))

    diff = TR - TA
    Vmax = 0.0
    for i in np.where(np.diff(np.sign(diff)) != 0)[0]:
        Vmax = V[i] - diff[i] * ((V[i + 1] - V[i]) / (diff[i + 1] - diff[i]))

    PR, PA = TR * V, TA * V
    ROC = (PA - PR) / W
    mi = int(np.argmax(ROC))

    Vs = math.sqrt(2 * W / (rho * S * P["CLmax"]))
    Vap = math.sqrt(2 * W * P["nLu"] / (rho * S * P["CLmax"]))
    Van = math.sqrt(2 * W * abs(P["nLd"]) / (rho * S * P["CLpd"]))

    # take-off
    Sg = 1.21 * (W / S) / (G * rho * P["CLg"] * (TA / W))
    Vx = P["kto"] * math.sqrt(2 * W / (rho * S * P["CLg"]))
    th_max = math.acos(1 - P["hobs"] / P["R"])
    Sa = P["R"] * math.sin(th_max)

    mask = (V >= Vs) & (V <= Vmax)
    return dict(h=h, rho=rho, k=k, V=V, TR=TR, TA=TA, PR=PR, PA=PA, ROC=ROC,
                TRmin_graph=TRmin_graph, TRmin=TRmin, err=abs(TRmin - TRmin_graph) / TRmin * 100,
                Vtr=Vtr, Vmax=Vmax, max_roc=ROC[mi], V_roc=V[mi], Vs=Vs, Vap=Vap, Van=Van,
                vp=np.linspace(0, Vap, 100), vn=np.linspace(0, Van, 100),
                Sg=Sg, Vx=Vx, Sa=Sa, Sto=Sg + Sa, th_max=th_max, Vh=V[mask], Vv=ROC[mask])


def f(x, d=2):
    return f"{x:,.{d}f}"


def cards(P, r):
    rs = [calc(P, h) for h in altitudes(P)]
    join = lambda key, d: " / ".join(f(x[key], d) for x in rs)
    return [
        ("Thrust required", [("Min. (from curve)", f"{f(r['TRmin_graph'])} N"), ("Min. (theory)", f"{f(r['TRmin'])} N"),
                             ("Error", f"{f(r['err'], 3)} %"), ("Speed at min. thrust", f"{f(r['Vtr'])} m/s"),
                             ("k = 1/(π·AR·e)", f(r["k"], 4))]),
        ("Thrust available & max speed", [("Total sea-level thrust", f"{f(P['Tpe'] * P['eng'])} N"),
                                          (f"Thrust at {r['h']} km", f"{f(r['TA'])} N"),
                                          ("Density", f"{f(r['rho'], 3)} kg/m³"),
                                          ("Max level-flight speed", f"{f(r['Vmax'])} m/s")]),
        ("Rate of climb", [("Max rate of climb", f"{f(r['max_roc'])} m/s"), ("Speed at max ROC", f"{f(r['V_roc'])} m/s"),
                           ("Stall speed (CL,max)", f"{f(r['Vs'])} m/s")]),
        ("V-n diagram", [("Corner speed (pitch up)", f"{f(r['Vap'])} m/s"), ("Corner speed (pitch down)", f"{f(r['Van'])} m/s"),
                         ("Load factor limits", f"{P['nLd']:g} to +{P['nLu']:g}"), ("Propulsive limit", f"{f(r['Vmax'])} m/s")]),
        ("Take-off", [(f"Take-off speed ({P['kto']:g}·Vstall)", f"{f(r['Vx'])} m/s"), ("Ground roll", f"{f(r['Sg'])} m"),
                      ("Airborne distance", f"{f(r['Sa'])} m"), (f"Total over {P['hobs']:g} m obstacle", f"{f(r['Sto'])} m")]),
        (f"Effect of altitude ({' / '.join(str(x['h']) for x in rs)} km)", [
            ("Min. thrust required", f"{join('TRmin', 0)} N"),
            ("Thrust available", f"{join('TA', 0)} N"),
            ("Max speed", f"{join('Vmax', 1)} m/s"),
            ("Max ROC", f"{join('max_roc', 1)} m/s")]),
    ]


# ---------- plots ----------
def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
    return base64.b64encode(buf.getvalue()).decode()


def _fig(title, xl, yl, theme):
    C = THEMES[theme]
    fig = Figure(figsize=(6.4, 4), facecolor=C["bg"])
    ax = fig.subplots()
    ax.set_facecolor(C["bg"])
    ax.set_title(title, color=C["fg"], fontsize=11)
    ax.set_xlabel(xl, color=C["fg"]); ax.set_ylabel(yl, color=C["fg"])
    ax.tick_params(colors=C["fg"])
    for s in ax.spines.values():
        s.set_color(C["grid"])
    ax.grid(color=C["grid"], alpha=0.8)
    return fig, ax, C


def _legend(ax, C, **kw):
    leg = ax.legend(facecolor=C["bg"], edgecolor=C["grid"], labelcolor=C["fg"], **kw)
    return leg


def plots(P, r, theme="dark"):
    h, out, V = r["h"], [], r["V"]

    fig, ax, C = _fig(f"Thrust vs Velocity (h = {h} km)", "Velocity (m/s)", "Thrust (N)", theme)
    ax.plot(V, r["TR"], color=C["blue"], label="Thrust required")
    ax.plot(V, np.full(V.shape, r["TA"], dtype=float), color=C["red"], label="Thrust available")
    ax.plot(r["Vmax"], r["TA"], "o", color=C["fg"]); _legend(ax, C)
    out.append(("Thrust vs velocity", _png(fig)))

    fig, ax, C = _fig(f"Power vs Velocity (h = {h} km)", "Velocity (m/s)", "Power (W)", theme)
    ax.plot(V, r["PR"], color=C["blue"], label="Power required"); ax.plot(V, r["PA"], color=C["red"], label="Power available")
    _legend(ax, C)
    out.append(("Power vs velocity", _png(fig)))

    fig, ax, C = _fig(f"Rate of Climb vs Velocity (h = {h} km)", "Velocity (m/s)", "Rate of climb (m/s)", theme)
    ax.plot(V, r["ROC"], color=C["blue"], label="ROC"); ax.plot(r["V_roc"], r["max_roc"], "o", color=C["red"], label="Max ROC")
    _legend(ax, C)
    out.append(("Rate of climb", _png(fig)))

    fig, ax, C = _fig(f"V-n Diagram (h = {h} km)", "Velocity (m/s)", "Load factor n", theme)
    rho, S, W = r["rho"], P["S"], P["W"]
    ax.plot(r["vp"], 0.5 * rho * r["vp"] ** 2 * S * P["CLmax"] / W, color=C["blue"], label="Aerodynamic limit (PU)")
    ax.plot(r["vn"], -0.5 * rho * r["vn"] ** 2 * S * P["CLpd"] / W, color=C["red"], label="Aerodynamic limit (PD)")
    ax.plot([r["Vap"], r["Vmax"]], [P["nLu"]] * 2, color=C["orange"], label="Structural limit (PU)")
    ax.plot([r["Van"], r["Vmax"]], [P["nLd"]] * 2, color=C["purple"], label="Structural limit (PD)")
    ax.plot([r["Vmax"]] * 2, [P["nLd"], P["nLu"]], color=C["green"], label="Propulsive limit")
    _legend(ax, C, fontsize=7)
    out.append(("V-n diagram", _png(fig)))

    fig, ax, C = _fig(f"Take-off Trajectory (h = {h} km)", "Distance (m)", "Height (m)", theme)
    th = np.linspace(0, r["th_max"], 200)
    ax.plot([0, r["Sg"]], [0, 0], color=C["orange"], label="Ground roll")
    ax.plot(r["Sg"] + P["R"] * np.sin(th), P["R"] * (1 - np.cos(th)), color=C["blue"], label="Airborne trajectory")
    ax.axhline(P["hobs"], color=C["gray"], ls="--", label=f"{P['hobs']:g} m obstacle")
    ax.scatter(r["Sto"], P["hobs"], color=C["red"], zorder=5, label="Obstacle cleared"); _legend(ax, C)
    out.append(("Take-off trajectory", _png(fig)))

    fig, ax, C = _fig(f"Hodograph (h = {h} km)", "Horizontal speed Vh (m/s)", "Vertical speed Vv (m/s)", theme)
    ax.plot(np.append(r["Vh"], r["Vmax"]), np.append(r["Vv"], 0.0), color=C["blue"], label="Hodograph")
    ax.scatter(r["V_roc"], r["max_roc"], color=C["red"], zorder=5)
    ax.annotate("Max RoC", (r["V_roc"], r["max_roc"]), xytext=(10, 10), textcoords="offset points", color=C["fg"])
    ax.scatter(r["Vmax"], 0, color=C["red"], zorder=5)
    ax.annotate("Vmax", (r["Vmax"], 0), xytext=(-40, 10), textcoords="offset points", color=C["fg"])
    _legend(ax, C)
    out.append(("Hodograph", _png(fig)))
    return out


def altitude_plot(P, theme="dark"):
    fig, ax, C = _fig("Effect of Altitude on Thrust Required", "Velocity (m/s)", "Thrust required (N)", theme)
    cols = [C["blue"], C["orange"], C["green"], C["red"], C["purple"], C["gray"]]
    for h, c in zip(altitudes(P), cols):
        r = calc(P, h)
        ax.plot(r["V"], r["TR"], color=c, label=f"h = {r['h']} km (ρ = {r['rho']:g})")
    _legend(ax, C)
    return ("Effect of altitude on thrust required", _png(fig))