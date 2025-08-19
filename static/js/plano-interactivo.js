// static/js/plano-interactivo.js
document.addEventListener("DOMContentLoaded", function () {
  const ignoreIdRegex = /^g\d+$/i;

  // ================================
  // Funciones auxiliares
  // ================================
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

  // ➕ Agregar a la lista textual
  function addToListaSeleccionados(id, nombre) {
    const lista = document.getElementById("lista-seleccionados");
    if (!lista) return;

    // Evitar duplicados
    if (document.getElementById(`li-comp-${id}`)) return;

    const li = document.createElement("li");
    li.id = `li-comp-${id}`;
    li.className = "list-group-item d-flex justify-content-between align-items-center";
    li.textContent = nombre;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-sm btn-danger";
    btn.textContent = "❌";
    btn.onclick = () => removeFromListaSeleccionados(id);

    li.appendChild(btn);
    lista.appendChild(li);
  }

  // ❌ Quitar de la lista textual y del checkbox
  function removeFromListaSeleccionados(id) {
    const li = document.getElementById(`li-comp-${id}`);
    if (li) li.remove();

    const checkbox = document.querySelector(
      `input[name="componentes_seleccionados"][value="${id}"]`
    );
    if (checkbox) {
      checkbox.checked = false;
      checkbox.dispatchEvent(new Event("change"));
    }
  }

  // ================================
  // Click sobre SVG
  // ================================
  function handleClickOnce(e) {
    e.preventDefault();
    e.stopPropagation();

    let elems;
    if (e.view && e.view.document) {
      elems = e.view.document.elementsFromPoint(e.clientX, e.clientY);
    } else {
      elems = document.elementsFromPoint(e.clientX, e.clientY);
    }

    let candidate = null;
    for (const el of elems) {
      if (el.id && !ignoreIdRegex.test(el.id)) {
        candidate = el;
        break;
      }
    }

    if (!candidate) return;

    const idOriginal = candidate.id.trim();
    let idComponente = idOriginal.replace(/-\d+$/, "").toLowerCase();

    console.log("🔍 ID detectado:", idOriginal, "→", idComponente);

    const fetchUrl = `/car/componentes-lookup/?part=${idComponente}`;
    console.log("📡 Consultando:", fetchUrl);

    fetch(fetchUrl, { credentials: "same-origin" })
      .then(res => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(data => {
        if (!data.found) {
          alert("❌ Componente no encontrado");
          return;
        }

        if (data.children && data.children.length > 0) {
          // Tiene hijos → mostrar detalle si quieres
        } else {
          // ✅ Seleccionable
          const confirmAdd = confirm(`✅ Componente: ${data.parent.nombre}\n¿Desea agregarlo al diagnóstico?`);

          if (confirmAdd) {
            const checkbox = document.querySelector(
              `input[name="componentes_seleccionados"][value="${data.parent.id}"]`
            );
            if (checkbox) {
              checkbox.checked = true;
              checkbox.dispatchEvent(new Event("change"));
              console.log(`✔️ Marcado en acordeón: ${data.parent.nombre} (id=${data.parent.id})`);

              // 🔽 también agregar a la lista textual
              addToListaSeleccionados(data.parent.id, data.parent.nombre);
            } else {
              console.warn(`⚠️ No encontré checkbox para id ${data.parent.id}`);
            }
          }
        }

        // Mostrar imagen asociada si existe
        if (data.parent.imagen_url) {
          const imageUrl = new URL(data.parent.imagen_url, window.location.origin).toString();
          const container = document.getElementById("plano-container");
          container.innerHTML = `<object type="image/svg+xml" id="svg-detail" data="${imageUrl}" class="w-100"></object>`;

          const obj = document.getElementById("svg-detail");
          obj.addEventListener("load", () => {
            const innerDoc = obj.contentDocument;
            if (innerDoc) {
              const innerSvg = innerDoc.querySelector("svg");
              attachListenersToSvg(innerSvg);
            }
          });
        }
      })
      .catch(err => {
        console.error("Error buscando componente:", err);
      });
  }

  // Inicializar sobre el SVG principal en el DOM
  const mainSvg = document.querySelector("svg");
  attachListenersToSvg(mainSvg);

  // ================================
  // Botón resetear plano
  // ================================
  const btnReset = document.getElementById("btn-reset-plano");
  if (btnReset) {
    btnReset.addEventListener("click", () => {
      const urlInicial = document.getElementById("plano-container").dataset.inicialUrl;
      const container = document.getElementById("plano-container");
      container.innerHTML = `<object type="image/svg+xml" id="svg-detail" data="${urlInicial}" class="w-100"></object>`;

      const obj = document.getElementById("svg-detail");
      obj.addEventListener("load", () => {
        const innerDoc = obj.contentDocument;
        if (innerDoc) {
          const innerSvg = innerDoc.querySelector("svg");
          attachListenersToSvg(innerSvg);
        }
      });
    });
  }
});
