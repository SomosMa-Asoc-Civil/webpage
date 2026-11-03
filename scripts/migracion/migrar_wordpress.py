#!/usr/bin/env python3
"""
Migración única del export de WordPress (Kubio) de SomosMa al sitio en Astro.

Uso:
    python3 scripts/migracion/migrar_wordpress.py ruta/al/export.xml

Genera:
    src/content/noticias/*.md   -> noticias con frontmatter (editables desde Pages CMS)
    src/data/*.json             -> textos de las páginas (editables desde Pages CMS)
    scripts/migracion/imagenes.txt -> URLs de las imágenes a descargar

Requiere: beautifulsoup4, lxml, markdownify (pip install beautifulsoup4 lxml markdownify)
Se corrió una sola vez; queda en el repo como registro de cómo se hizo la migración.
"""
import html
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from markdownify import markdownify as md

ROOT = Path(__file__).resolve().parents[2]
NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
    "dc": "http://purl.org/dc/elements/1.1/",
}
UPLOADS_RE = re.compile(r"https?://(?:www\.)?somosma\.com\.ar/wp-content/uploads/([^\s\"'<>)?#]+)")
SITE_RE = re.compile(r"https?://(?:www\.)?somosma\.com\.ar")
AUTORES = {
    "l0060747": "SomosMa",
    "SomosMaAdmin": "SomosMa",
    "CeciSomosMa": "Ceci Bertolino",
    "DianaSomosMa": "Diana Deharbe",
    "Poli_studio": "SomosMa",
}

imagenes: set[str] = set()


def local_upload(url: str) -> str:
    """https://somosma.com.ar/wp-content/uploads/2025/04/x.jpg -> /uploads/2025/04/x.jpg"""
    if not url:
        return ""
    m = UPLOADS_RE.search(url)
    if not m:
        return url
    imagenes.add("https://somosma.com.ar/wp-content/uploads/" + m.group(1))
    return "/uploads/" + m.group(1)


def local_link(url: str) -> str:
    url = (url or "").strip()
    if UPLOADS_RE.search(url):
        return local_upload(url)
    url = SITE_RE.sub("", url)
    if url == "":
        return "/"
    return url


def youtube_id(url: str) -> str:
    """https://www.youtube.com/watch?v=ABC&t=2s -> ABC"""
    m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else ""


def fix_instagram(url: str) -> str:
    """Los links de login de Instagram (accounts/login/?next=/usuario/) -> perfil directo."""
    url = url.strip()
    if "instagram.com/accounts/login" in url:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        nxt = q.get("next", [""])[0]
        handle = nxt.strip("/").split("/")[0]
        if handle:
            return f"https://www.instagram.com/{handle}/"
    return re.sub(r"(instagram\.com/[^/?]+/)profilecard/?\??.*$", r"\1", url)


# ---------- Parser de bloques Kubio/Gutenberg ----------
TOK = re.compile(r"<!-- (/?)wp:([a-z0-9/-]+)\s*(\{.*?\})?\s*(/?)-->", re.S)
TEXTY = {"kubio/heading", "kubio/text", "paragraph", "heading", "kubio/button", "kubio/link",
         "list-item", "kubio/iconlistitem"}


