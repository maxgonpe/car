// static/js/plano-interactivo.js
document.addEventListener("DOMContentLoaded", function () {
  const ignoreIdRegex = /^g\d+$/i;

  function highlight(el) {
    try {
      el.style.outline = "3px solid rgba(255,0,0,0.25)";
      el.style.outlineOffset = "2px";
    } catch (e) {}
  }

  function unhighlight(el) {
    try {
      el.style.outline = "none";
    } catch (e) {}
  }

  function attachListenersToSvg(svgRoot) {
    if (!svgRoot) return;

    const zonas = svgRoot.querySelectorAll("[id]");
    zonas.forEach(z => {
      if (!z.id || ignoreIdRegex.test(z.id)) return;

      z.removeEventListener("click", handleClickOnce);
      z.addEventListener("click", handleClickOnce, { passive: false });

      z.addEventListener("mouseenter", function () {
        z.style.cursor = "pointer";
        z.style.stroke = "red";
        z.style.strokeWidth = "2";
      });

      z.addEventListener("mouseleave", function () {
        z.style.stroke = "none";
      });
    });
  }

  function handleClickOnce(e) {
    e.preventDefault();
    e.stopPropagation();

    const elems = document.elementsFromPoint(e.clientX, e.clientY);
    let candidate = null;

    for (const el of elems) {
      if (el.id && !ignoreIdRegex.test(el.id)) {
        candidate = el;
        break;
      }
    }

    if (!candidate) {
      console.debug("No se encontró elemento con id válido en el punto.");
      return;
    }

    const idComponente = candidate.id;
    highlight(candidate);
    setTimeout(() => unhighlight(candidate), 900);

    const fetchUrl = new URL(`/car/componentes-lookup/`, window.location.origin);
    fetchUrl.searchParams.set("part", idComponente);

    fetch(fetchUrl.toString(), { credentials: "same-origin" })
      .then(res => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(data => {
        if (data.found) {
          if (data.children && data.children.length > 0) {
            alert(`✅ Componente: ${data.parent.nombre}\nHijos: ${data.children.map(c => c.nombre).join(", ")}`);
          } else {
            alert(`✅ Componente: ${data.parent.nombre}\n(No tiene hijos)`);
          }

          if (data.parent.imagen_url) {
            const imageUrl = new URL(data.parent.imagen_url, window.location.origin).toString();
            const container = document.getElementById("plano-container");
            container.innerHTML = `<object type="image/svg+xml" id="svg-detail" data="${imageUrl}" class="w-100"></object>`;

            // 🔹 Esperar a que el nuevo SVG cargue para añadirle listeners
            const obj = document.getElementById("svg-detail");
            obj.addEventListener("load", () => {
              const innerDoc = obj.contentDocument;
              if (innerDoc) {
                const innerSvg = innerDoc.querySelector("svg");
                attachListenersToSvg(innerSvg);
              }
            });
          }
        } else {
          alert("❌ Componente no encontrado");
        }
      })
      .catch(err => {
        console.error("Error buscando componente:", err);
      });
  }

  // Inicializar sobre el SVG principal en el DOM
  const mainSvg = document.querySelector("svg");
  attachListenersToSvg(mainSvg);
});


