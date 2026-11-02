"""Flight performance calculations and matplotlib plots (from the tutorial script)."""
import base64, io, math
import numpy as np
from matplotlib.figure import Figure

G = 9.81

# key, label, default
FIELDS = [
    ("S", "Wing area S (m²)", 47), ("AR", "Aspect ratio AR", 6.5),
    ("e", "Oswald efficiency e", 0.87), ("CD0", "Zero-lift drag coeff. CD,0", 0.032),
    ("W", "Gross weight W (N)", 103047), ("eng", "Number of engines", 2),
    ("Tpe", "Thrust per engine at sea level (N)", 40298), ("fuel", "Fuel (gallons of kerosene)", 1900),
    ("Ct", "TSFC Ct (1/s)", 1 / 3600), ("CLmax", "CL,max", 0.8),
    ("CLflap", "CL,max (flaps fully deployed)", 2.8), ("CLpd", "CL,max (pitch down)", 1.5),
    ("mu", "Rolling friction coeff. μ", 0.02), ("nLu", "Structural limit, positive load factor", 5),
    ("nLd", "Structural limit, negative load factor", -3), ("R", "Take-off airborne arc radius R (m)", 1356.64),
    ("hobs", "Obstacle height (m)", 50), ("rho0", "Density at 0 km (kg/m³)", 1.225),
    ("rho1", "Density at 1 km (kg/m³)", 1.112), ("rho4", "Density at 4 km (kg/m³)", 0.819),
]
DEFAULTS = {k: d for k, _, d in FIELDS}


def calc(P, h):
    rho = P["rho1"] if h == 1 else P["rho4"]
    S, AR, e, CD0, W = P["S"], P["AR"], P["e"], P["CD0"], P["W"]
    k = 1 / (math.pi * AR * e)
    V = np.arange(25, 500)

    q = 0.5 * rho * V**2 * S
    TR = q * CD0 + q * k * (W / q) ** 2
    TA = P["Tpe"] * P["eng"] * rho / P["rho0"]
    TRmin_graph = TR.min()
    TRmin = W * math.sqrt(4 * CD0 * k)
    Vtr = math.sqrt((2 / rho) * (W / S) * math.sqrt(k / CD0))

    # maximum speed: last crossing of TR and TA (linear interpolation)
    diff = TR - TA
    Vmax = 0.0
    for i in np.where(np.diff(np.sign(diff)) != 0)[0]:
        Vmax = V[i] - diff[i] * ((V[i + 1] - V[i]) / (diff[i + 1] - diff[i]))

    PR, PA = TR * V, TA * V
    ROC = (PA - PR) / W
    mi = int(np.argmax(ROC))

    # V-n diagram
    Vs = math.sqrt(2 * W / (rho * S * P["CLmax"]))
    Vap = math.sqrt(2 * W * P["nLu"] / (rho * S * P["CLmax"]))
    Van = math.sqrt(2 * W * abs(P["nLd"]) / (rho * S * P["CLpd"]))
    vp = np.linspace(0, Vap, 100)
    vn = np.linspace(0, Van, 100)

    # take-off
    Sg = 1.21 * (W / S) / (G * rho * P["CLmax"] * (TA / W))
    Vx = 1.2 * Vs
    th_max = math.acos(1 - P["hobs"] / P["R"])
    Sa = P["R"] * math.sin(th_max)

    # hodograph
    mask = (V >= Vs) & (V <= Vmax)
    return dict(h=h, rho=rho, k=k, V=V, TR=TR, TA=TA, PR=PR, PA=PA, ROC=ROC,
                TRmin_graph=TRmin_graph, TRmin=TRmin, err=abs(TRmin - TRmin_graph) / TRmin * 100,
                Vtr=Vtr, Vmax=Vmax, max_roc=ROC[mi], V_roc=V[mi], Vs=Vs, Vap=Vap, Van=Van,
                vp=vp, vn=vn, Sg=Sg, Vx=Vx, Sa=Sa, Sto=Sg + Sa, th_max=th_max,
                Vh=V[mask], Vv=ROC[mask])


def f(x, d=2):
    return f"{x:,.{d}f}"


def cards(P, r):
    """Result cards as (title, [(label, value), ...])."""
    a, b = calc(P, 1), calc(P, 4)
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
        ("Take-off", [("Take-off speed (1.2·Vstall)", f"{f(r['Vx'])} m/s"), ("Ground roll", f"{f(r['Sg'])} m"),
                      ("Airborne distance", f"{f(r['Sa'])} m"), (f"Total over {P['hobs']:g} m obstacle", f"{f(r['Sto'])} m")]),
        ("Effect of altitude (1 km vs 4 km)", [("Min. thrust required", f"{f(a['TRmin'], 0)} vs {f(b['TRmin'], 0)} N"),
                                               ("Thrust available", f"{f(a['TA'], 0)} vs {f(b['TA'], 0)} N"),
                                               ("Max speed", f"{f(a['Vmax'], 1)} vs {f(b['Vmax'], 1)} m/s"),
                                               ("Max ROC", f"{f(a['max_roc'], 1)} vs {f(b['max_roc'], 1)} m/s")]),
    ]


