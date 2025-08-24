import xml.etree.ElementTree as ET
import os

def extract_objects(svg_file, output_dir="output_svgs"):
    os.makedirs(output_dir, exist_ok=True)

    tree = ET.parse(svg_file)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}

    # tamaño del lienzo original
    width = root.attrib.get("width", "1000")
    height = root.attrib.get("height", "1000")

    # buscar objetos con id
    for elem in root.findall(".//*[@id]", ns):
        elem_id = elem.attrib["id"]

        # clonar solo el objeto
        new_svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": width,
            "height": height,
            "viewBox": f"0 0 {width} {height}"
        })
        new_svg.append(elem)

        # archivo de salida
        out_path = os.path.join(output_dir, f"{elem_id}.svg")
        ET.ElementTree(new_svg).write(out_path, encoding="utf-8", xml_declaration=True)

        print(f"✅ Exportado: {out_path}")

# ejemplo de uso
extract_objects("entrada.svg")
