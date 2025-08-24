import os
import base64
import xml.etree.ElementTree as ET
from PIL import Image
from io import BytesIO

def extract_regions_from_svg(svg_path, output_dir="recortes"):
    os.makedirs(output_dir, exist_ok=True)

    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Encuentra la capa base (suponiendo que es un <image>)
    ns = {
        "svg": "http://www.w3.org/2000/svg",
        "xlink": "http://www.w3.org/1999/xlink"
    }
    base_image_element = root.find(".//svg:image", ns)
    if base_image_element is None:
        raise ValueError("❌ No se encontró capa base <image> en el SVG")

    base_href = base_image_element.attrib.get("{http://www.w3.org/1999/xlink}href")
    if not base_href:
        raise ValueError("❌ El <image> no tiene href")

    # --- Caso 1: imagen embebida en base64 ---
    if base_href.startswith("data:image/"):
        header, encoded = base_href.split(",", 1)
        img_data = base64.b64decode(encoded)
        base_image = Image.open(BytesIO(img_data))
        print("📦 Imagen base cargada desde datos embebidos (base64).")
    else:
        # --- Caso 2: referencia a archivo ---
        base_image = Image.open(base_href)
        print(f"📂 Imagen base cargada desde archivo: {base_href}")

    # Buscar rectángulos marcadores
    for shape in root.findall(".//svg:rect", ns):
        id_ = shape.attrib.get("id")
        if not id_:
            continue

        x = float(shape.attrib.get("x", 0))
        y = float(shape.attrib.get("y", 0))
        w = float(shape.attrib.get("width", 0))
        h = float(shape.attrib.get("height", 0))

        # Recortar región de la imagen base
        cropped = base_image.crop((x, y, x + w, y + h))

        out_path = os.path.join(output_dir, f"{id_}.png")
        cropped.save(out_path)
        print(f"✅ Guardado {out_path}")

    print("🎉 Listo, regiones recortadas de la capa base.")

if __name__ == "__main__":
    extract_regions_from_svg("entrada.svg")
