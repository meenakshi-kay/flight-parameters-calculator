from flask import Flask, redirect, render_template, request, session, url_for
import performance as perf
from performance import altitudes, ALT_KEYS


app = Flask(__name__)
app.secret_key = "change-me"  # needed for session storage of inputs


def params():
    P = dict(perf.DEFAULTS)
    P.update(session.get("inputs", {}))
    for key in ALT_KEYS:
        P[key] = min(5, max(0, int(round(P[key]))))
    return P


def pick_alt(P):
    alts = altitudes(P)
    try:
        h = int(request.args.get("alt", alts[0]))
    except ValueError:
        h = alts[0]
    return h if h in alts else alts[0]


@app.context_processor
def inject():
    return dict(page=request.endpoint)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/inputs", methods=["GET", "POST"])
def inputs():
    if request.method == "POST":
        if request.form.get("action") == "reset":
            session.pop("inputs", None)
            return redirect(url_for("inputs", msg="reset"))
        vals = {}
        for key, _, default in perf.FIELDS:
            try:
                vals[key] = float(request.form[key])
            except (KeyError, ValueError):
                vals[key] = default
        session["inputs"] = vals
        return redirect(url_for("calculations"))
    return render_template("inputs.html", groups=perf.GROUPS, P=params(), msg=request.args.get("msg"))


@app.route("/calculations")
def calculations():
    P = params(); h = pick_alt(P)
    return render_template("calculations.html", cards=perf.cards(P, perf.calc(P, h)), alt=h, alts=altitudes(P))


@app.route("/plots")
def plots():
    P = params(); h = pick_alt(P)
    imgs = perf.plots(P, perf.calc(P, h)) + [perf.altitude_plot(P)]
    return render_template("plots.html", imgs=imgs, alt=h, alts=altitudes(P))


@app.route("/report")
def report():
    P = params()
    sections = []
    for h in sorted({P["h1"], P["h2"]}):
        r = perf.calc(P, h)
        sections.append(dict(h=h, cards=perf.cards(P, r)[:5], imgs=perf.plots(P, r, "light")))
    return render_template("report.html", P=P, sections=sections, alt_img=perf.altitude_plot(P, "light"))


if __name__ == "__main__":
    app.run(debug=True)
