"""
Builds the PPLLM Assistant stress corpus: PDFs shaped like the files students and
faculty actually upload (journal articles, news articles saved from a browser,
scans, slides exported to PDF), each with questions whose answers we know.

Run:  python3 tests/stress/make_corpus.py
Output: tests/stress/corpus/*.pdf and tests/stress/corpus/questions.json
"""
import json
import os
import random

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                SimpleDocTemplate, Spacer, Table, PageBreak)
from reportlab.pdfgen import canvas

OUT = os.path.join(os.path.dirname(__file__), "corpus")
os.makedirs(OUT, exist_ok=True)
pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuB", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"))

ss = getSampleStyleSheet()
body = ParagraphStyle("b", parent=ss["BodyText"], fontName="DejaVu", fontSize=10, leading=13)
h = ParagraphStyle("h", parent=ss["Heading2"], fontName="DejaVuB")
title = ParagraphStyle("t", parent=ss["Title"], fontName="DejaVuB")
random.seed(7)

QUESTIONS = {}

FILLER = [
    "Prior work has examined related questions in adjacent settings, though with smaller samples and shorter time horizons.",
    "We note that several robustness checks, reported in the appendix, leave the main estimates essentially unchanged.",
    "Interpretation of these patterns requires care, because institutional context differs considerably across sites.",
    "The literature offers competing explanations, and the evidence presented here speaks to only some of them.",
    "Data were cleaned following standard procedures, and observations with missing identifiers were dropped.",
    "These considerations motivate the empirical approach described in the following sections of the paper.",
]


def filler(n):
    return " ".join(random.choice(FILLER) for _ in range(n))


def article_story(fi_ligatures=False):
    """A business-school style empirical article. Facts are planted so we can check answers."""
    fi = (lambda s: s.replace("fi", "ﬁ").replace("fl", "ﬂ")) if fi_ligatures else (lambda s: s)
    parts = [
        ("title", "Generative AI Assistance and Novice Analyst Productivity"),
        ("p", "Ravi Natarajan and Ellen Brooks, Kelley School of Business"),
        ("h", "Abstract"),
        ("p", fi("We study how access to a generative AI assistant affects the productivity of novice financial analysts. "
                 "Using a field experiment with 412 analysts at a regional bank, we find that assistance raised report completion "
                 "by 23 percent and reduced reconciliation errors, with the largest benefits for the least experienced workers.")),
        ("h", "1. Introduction"),
        ("p", fi(filler(4) + " Our central question is whether AI assistance narrows or widens the gap between novice and expert analysts. "
                 "We find the gap narrows: the bottom quartile of analysts gained the most from the assistant.")),
        ("p", fi(filler(5))),
        ("h", "2. Related Work"),
        ("p", fi(filler(6) + " Brynjolfsson and coauthors document similar effects among customer support agents.")),
        ("h", "3. Methods"),
        ("p", fi("We randomly assigned 206 analysts to receive the assistant and 206 to a control group for eight weeks. "
                 "The primary outcome was the number of completed variance reports per week; the secondary outcome was the "
                 "reconciliation error rate measured by an independent audit team. We estimate effects with ordinary least squares "
                 "and branch fixed effects, clustering standard errors at the branch level. " + filler(3))),
        ("p", fi(filler(5))),
        ("h", "4. Results"),
        ("p", fi("Treated analysts completed 23 percent more variance reports per week than controls. The reconciliation error rate fell "
                 "from 6.1 percent to 4.4 percent. Effects were concentrated among analysts with less than two years of tenure. " + filler(3))),
        ("p", fi(filler(6))),
        ("h", "5. Discussion"),
        ("p", fi("The results suggest that AI assistance functions as a skill equalizer within this setting. Managers should pair "
                 "assistant rollouts with verification training, because a minority of assisted reports contained confident but "
                 "unsupported figures. " + filler(3))),
        ("h", "6. Limitations"),
        ("p", fi("The study covers a single bank over eight weeks, so long-run learning effects and general equilibrium effects on "
                 "hiring are outside its scope. " + filler(2))),
        ("h", "7. Conclusion"),
        ("p", fi("Generative AI assistance raised novice analyst productivity substantially, and the gains were largest for the least "
                 "experienced workers. " + filler(2))),
        ("h", "References"),
    ]
    for i in range(18):
        parts.append(("p", f"[{i+1}] Author{i}, A., and Coauthor, B. (20{10+i%15}). Artificial intelligence, productivity, and labor "
                           f"markets: evidence from field experiments. Journal of Applied Methods {i+3}(2), {100+i}-{120+i}. doi:10.1000/jam.{i}"))
    return parts


