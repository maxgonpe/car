import os
import xml.etree.ElementTree as ET
import cairosvg
from PIL import Image

def extract_regions_from_svg(svg_path, output_dir="recortes"):
    os.makedirs(output_dir, exist_ok=True)

    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Encuentra la capa base (suponiendo que es un <image>)
    base_image_element = root.find(".//{http://www.w3.org/2000/svg}image")
    if base_image_element is None:
        raise ValueError("No se encontró capa base <image> en el SVG")

    # Ruta de la imagen base
    base_href = base_image_element.attrib.get("{http://www.w3.org/1999/xlink}href")
    if not base_href:
        raise ValueError("El <image> no tiene href con la imagen de base")

    # Abrir la imagen base con Pillow
    base_image = Image.open(base_href)

    # Buscar shapes que usas como marcadores
    ns = {"svg": "http://www.w3.org/2000/svg"}
    for shape in root.findall(".//svg:rect", ns):
        id_ = shape.attrib.get("id")
        if not id_:
            continue

        x = float(shape.attrib.get("x", 0))
        y = float(shape.attrib.get("y", 0))
        w = float(shape.attrib.get("width", 0))
        h = float(shape.attrib.get("height", 0))

        # Recortar región de la imagen base
        cropped = base_image.crop((x, y, x+w, y+h))

        out_path = os.path.join(output_dir, f"{id_}.png")
        cropped.save(out_path)
        print(f"✅ Guardado {out_path}")

    print("🎉 Listo, regiones recortadas de la capa base.")

if __name__ == "__main__":
    extract_regions_from_svg("entrada.svg")
