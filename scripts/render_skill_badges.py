from copy import deepcopy
from pathlib import Path
import re
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)


def element(name):
    return f"{{{SVG}}}{name}"


def render_badge(mark, index):
    entrance_delay = index * 34
    glow_delay = 1650 + index * 120
    badge = ET.Element(element("svg"), id="still", width="25", height="20", viewBox="0 0 25 20", role="img")
    badge.append(deepcopy(mark.find(element("title"))))

    ET.SubElement(badge, element("style")).text = f"""
    @media (prefers-reduced-motion: no-preference) {{
      :root:not(:target) .mark {{ animation: arrive 460ms cubic-bezier(.2,.75,.2,1) {entrance_delay}ms both; }}
      :root:not(:target) .glow {{ animation: pulse 7000ms ease-in-out {glow_delay}ms infinite; }}
    }}
    @keyframes arrive {{
      from {{ opacity: .26; transform: translateY(1.2px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes pulse {{
      0%, 30%, 100% {{ opacity: 0; }}
      13% {{ opacity: .62; }}
    }}
  """

    ET.SubElement(badge, element("path"), d="M0 0H25V20H0Z", fill="#252525")
    ET.SubElement(badge, element("rect"), {
        "class": "glow", "x": ".5", "y": ".5", "width": "24", "height": "19",
        "fill": "none", "stroke": "#dedede", "stroke-width": ".75", "opacity": "0",
    })
    group = ET.SubElement(badge, element("g"), {"class": "mark"})
    logo = ET.SubElement(
        group, element("svg"), x="5.5", y="3", width="14", height="14",
        viewBox=mark.attrib["viewBox"], fill="#f2f2f2",
    )
    logo.extend(deepcopy(mark.findall(element("path"))))

    ET.indent(badge, space="  ")
    return ET.tostring(badge, encoding="unicode") + "\n"


def main():
    assets = Path(__file__).resolve().parents[1] / "assets"
    marks = ET.parse(assets / "skill-marks.svg").getroot().findall(element("symbol"))
    names = [mark.attrib["id"] for mark in marks]
    if len(names) != len(set(names)) or any(not re.fullmatch(r"[a-z0-9-]+", name) for name in names):
        raise ValueError("Skill mark IDs must be unique lowercase filenames")

    output = assets / "skill-badges"
    output.mkdir(exist_ok=True)
    for index, mark in enumerate(marks):
        (output / f"{mark.attrib['id']}.svg").write_text(render_badge(mark, index), encoding="utf-8")

    print(f"Rendered {len(marks)} animated skill badges")


if __name__ == "__main__":
    main()