ARTICLE_QS = [
    {"q": "What is this paper about?", "expect": ["generative ai", "analyst"]},
    {"q": "Summarize the article", "expect": ["productiv"]},
    {"q": "How many analysts were in the experiment?", "expect": ["412"]},
    {"q": "What methods did the authors use?", "expect": ["randomly assigned", "least squares"]},
    {"q": "What are the main findings?", "expect": ["23 percent"]},
    {"q": "What were the results?", "expect": ["23 percent"]},
    {"q": "How much did the error rate fall?", "expect": ["4.4"]},
    {"q": "What are the limitations of the study?", "expect": ["single bank"]},
    {"q": "What should managers do?", "expect": ["verification training"]},
    {"q": "Who benefits most from AI?", "expect": ["least experienced", "bottom quartile", "less than two years"]},
    {"q": "What does the conclusion say?", "expect": ["raised novice"]},
    {"q": "Did workers become more efficient?", "expect": ["23 percent", "productiv"]},
    {"q": "What's the takeaway?", "expect": ["productiv", "ai assistance"]},
    {"q": "Who wrote it?", "expect": ["natarajan"]},
]


def build_flow(parts):
    flow = []
    for kind, text in parts:
        style = {"title": title, "h": h, "p": body}[kind]
        flow.append(Paragraph(text, style))
        if kind != "p":
            flow.append(Spacer(1, 4))
    return flow


def single_column(name, parts):
    SimpleDocTemplate(os.path.join(OUT, name), pagesize=letter).build(build_flow(parts))


def two_column(name, parts):
    doc = BaseDocTemplate(os.path.join(OUT, name), pagesize=letter)
    w, hgt = letter
    gap = 0.3 * inch
    colw = (w - 2 * inch - gap) / 2
    frames = [Frame(inch, inch, colw, hgt - 2 * inch, id="c1"),
              Frame(inch + colw + gap, inch, colw, hgt - 2 * inch, id="c2")]
    def header(c, d):
        c.setFont("DejaVu", 7)
        c.drawString(inch, hgt - 0.6 * inch, "Journal of Applied Methods · Vol. 12 · Preprint · Do not cite without permission")
        c.drawRightString(w - inch, 0.6 * inch, f"Page {d.page}")
    doc.addPageTemplates([PageTemplate(frames=frames, onPage=header)])
    doc.build(build_flow(parts))


