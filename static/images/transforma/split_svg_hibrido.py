import os
import xml.etree.ElementTree as ET
from copy import deepcopy
from svgelements import SVG

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# ---------- Opción 1: Objetos individuales ----------
def extract_objects(svg_file, output_dir="output_objects"):
    ensure_dir(output_dir)
    svg = SVG.parse(svg_file)
    tree = ET.parse(svg_file)
    root = tree.getroot()

    for element in svg.elements():
        el_id = getattr(element, "id", None)
        if not el_id:
            continue

        try:
            bbox = element.bbox()
        except Exception:
            bbox = None
        if not bbox:
            continue

        xmin, ymin, xmax, ymax = bbox
        w, h = xmax - xmin, ymax - ymin
        if w <= 0 or h <= 0:
            continue

        # Crear nuevo SVG
        new_svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": str(w),
            "height": str(h),
            "viewBox": f"{xmin} {ymin} {w} {h}",
        })

        node = root.find(f".//*[@id='{el_id}']")
        if node is not None:
            new_svg.append(deepcopy(node))
            out_path = os.path.join(output_dir, f"{el_id}.svg")
            ET.ElementTree(new_svg).write(out_path, encoding="utf-8", xml_declaration=True)
            print(f"✅ Objeto exportado: {out_path}")

# ---------- Opción 2: Grupos completos ----------
def extract_groups(svg_file, output_dir="output_groups"):
    ensure_dir(output_dir)
    svg = SVG.parse(svg_file)
    tree = ET.parse(svg_file)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}

    for group in root.findall(".//svg:g[@id]", ns):
        group_id = group.attrib["id"]

        # Bounding box combinado
        bbox = None
        for element in svg.elements():
            if getattr(element, "id", None) and element.id.startswith(group_id):
                try:
                    cbbox = element.bbox()
                    if cbbox:
                        if bbox is None:
                            bbox = cbbox
                        else:
                            xmin, ymin, xmax, ymax = bbox
                            cxmin, cymin, cxmax, cymax = cbbox
                            bbox = (min(xmin, cxmin), min(ymin, cymin),
                                    max(xmax, cxmax), max(ymax, cymax))
                except Exception:
                    continue

        if not bbox:
            continue

        xmin, ymin, xmax, ymax = bbox
        w, h = xmax - xmin, ymax - ymin
        if w <= 0 or h <= 0:
            continue

        # Nuevo SVG con el grupo entero
        new_svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": str(w),
            "height": str(h),
            "viewBox": f"{xmin} {ymin} {w} {h}",
        })
        new_svg.append(deepcopy(group))

        out_path = os.path.join(output_dir, f"{group_id}.svg")
        ET.ElementTree(new_svg).write(out_path, encoding="utf-8", xml_declaration=True)
        print(f"✅ Grupo exportado: {out_path}")

# ---------- Opción 3: Híbrido (objetos + grupos) ----------
def extract_all(svg_file, output_dir="output_all"):
    extract_objects(svg_file, os.path.join(output_dir, "objects"))
    extract_groups(svg_file, os.path.join(output_dir, "groups"))

# ---------- Ejemplo de uso ----------
if __name__ == "__main__":
    svg_file = "entrada.svg"

    print("\n--- Opción 1: Objetos ---")
    extract_objects(svg_file)

    print("\n--- Opción 2: Grupos ---")
    extract_groups(svg_file)

    print("\n--- Opción 3: Híbrido ---")
    extract_all(svg_file)
