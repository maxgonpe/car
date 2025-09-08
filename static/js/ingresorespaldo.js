document.addEventListener('DOMContentLoaded', function () {
  console.log("📌 ingreso.js cargado");

  const meta = document.getElementById("diagnostico-meta");
  const diagnosticoId = meta?.dataset.diagnosticoId || "";
  const CSRF = meta?.dataset.csrf || "";

  // =====================================================
  // === CARGAR SVG INLINE ===
  // =====================================================
  const cont = document.getElementById("plano-container");
  const urlSvg = cont.dataset.inicialUrl;

  async function cargarSVGInline() {
    try {
      const res = await fetch(urlSvg);
      const svgText = await res.text();
      cont.innerHTML = svgText;
      engancharEventosSVG();
    } catch (err) {
      console.error("Error cargando SVG:", err);
    }
  }

  function engancharEventosSVG() {
    cont.querySelectorAll('[id]').forEach(el => {
      el.style.cursor = "pointer";
      el.addEventListener('click', () => {
        const codigo = el.id;
        fetch(`/car/componentes-lookup/?part=${codigo}`)
          .then(r => r.json())
          .then(data => {
            if (data.found) {
              const compId = data.parent.id;
              const compNombre = data.parent.nombre;

              let cb = document.querySelector(
                `input[name="componentes_seleccionados"][value="${compId}"]`
              );
              if (!cb) {
                cb = document.createElement("input");
                cb.type = "checkbox";
                cb.name = "componentes_seleccionados";
                cb.value = compId;
                cb.id = `hidden-comp-${compId}`;
                cb.checked = true;
                cb.dataset.nombre = compNombre;
                cb.style.display = "none";
                document.forms[0].appendChild(cb);
              } else {
                cb.checked = !cb.checked;
              }

              el.style.fill = cb.checked ? "orange" : "";
              if (cb.checked) {
                agregarALista(compId, compNombre, codigo);
              } else {
                quitarDeLista(compId);
              }
            }
          });
      });
    });
  }

  // Resetear el plano
  const btnReset = document.getElementById("btn-reset-plano");
  btnReset?.addEventListener("click", cargarSVGInline);

  // Inicial
  cargarSVGInline();

  // =====================================================
  // LISTA DE COMPONENTES
  // =====================================================
  const lista = document.getElementById("lista-seleccionados");

  function agregarALista(compId, compNombre, codigoSvg = null) {
    if (!document.getElementById(`comp-li-${compId}`)) {
      const li = document.createElement("li");
      li.id = `comp-li-${compId}`;
      li.className = "list-group-item d-flex justify-content-between align-items-center";
      li.textContent = compNombre;

      const btnRemove = document.createElement("button");
      btnRemove.className = "btn btn-sm btn-outline-danger ms-2";
      btnRemove.textContent = "✕";
      btnRemove.addEventListener("click", () => {
        const cb = document.querySelector(
          `input[name="componentes_seleccionados"][value="${compId}"]`
        );
        if (cb) cb.checked = false;
        if (codigoSvg) {
          const elSvg = document.getElementById(codigoSvg);
          if (elSvg) elSvg.style.fill = "";
        }
        li.remove();
      });

      li.appendChild(btnRemove);
      lista.appendChild(li);
    }
  }

  function quitarDeLista(compId) {
    const li = document.getElementById(`comp-li-${compId}`);
    if (li) li.remove();
  }

  // =====================================================
  // REPUESTOS (igual que antes)
  // =====================================================
  window.cargarRepuestos = function () {
    let url = "";
    if (diagnosticoId) {
      url = `/diagnostico/${diagnosticoId}/sugerir-repuestos/`;
    }
    fetch(url)
      .then(r => r.json())
      .then(data => {
        const cont = document.getElementById("repuestos-list");
        cont.innerHTML = "";
        if (!data.repuestos || data.repuestos.length === 0) {
          cont.innerHTML = "<p class='text-muted'>No hay repuestos sugeridos.</p>";
          return;
        }
        data.repuestos.forEach(r => {
          const div = document.createElement("div");
          div.classList.add("card", "mb-2", "p-2");
          div.innerHTML = `
            <b>${r.nombre}</b> (${r.oem || "sin OEM"})<br>
            <small>${r.marca} ${r.modelo} ${r.anio || ""}</small><br>
            Stock: ${r.stock || 0} – $${r.precio_venta.toFixed(0)}<br>
            <button class="btn btn-success btn-sm mt-1" onclick="agregarRepuesto(${r.id})">
              ➕ Añadir al diagnóstico
            </button>
          `;
          cont.appendChild(div);
        });
      });
  };

  window.agregarRepuesto = function (repuestoId) {
    if (!diagnosticoId) {
      alert("⚠️ Primero guarda el diagnóstico para asociar repuestos.");
      return;
    }
    fetch(`/diagnostico/${diagnosticoId}/agregar-repuesto/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": CSRF,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ repuesto_id: repuestoId })
    })
      .then(r => r.json())
      .then(data => {
        alert(data.message || "Repuesto agregado");
      });
  };

  window.cargarTablaRepuestos = function () {
    if (!diagnosticoId) {
      alert("⚠️ Aún no se ha guardado el diagnóstico.");
      return;
    }
    fetch(`/diagnostico/${diagnosticoId}/repuestos/`)
      .then(r => r.json())
      .then(data => {
        const cont = document.getElementById("tabla-contenido");
        cont.innerHTML = "";
        if (!data.repuestos || data.repuestos.length === 0) {
          cont.innerHTML = "<p class='text-muted'>No hay repuestos agregados.</p>";
          return;
        }

        let tabla = `
          <table class="table table-sm table-bordered align-middle text-center">
            <thead class="table-light">
              <tr>
                <th>Nombre</th>
                <th>OEM</th>
                <th>Cantidad</th>
                <th>Precio</th>
                <th>Subtotal</th>
              </tr>
            </thead>
            <tbody>
        `;

        data.repuestos.forEach(r => {
          tabla += `
            <tr id="dr-${r.id}">
              <td>${r.nombre}</td>
              <td>${r.oem || "-"}</td>
              <td>
                <input type="number" value="${r.cantidad}" min="1"
                       class="form-control form-control-sm"
                       onchange="actualizarCantidad(${r.id}, this.value)">
              </td>
              <td>$${r.precio_unitario.toFixed(0)}</td>
              <td id="subtotal-${r.id}">$${r.subtotal.toFixed(0)}</td>
            </tr>
          `;
        });

        tabla += `
            </tbody>
          </table>
          <h5 class="text-end">💰 Total: <span id="total-general">$${data.total.toFixed(0)}</span></h5>
        `;

        cont.innerHTML = tabla;
      });
  };

  window.actualizarCantidad = function (drId, nuevaCantidad) {
    fetch(`/diagnostico/${diagnosticoId}/repuesto/${drId}/cantidad/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": CSRF,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ cantidad: nuevaCantidad })
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          alert(data.error);
          return;
        }
        document.getElementById(`subtotal-${drId}`).innerText = `$${data.subtotal.toFixed(0)}`;
        cargarTablaRepuestos();
      });
  };
});