def news_saved_from_browser(name):
    """A blog/news page printed to PDF: nav menus, cookie banner, share buttons, ads, comments.
    Mirrors the 'shipwithjev.pdf' file from Nick's screenshot."""
    c = canvas.Canvas(os.path.join(OUT, name), pagesize=letter)
    w, hgt = letter
    def chrome(page):
        c.setFont("Helvetica", 7)
        c.drawString(30, hgt - 20, f"10/12/26, 3:14 PM    Jev plays Doom | Ship with Jev    https://shipwithjev.dev/blog/jev-plays-doom    {page}/3")
        c.drawString(30, hgt - 40, "Home   Docs   Blog   Pricing   Changelog   Sign in   Get started  ☰")
        c.drawString(30, 20, "© 2026 Ship with Jev · Privacy · Terms · Cookie settings · Status")
    paras = [
        "Jev plays Doom",
        "We accept cookies to improve your experience. Accept all  Reject  Manage preferences",
        "Share on X   Share on LinkedIn   Copy link   ♥ 214",
        "We wired Jev into a Doom engine to see how fast a System One model can make game decisions. Every game tick, the agent sends the "
        "current frame summary to Jev as state and asks three typed questions: which weapon to use, whether to strafe left or right, "
        "and a threat score from one to five.",
        "Jev answers all three questions in parallel in about 90 milliseconds, which is fast enough to act on every third frame. "
        "A language model planner that wrote free text took more than two seconds per decision, so the marine kept walking into walls.",
        "ADVERTISEMENT   Try Jev free for 14 days →",
        "The trick is that Jev never writes text. It returns a choice with a probability for each option, so the game loop can ignore "
        "low-confidence answers. We set the threshold at 0.6 confidence; below that the agent keeps its previous action.",
        "Results: the Jev agent cleared the first level, E1M1, in 3 minutes 41 seconds and survived 78 percent of encounters. "
        "The text-based planner never finished the level.",
        "Related posts   Jev vs Laya   Building a guardrail with Noul   Typed decisions for email triage",
        "Comments (12)   Login to comment   Sort by: Newest",
        "doomfan88 · 2h   lol the marine strafing is perfect",
        "Subscribe to our newsletter   Email address   Subscribe",
    ]
    y = hgt - 70
    page = 1
    chrome(page)
    for p in paras:
        size = 20 if p == "Jev plays Doom" else 10
        c.setFont("Helvetica-Bold" if size == 20 else "Helvetica", size)
        words, line = p.split(), ""
        for wd in words:
            if c.stringWidth(line + " " + wd, "Helvetica", size) > w - 60:
                c.drawString(30, y, line.strip()); y -= size + 4; line = ""
            line += " " + wd
        c.drawString(30, y, line.strip()); y -= size + 14
        if y < 120:
            c.showPage(); page += 1; chrome(page); y = hgt - 70
    c.save()


NEWS_QS = [
    {"q": "How does Jev play Doom?", "expect": ["typed questions", "parallel", "weapon"]},
    {"q": "How fast is Jev?", "expect": ["90 milliseconds"]},
    {"q": "What was the confidence threshold?", "expect": ["0.6"]},
    {"q": "Did the agent finish the level?", "expect": ["e1m1", "3 minutes"]},
    {"q": "Summarize this", "expect": ["doom"]},
    {"q": "Why is a language model worse for this?", "expect": ["two seconds", "free text"]},
]


