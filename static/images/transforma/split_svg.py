import os
import xml.etree.ElementTree as ET
from copy import deepcopy
from svgelements import SVG, Path, Shape

def extract_objects_with_bbox(svg_file, output_dir="output_svgs"):
    os.makedirs(output_dir, exist_ok=True)

    # Leer SVG con svgelements
    svg = SVG.parse(svg_file)

    # Parsear con ElementTree para duplicar nodos XML
    tree = ET.parse(svg_file)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}

    for elem in root.findall(".//*[@id]", ns):
        elem_id = elem.attrib["id"]

        # Buscar shape equivalente en svgelements
        shape = next((s for s in svg.elements() if getattr(s, "id", None) == elem_id), None)
        if not shape:
            continue

        # Intentar calcular bounding box
        try:
            bbox = shape.bbox()
        except Exception:
            bbox = None

        if not bbox:
            print(f"⚠️  {elem_id} no tiene bbox (posible grupo/contenedor). Saltando...")
            continue

        xmin, ymin, xmax, ymax = bbox
        w, h = xmax - xmin, ymax - ymin

        if w <= 0 or h <= 0:
            print(f"⚠️  {elem_id} tiene tamaño nulo ({w}x{h}). Saltando...")
            continue

        # Crear nuevo SVG recortado
        new_svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": str(w),
            "height": str(h),
            "viewBox": f"{xmin} {ymin} {w} {h}",
        })

        # Clonar objeto (deepcopy porque si no lo sacamos del original)
        new_svg.append(deepcopy(elem))

        # Guardar
        out_path = os.path.join(output_dir, f"{elem_id}.svg")
        ET.ElementTree(new_svg).write(out_path, encoding="utf-8", xml_declaration=True)
        print(f"✅ Exportado: {out_path} (recortado a {w}x{h})")

# Ejemplo de uso
if __name__ == "__main__":
    extract_objects_with_bbox("entrada.svg")