def clean(t: str) -> str:
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r"</p>\s*<p[^>]*>", "\n\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t ]+", " ", t)
    t = "\n".join(l.strip() for l in t.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def prose(t: str) -> str:
    """Une los saltos de línea manuales de Kubio dentro de cada párrafo."""
    paras = [re.sub(r"\s*\n\s*", " ", p).strip() for p in t.split("\n\n")]
    return "\n\n".join(p for p in paras if p)


def lines(t: str) -> list[str]:
    return [re.sub(r"^[-•]\s*", "", l).strip() for l in t.split("\n") if l.strip()]


def parse_blocks(s: str) -> list[dict]:
    out, stack, pos, section = [], [], 0, None
    for m in TOK.finditer(s):
        closing, name, attrs, selfc = m.groups()
        between = s[pos:m.start()]
        pos = m.end()
        if closing:
            if stack:
                n, a = stack.pop()
                if n in TEXTY:
                    t = clean(between)
                    if t:
                        out.append(dict(section=section, type=n.split("/")[-1], text=t))
            continue
        try:
            a = json.loads(attrs) if attrs else {}
        except Exception:
            a = {}
        if name == "kubio/section":
            section = (a.get("attrs") or {}).get("name") or a.get("anchor")
        if name in ("kubio/image", "image"):
            out.append(dict(section=section, type="img", text=a.get("url", "")))
        if name == "kubio/social-icon":
            out.append(dict(section=section, type="social", text=((a.get("link") or {}).get("value") or "").strip()))
        if name in ("kubio/button", "kubio/link"):
            out.append(dict(section=section, type="href", text=(a.get("link") or {}).get("value", "")))
        if name == "embed" and "youtube" in (a.get("url") or ""):
            out.append(dict(section=section, type="video", text=a["url"]))
        if not selfc:
            stack.append((name, a))
    return out


# ---------- Export ----------
def load(path: str):
    ch = ET.parse(path).getroot().find("channel")
    items = ch.findall("item")
    get = lambda it, k: it.findtext(k, namespaces=NS) or ""
    by_type: dict[str, list] = {}
    for it in items:
        by_type.setdefault(get(it, "wp:post_type"), []).append(it)
    attachments = {get(a, "wp:post_id"): get(a, "wp:attachment_url") for a in by_type.get("attachment", [])}
    for url in attachments.values():
        local_upload(url)
    return by_type, attachments, get


def page_blocks(by_type, get, post_id):
    for it in by_type["page"]:
        if get(it, "wp:post_id") == post_id:
            return parse_blocks(get(it, "content:encoded"))
    raise SystemExit(f"No encontré la página {post_id}")


def find(nodes, type_, text_startswith=None, after=0):
    for i, n in enumerate(nodes[after:], start=after):
        if n["type"] == type_ and (text_startswith is None or n["text"].startswith(text_startswith)):
            return i, n["text"]
    raise SystemExit(f"No encontré {type_} {text_startswith!r}")


def write_json(name, data):
    p = ROOT / "src/data" / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("  ", p.relative_to(ROOT))


def migrar_paginas(by_type, get):
    # Inicio (página 24)
    n = page_blocks(by_type, get, "24")
    t = [x["text"] for x in n]
    write_json("inicio", {
        "hero": {
            "imagen": local_upload(t[0]),
            "antetitulo": t[1],
            "titulo": t[2],
            "texto": prose(t[3]),
            "botones": [
                {"texto": "Contactanos", "url": "/contacto/"},
                {"texto": "Sumate", "url": "/sumate/"},
            ],
        },
        "cifras": {
            "titulo": "Cifras que importan",
            "items": [
                {"dato": prose(t[9]), "texto": prose(t[10]), "fuente": prose(t[11]).strip("()")},
                {"dato": prose(t[12]), "texto": prose(t[13]), "fuente": prose(t[14]).strip("()")},
            ],
            "destacado": {
                "titulo": prose(t[15]),
                "subtitulo": prose(t[16]),
                "boton": {"texto": "Conocer más", "url": "/nosotras/"},
                "lugar": prose(t[19]),
                "dato": prose(t[20]),
                "texto": prose(t[21]),
                "fuente": prose(t[22]).strip("()"),
            },
        },
        "instagram": {
            "titulo": "Seguinos en Instagram",
            "texto": "Compartimos novedades, campañas y recursos todos los días.",
            "usuario": "monomarentalesargentina",
        },
        "alianzas": {
            "titulo": prose(t[23]),
            "texto": prose(t[24]),
            "boton": {"texto": "Escribinos y trabajemos en red", "url": "/contacto/"},
        },
    })

    # Nosotras (página 115)
    n = page_blocks(by_type, get, "115")
    i_hist, _ = find(n, "heading", "Nuestra historia")
    i_eq, _ = find(n, "heading", "El equipo")
    equipo, actual = [], None
    for x in n[i_eq + 2:]:
        if x["section"] != "Team":
            break
        if x["type"] == "img":
            actual = {"nombre": "", "cargo": "", "foto": local_upload(x["text"]), "bio": "", "video": "", "redes": []}
            equipo.append(actual)
        elif actual is None:
            continue
        elif x["type"] == "video":
            actual["video"] = youtube_id(x["text"])
        elif x["type"] == "heading":
            actual["nombre"] = prose(x["text"])
        elif x["type"] == "text":
            parts = x["text"].split("\n", 1)
            if not actual["cargo"]:
                actual["cargo"] = parts[0].strip()
                if len(parts) > 1:
                    actual["bio"] = prose(parts[1])
            else:
                actual["bio"] = (actual["bio"] + "\n\n" + prose(x["text"])).strip()
        elif x["type"] == "social" and x["text"]:
            url = fix_instagram(x["text"])
            red = "linkedin" if "linkedin" in url else "instagram"
            if not any(r["url"] == url for r in actual["redes"]):
                actual["redes"].append({"red": red, "url": url})
    write_json("nosotras", {
        "hero": {
            "titulo": prose(n[0]["text"].split("|")[0]),
            "antetitulo": prose(n[0]["text"].split("|")[-1]),
            "texto": prose(n[1]["text"]),
        },
        "ser_monomarental": {
            "titulo": prose(n[2]["text"]).rstrip("."),
            "parrafos": [prose(x["text"]) for x in n[3:i_hist] if x["type"] == "paragraph"],
        },
        "videos": [youtube_id(x["text"]) for x in n[:i_hist] if x["type"] == "video"],
        "historia": {"titulo": prose(n[i_hist]["text"]), "texto": prose(n[i_hist + 1]["text"])},
        "equipo": {"titulo": prose(n[i_eq]["text"]), "texto": prose(n[i_eq + 1]["text"]), "integrantes": equipo},
        "cierre": {"texto": "Sumate vos también", "url": "/sumate/"},
    })

    # Qué hacemos (página 27)
    n = page_blocks(by_type, get, "27")
    t = [x["text"] for x in n]
    intro = lines(t[1])
    areas = []
    for hi, ti in ((2, 3), (4, 5), (6, 7), (8, 9)):
        areas.append({"titulo": prose(t[hi]).capitalize(), "items": lines(t[ti])})
    write_json("que-hacemos", {
        "titulo": prose(t[0]),
        "intro": [l for l in intro if l.upper() != "NUESTRAS ÁREAS DE TRABAJO"],
        "areas_titulo": "Nuestras áreas de trabajo",
        "areas": areas,
        "logros": {"titulo": "Logros destacados", "items": lines(t[11])},
        "cta": {"titulo": "Sumate vos también", "texto": prose(t[14]), "boton": {"texto": "Quiero sumarme", "url": "/sumate/"}},
    })

    # Sumate (página 32)
    n = page_blocks(by_type, get, "32")
    t = [x["text"] for x in n]
    vol = lines(t[3])
    write_json("sumate", {
        "imagen": local_upload(t[0]),
        "titulo": prose(t[1]).capitalize(),
        "voluntariado": {"titulo": prose(t[2]).capitalize(), "texto": vol[0], "areas": vol[1:]},
        "formulario": {
            "titulo": "Quiero ser voluntaria",
            "texto": "Completá tus datos y nos pondremos en contacto.",
            "asunto_mail": "Nueva voluntaria desde la web",
        },
    })

    # Contacto (página 36)
    n = page_blocks(by_type, get, "36")
    t = [x["text"] for x in n]
    faq = [{"pregunta": prose(t[i]), "respuesta": prose(t[i + 1])} for i in (1, 3, 5, 7)]
    hab = t[11].split("\n", 1)
    write_json("contacto", {
        "faq": {"titulo": prose(t[0]), "preguntas": faq},
        "titulo": prose(t[10]).rstrip("."),
        "subtitulo": hab[0].strip(),
        "texto": prose(hab[1]) if len(hab) > 1 else "",
        "formulario": {"titulo": prose(t[16]), "asunto_mail": "Nuevo mensaje desde la web"},
    })


def migrar_noticias(by_type, attachments, get):
    out_dir = ROOT / "src/content/noticias"
    out_dir.mkdir(parents=True, exist_ok=True)
    for it in by_type.get("post", []):
        if get(it, "wp:status") != "publish":
            continue
        slug = urllib.parse.unquote(get(it, "wp:post_name"))
        meta = {m.findtext("wp:meta_key", namespaces=NS): m.findtext("wp:meta_value", namespaces=NS)
                for m in it.findall("wp:postmeta", NS)}
        cats = [html.unescape(c.text) for c in it.findall("category")
                if c.get("domain") == "category" and c.text != "Sin categoría"]
        tags = [html.unescape(c.text) for c in it.findall("category") if c.get("domain") == "post_tag"]
        body_html = get(it, "content:encoded")
        # Las imágenes de Kubio solo existen como comentario de bloque: las paso a <img>
        def kubio_img(m):
            try:
                url = json.loads(m.group(1)).get("url", "")
            except Exception:
                url = ""
            return f'<p><img src="{url}" alt=""></p>' if url else ""
        body_html = re.sub(r"<!-- wp:kubio/image (\{.*?\}) /-->", kubio_img, body_html, flags=re.S)
        # Epígrafes cargados como "verso"/"preformateado" -> párrafo en cursiva
        body_html = re.sub(r'<pre class="wp-block-(?:verse|preformatted)">(.*?)</pre>',
                           r"<p><em>\1</em></p>", body_html, flags=re.S)
        body_html = re.sub(r"<!--.*?-->", "", body_html, flags=re.S)
        body_html = re.sub(r"<p>\s*(&nbsp;)?\s*</p>", "", body_html)
        body_html = UPLOADS_RE.sub(lambda m: local_upload(m.group(0)), body_html)
        body_html = re.sub(r'href="https?://(?:www\.)?somosma\.com\.ar/?', 'href="/', body_html)
        body = md(body_html, heading_style="ATX", bullets="-", strip=["span", "div"])
        # Imagen reducida con link a la original -> directamente la original
        body = re.sub(r"\[!\[([^\]]*)\]\([^)]+\)\]\((/uploads/[^)]+)\)", r"![\1](\2)", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
        excerpt = html.unescape(get(it, "excerpt:encoded")).strip()
        if not excerpt:
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(body_html))).strip()
            excerpt = (text[:200].rsplit(" ", 1)[0] + "…") if len(text) > 200 else text
        fm = {
            "title": html.unescape(it.findtext("title") or "").strip(),
            "date": get(it, "wp:post_date")[:10],
            "author": AUTORES.get(get(it, "dc:creator"), "SomosMa"),
            "image": local_upload(attachments.get(meta.get("_thumbnail_id", ""), "")),
            "excerpt": excerpt,
            "categories": cats,
            "tags": tags,
            "draft": False,
        }
        lines_fm = ["---"]
        for k, v in fm.items():
            lines_fm.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        lines_fm.append("---")
        (out_dir / f"{slug}.md").write_text("\n".join(lines_fm) + "\n\n" + body, encoding="utf-8")
        print("  ", f"src/content/noticias/{slug}.md")


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    by_type, attachments, get = load(sys.argv[1])
    print("Páginas:")
    migrar_paginas(by_type, get)
    print("Noticias:")
    migrar_noticias(by_type, attachments, get)
    # Logo y favicon (no figuran como adjuntos en el export)
    imagenes.add("https://somosma.com.ar/wp-content/uploads/2025/03/cropped-cropped-cropped-Mesa-de-trabajo-1.png")
    imagenes.add("https://somosma.com.ar/wp-content/uploads/2025/03/cropped-cropped-cropped-Mesa-de-trabajo-1-270x270.png")
    lista = ROOT / "scripts/migracion/imagenes.txt"
    lista.write_text("\n".join(sorted(imagenes)) + "\n", encoding="utf-8")
    print(f"Imágenes a descargar: {len(imagenes)} -> {lista.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