# ---------- plots (matplotlib Figure -> base64 PNG) ----------
def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    return base64.b64encode(buf.getvalue()).decode()


def _fig(title, xl, yl):
    fig = Figure(figsize=(6, 4))
    ax = fig.subplots()
    ax.set(title=title, xlabel=xl, ylabel=yl)
    ax.grid(alpha=0.4)
    return fig, ax


def plots(P, r):
    h, out = r["h"], []
    V = r["V"]

    fig, ax = _fig(f"Thrust vs Velocity (h = {h} km)", "Velocity (m/s)", "Thrust (N)")
    ax.plot(V, r["TR"], "b", label="Thrust required")
    ax.plot(V, np.full_like(V, r["TA"], dtype=float), "r", label="Thrust available")
    ax.plot(r["Vmax"], r["TA"], "ko"); ax.legend()
    out.append(("Thrust vs velocity", _png(fig)))

    fig, ax = _fig(f"Power vs Velocity (h = {h} km)", "Velocity (m/s)", "Power (W)")
    ax.plot(V, r["PR"], label="Power required"); ax.plot(V, r["PA"], label="Power available"); ax.legend()
    out.append(("Power vs velocity", _png(fig)))

    fig, ax = _fig(f"Rate of Climb vs Velocity (h = {h} km)", "Velocity (m/s)", "Rate of climb (m/s)")
    ax.plot(V, r["ROC"], label="ROC"); ax.plot(r["V_roc"], r["max_roc"], "ro", label="Max ROC"); ax.legend()
    out.append(("Rate of climb", _png(fig)))

    fig, ax = _fig(f"V-n Diagram (h = {h} km)", "Velocity (m/s)", "Load factor n")
    rho, S, W = r["rho"], P["S"], P["W"]
    ax.plot(r["vp"], 0.5 * rho * r["vp"] ** 2 * S * P["CLmax"] / W, "b", label="Aerodynamic limit (PU)")
    ax.plot(r["vn"], -0.5 * rho * r["vn"] ** 2 * S * P["CLpd"] / W, "r", label="Aerodynamic limit (PD)")
    ax.plot([r["Vap"], r["Vmax"]], [P["nLu"]] * 2, color="orange", label="Structural limit (PU)")
    ax.plot([r["Van"], r["Vmax"]], [P["nLd"]] * 2, color="purple", label="Structural limit (PD)")
    ax.plot([r["Vmax"]] * 2, [P["nLd"], P["nLu"]], "g", label="Propulsive limit")
    ax.legend(fontsize=7)
    out.append(("V-n diagram", _png(fig)))

    fig, ax = _fig(f"Take-off Trajectory (h = {h} km)", "Distance (m)", "Height (m)")
    th = np.linspace(0, r["th_max"], 200)
    ax.plot([0, r["Sg"]], [0, 0], label="Ground roll")
    ax.plot(r["Sg"] + P["R"] * np.sin(th), P["R"] * (1 - np.cos(th)), label="Airborne trajectory")
    ax.axhline(P["hobs"], color="gray", ls="--", label=f"{P['hobs']:g} m obstacle")
    ax.scatter(r["Sto"], P["hobs"], color="red", zorder=5, label="Obstacle cleared"); ax.legend()
    out.append(("Take-off trajectory", _png(fig)))

    fig, ax = _fig(f"Hodograph (h = {h} km)", "Horizontal speed Vh (m/s)", "Vertical speed Vv (m/s)")
    vh, vv = np.append(r["Vh"], r["Vmax"]), np.append(r["Vv"], 0.0)
    ax.plot(vh, vv, label="Hodograph")
    ax.scatter(r["V_roc"], r["max_roc"], color="blue", zorder=5); ax.annotate("Max RoC", (r["V_roc"], r["max_roc"]), xytext=(10, 10), textcoords="offset points")
    ax.scatter(r["Vmax"], 0, color="blue", zorder=5); ax.annotate("Vmax", (r["Vmax"], 0), xytext=(-40, 10), textcoords="offset points")
    ax.legend()
    out.append(("Hodograph", _png(fig)))
    return out


def altitude_plot(P):
    fig, ax = _fig("Effect of Altitude on Thrust Required", "Velocity (m/s)", "Thrust required (N)")
    for h, c in ((1, "tab:blue"), (4, "tab:orange")):
        r = calc(P, h)
        ax.plot(r["V"], r["TR"], color=c, label=f"h = {h} km (ρ = {r['rho']:g})")
    ax.legend()
    return ("Effect of altitude on thrust required", _png(fig))
