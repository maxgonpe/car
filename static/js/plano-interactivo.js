// static/js/plano-interactivo.js
document.addEventListener("DOMContentLoaded", function () {
  // helper: ignora ids tipo g8, layer de inkscape
  const ignoreIdRegex = /^g\d+$/i;

  // subrayado visual (clase CSS o estilos inline)
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

  // manejador único de click que elige el candidato correcto
  function handleClickOnce(e) {
    e.preventDefault();
    e.stopPropagation();

    // obtener la pila de elementos bajo el puntero (top -> bottom)
    const elems = document.elementsFromPoint(e.clientX, e.clientY);

    // elegir el primer elemento con id válido y que no sea "gNN"
    let candidate = null;
    for (const el of elems) {
      if (el.id && !ignoreIdRegex.test(el.id)) {
        candidate = el;
        break;
      }
    }
    if (!candidate) {
      // nada válido encontrado
      console.debug("No se encontró elemento con id válido en el punto.");
      return;
    }

    const idComponente = candidate.id;
    // visual feedback
    highlight(candidate);
    setTimeout(() => unhighlight(candidate), 900);

    // construir URL absoluta por si acaso
    const fetchUrl = new URL(`/car/componentes-lookup/`, window.location.origin);
    fetchUrl.searchParams.set("part", idComponente);

    fetch(fetchUrl.toString(), { credentials: "same-origin" })
      .then(res => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(data => {
        if (data.found) {
          // muestra en un panel en vez de alert si quieres (aquí uso alert para simplicidad)
          if (data.children && data.children.length > 0) {
            alert(`✅ Componente: ${data.parent.nombre}\nHijos: ${data.children.map(c => c.nombre).join(", ")}`);
            // si hay imagen asociada, cargarla (URL absoluta)
            if (data.parent.imagen_url) {
              const imageUrl = new URL(data.parent.imagen_url, window.location.origin).toString();
              document.getElementById("plano-container").innerHTML =
                `<object type="image/svg+xml" data="${imageUrl}" class="w-100" aria-label="Detalle ${data.parent.nombre}"></object>`;
            }
          } else {
            alert(`✅ Componente: ${data.parent.nombre}\n(No tiene hijos)`);
          }
        } else {
          alert("❌ Componente no encontrado");
        }
      })
      .catch(err => {
        console.error("Error buscando componente:", err);
      });
  }

  // en lugar de añadir un listener a *cada* elemento, podemos
  // delegar en el <svg> padre. Así solo hay un listener y no se duplica.
  // Pero aquí mantengo attach por si ya tienes listener por elemento:
  const zonas = document.querySelectorAll("svg [id]");
  zonas.forEach(z => {
    // remover posibles listeners duplicados (evita ghost handlers)
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

  // adicional: delegación sobre el contenedor (opcional)
  // const svgContainer = document.getElementById('plano-container');
  // svgContainer && svgContainer.addEventListener('click', handleClickOnce);
});


