import os
import xml.etree.ElementTree as ET
from copy import deepcopy
from svgelements import SVG

def extract_groups_with_bbox(svg_file, output_dir="output_groups"):
    os.makedirs(output_dir, exist_ok=True)

    # Leer SVG con svgelements
    svg = SVG.parse(svg_file)

    # Parsear con ElementTree para duplicar nodos XML
    tree = ET.parse(svg_file)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}

    # Buscar todos los grupos con ID
    for group in root.findall(".//svg:g[@id]", ns):
        group_id = group.attrib["id"]

        # Buscar elementos en svgelements con ese id
        shape = next((s for s in svg.elements() if getattr(s, "id", None) == group_id), None)

        # Calcular bounding box de TODOS los hijos
        bbox = None
        for child in svg.elements():
            if getattr(child, "id", None) and child.id.startswith(group_id):
                try:
                    cbbox = child.bbox()
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
            print(f"⚠️  Grupo {group_id} no tiene bbox válido. Saltando...")
            continue

        xmin, ymin, xmax, ymax = bbox
        w, h = xmax - xmin, ymax - ymin

        if w <= 0 or h <= 0:
            print(f"⚠️  Grupo {group_id} con tamaño nulo ({w}x{h}). Saltando...")
            continue

        # Crear nuevo SVG recortado
        new_svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": str(w),
            "height": str(h),
            "viewBox": f"{xmin} {ymin} {w} {h}",
        })

        # Clonar el grupo completo
        new_svg.append(deepcopy(group))

        # Guardar
        out_path = os.path.join(output_dir, f"{group_id}.svg")
        ET.ElementTree(new_svg).write(out_path, encoding="utf-8", xml_declaration=True)
        print(f"✅ Exportado grupo: {out_path} (recortado a {w}x{h})")

# Ejemplo de uso
if __name__ == "__main__":
    extract_groups_with_bbox("entrada.svg")
