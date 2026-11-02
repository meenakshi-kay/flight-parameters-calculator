from flask import Flask, redirect, render_template, request, session, url_for
import performance as perf

app = Flask(__name__)
app.secret_key = "change-me"  # needed for session storage of inputs


def params():
    P = dict(perf.DEFAULTS)
    P.update(session.get("inputs", {}))
    return P


def alt():
    return 4 if request.args.get("alt") == "4" else 1


@app.context_processor
def inject():
    return dict(page=request.endpoint)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/inputs", methods=["GET", "POST"])
def inputs():
    if request.method == "POST":
        if "reset" in request.form:
            session.pop("inputs", None)
        else:
            vals = {}
            for key, _, default in perf.FIELDS:
                try:
                    vals[key] = float(request.form[key])
                except (KeyError, ValueError):
                    vals[key] = default
            session["inputs"] = vals
        return redirect(url_for("inputs", saved=1))
    return render_template("inputs.html", fields=perf.FIELDS, P=params(), saved=request.args.get("saved"))


@app.route("/calculations")
def calculations():
    P, h = params(), alt()
    return render_template("calculations.html", cards=perf.cards(P, perf.calc(P, h)), alt=h)


@app.route("/plots")
def plots():
    P, h = params(), alt()
    imgs = perf.plots(P, perf.calc(P, h)) + [perf.altitude_plot(P)]
    return render_template("plots.html", imgs=imgs, alt=h)


@app.route("/report")
def report():
    P = params()
    sections = []
    for h in (1, 4):
        r = perf.calc(P, h)
        sections.append(dict(h=h, cards=perf.cards(P, r)[:5], imgs=perf.plots(P, r)))
    return render_template("report.html", P=P, sections=sections, alt_img=perf.altitude_plot(P))


if __name__ == "__main__":
    app.run(debug=True)