def scanned(name):
    """Image-only PDF (a scan / photo of a page). No text layer at all."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("L", (1275, 1650), 255)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 28)
    text = ("Memo: Campus AI Policy\n\nStudents may use AI assistants for brainstorming\n"
            "but must disclose use in a footnote.\nViolations are referred to the honor council.")
    d.multiline_text((100, 120), text, font=f, fill=0, spacing=12)
    img.save(os.path.join(OUT, name), "PDF", resolution=150)


def tiny(name):
    c = canvas.Canvas(os.path.join(OUT, name), pagesize=letter)
    c.setFont("Helvetica", 11)
    c.drawString(72, 700, "Reminder: the AI literacy workshop moves to Hodge Hall room 2075 on Thursday at 3 pm.")
    c.save()


def long_report(name):
    parts = [("title", "Annual Technology Survey of Midwestern Small Businesses")]
    topics = ["cloud accounting", "cybersecurity training", "point of sale systems", "customer relationship software",
              "website analytics", "payroll automation", "inventory forecasting", "e-commerce platforms"]
    for i in range(1, 41):
        t = topics[i % len(topics)]
        parts.append(("h", f"Section {i}: {t.title()}"))
        parts.append(("p", f"Adoption of {t} among respondents reached {20 + i} percent in this wave. " + filler(8)))
        if i == 33:
            parts.append(("p", "Notably, ransomware incidents were reported by 17 businesses, and the median recovery cost was $48,000."))
    single_column(name, parts)


LONG_QS = [
    {"q": "How many businesses reported ransomware?", "expect": ["17 businesses"]},
    {"q": "What was the median recovery cost?", "expect": ["48,000"]},
    {"q": "What is this report about?", "expect": ["survey", "adoption"]},
]


def spanish(name):
    parts = [("title", "La inteligencia artificial en las universidades"),
             ("p", "Este artículo analiza cómo los estudiantes universitarios usan herramientas de inteligencia artificial. "
                   "Encuestamos a 1.250 estudiantes en tres universidades y encontramos que el 64 por ciento usa asistentes "
                   "de IA cada semana, principalmente para resumir lecturas.")]
    single_column(name, parts)


SPANISH_QS = [
    {"q": "How many students were surveyed?", "expect": ["1.250"]},
    {"q": "¿Cuántos estudiantes fueron encuestados?", "expect": ["1.250"]},
]


def table_heavy(name):
    flow = [Paragraph("Quarterly Results Summary", title),
            Paragraph("Table 1 reports revenue by segment for fiscal 2026.", body)]
    data = [["Segment", "Q1", "Q2", "Q3", "Q4"],
            ["Consulting", "$1.2M", "$1.4M", "$1.1M", "$1.9M"],
            ["Software", "$3.4M", "$3.9M", "$4.2M", "$4.8M"],
            ["Training", "$0.3M", "$0.2M", "$0.4M", "$0.5M"]]
    flow.append(Table(data))
    SimpleDocTemplate(os.path.join(OUT, name), pagesize=letter).build(flow)


TABLE_QS = [
    {"q": "What was software revenue in Q4?", "expect": ["4.8m"]},
    {"q": "Which segment earned the most?", "expect": ["software"]},
]


def encrypted(name):
    import pikepdf
    src = os.path.join(OUT, "tiny_memo.pdf")
    with pikepdf.open(src) as pdf:
        pdf.save(os.path.join(OUT, name), encryption=pikepdf.Encryption(owner="owner", user="secret"))


def slides(name):
    c = canvas.Canvas(os.path.join(OUT, name), pagesize=(792, 612))
    decks = [("AI Literacy 101", ["What is a token?", "Why models hallucinate", "Checking sources"]),
             ("What is a token?", ["Models read text in pieces called tokens", "About 4 characters each in English"]),
             ("Why models hallucinate", ["They predict likely words", "Not looked up facts"]),
             ("Checking sources", ["Ask for the passage", "Verify numbers yourself"])]
    for t, bullets in decks:
        c.setFont("Helvetica-Bold", 30); c.drawString(60, 520, t)
        c.setFont("Helvetica", 20)
        for i, b in enumerate(bullets):
            c.drawString(80, 450 - i * 40, "• " + b)
        c.showPage()
    c.save()


SLIDES_QS = [
    {"q": "Why do models hallucinate?", "expect": ["predict likely words"]},
    {"q": "How long is a token?", "expect": ["4 characters"]},
]

single_column("article_single_column.pdf", article_story())
QUESTIONS["article_single_column.pdf"] = ARTICLE_QS
two_column("article_two_column.pdf", article_story())
QUESTIONS["article_two_column.pdf"] = ARTICLE_QS
single_column("article_ligatures.pdf", article_story(fi_ligatures=True))
QUESTIONS["article_ligatures.pdf"] = [{"q": "What were the findings?", "expect": ["23 percent"]},
                                      {"q": "What is the reconciliation error rate?", "expect": ["4.4"]},
                                      {"q": "What are the main findings?", "expect": ["23 percent"]}]
news_saved_from_browser("news_saved_from_browser.pdf"); QUESTIONS["news_saved_from_browser.pdf"] = NEWS_QS
scanned("scanned_memo.pdf"); QUESTIONS["scanned_memo.pdf"] = [{"q": "Can students use AI?", "expect": ["brainstorming"]}]
tiny("tiny_memo.pdf"); QUESTIONS["tiny_memo.pdf"] = [{"q": "Where is the workshop?", "expect": ["hodge hall"]},
                                                    {"q": "When is it?", "expect": ["thursday"]}]
long_report("long_report_40_sections.pdf"); QUESTIONS["long_report_40_sections.pdf"] = LONG_QS
spanish("spanish_article.pdf"); QUESTIONS["spanish_article.pdf"] = SPANISH_QS
table_heavy("table_heavy.pdf"); QUESTIONS["table_heavy.pdf"] = TABLE_QS
encrypted("password_protected.pdf"); QUESTIONS["password_protected.pdf"] = [{"q": "Where is the workshop?", "expect": ["hodge hall"]}]
slides("slides_exported.pdf"); QUESTIONS["slides_exported.pdf"] = SLIDES_QS

with open(os.path.join(OUT, "questions.json"), "w") as f:
    json.dump(QUESTIONS, f, indent=1)
print("wrote", len(QUESTIONS), "PDFs to", OUT)
