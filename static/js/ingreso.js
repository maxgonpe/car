/* ======= Helpers ======= */
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/* ======= Main DOM logic ======= */
document.addEventListener('DOMContentLoaded', function () {
  console.log("📌 ingreso.html cargado");

  // --- Meta ---
  const meta = document.getElementById("diagnostico-meta");
  const diagnosticoId = meta?.dataset.diagnosticoId?.trim() || "";
  const CSRF = meta?.dataset.csrf || "";

  // ==================== CLIENTE ====================
  const clienteSelect  = document.getElementById('cliente_existente');
  const nuevoClienteCampos = document.getElementById('nuevo_cliente_campos');
  function toggleClienteCampos() {
    if (!nuevoClienteCampos) return;
    nuevoClienteCampos.style.display = clienteSelect && clienteSelect.value ? 'none' : 'block';
  }
  if (clienteSelect) {
    clienteSelect.addEventListener('change', () => {
      toggleClienteCampos();
      cargarVehiculos(clienteSelect.value);
      const vehSel = document.getElementById('vehiculo_select');
      if (vehSel) vehSel.value = '';
      toggleVehiculoCampos();
    });
    toggleClienteCampos();
  }

  // ==================== VEHÍCULO ====================
  const vehiculoSelect = document.getElementById('vehiculo_select');
  const vehiculoFields = document.getElementById('vehiculo_fields');
  function toggleVehiculoCampos() {
    if (!vehiculoFields) return;
    vehiculoFields.style.display = vehiculoSelect && vehiculoSelect.value ? 'none' : 'block';
  }

  async function cargarVehiculos(clienteId, selectedVehiculoId = null) {
    if (!vehiculoSelect) return;
    vehiculoSelect.innerHTML = '<option value="">-- Nuevo vehículo --</option>';
    if (!clienteId) { toggleVehiculoCampos(); return; }
    try {
      const res = await fetch(`/api/vehiculos/${clienteId}/`);
      if (!res.ok) return;
      const data = await res.json();
      data.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.id;
        opt.textContent = `${v.placa} • ${v.marca} ${v.modelo} (${v.anio})`;
        if (selectedVehiculoId && String(v.id) === String(selectedVehiculoId)) {
          opt.selected = true;
        }
        vehiculoSelect.appendChild(opt);
      });
    } catch (err) {
      console.error("Error cargando vehículos:", err);
    }
    toggleVehiculoCampos();
  }

  if (vehiculoSelect) {
    vehiculoSelect.addEventListener('change', toggleVehiculoCampos);
    if (clienteSelect && clienteSelect.value) {
      cargarVehiculos(clienteSelect.value, vehiculoSelect.dataset.selected);
    } else {
      toggleVehiculoCampos();
    }
  }

  // ==================== COMPONENTES seleccionados ====================
  const lista = document.getElementById("lista-seleccionados");
  function agregarALista(compId, compNombre, codigoSvg = null) {
    if (!lista) return;
    if (!document.getElementById(`comp-li-${compId}`)) {
      const li = document.createElement("li");
      li.id = `comp-li-${compId}`;
      li.className = "list-group-item d-flex justify-content-between align-items-center";
      li.textContent = compNombre;

      const btnRemove = document.createElement("button");
      btnRemove.className = "btn btn-sm btn-outline-danger ms-2";
      btnRemove.textContent = "✕";
      btnRemove.addEventListener("click", () => {
        const cb = document.querySelector(`input[name="componentes_seleccionados"][value="${compId}"]`);
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

  function actualizarListaSeleccionados() {
    if (!lista) return;
    lista.innerHTML = "";
    document.querySelectorAll('input[name="componentes_seleccionados"]:checked').forEach(cb => {
      const nombre = cb.dataset.nombre || cb.value;
      agregarALista(cb.value, nombre);
    });
  }

  document.querySelectorAll('input[name="componentes_seleccionados"]').forEach(cb => {
    cb.addEventListener("change", actualizarListaSeleccionados);
  });
  actualizarListaSeleccionados();

  // ==================== INTERACTIVIDAD SVG ====================
  const planoContainer = document.getElementById('plano-container');
  if (planoContainer) {
    planoContainer.addEventListener('click', function (ev) {
      const target = ev.target.closest('[id]');
      if (!target || !planoContainer.contains(target)) return;
      const codigo = target.id;
      fetch(`/car/componentes-lookup/?part=${encodeURIComponent(codigo)}`)
        .then(r => r.json())
        .then(data => {
          if (!data) return;
          if (data.found) {
            const compId = data.parent.id;
            const compNombre = data.parent.nombre;
            let cb = document.querySelector(`input[name="componentes_seleccionados"][value="${compId}"]`);
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
            target.style.fill = cb.checked ? "orange" : "";
            if (cb.checked) {
              agregarALista(compId, compNombre, codigo);
            } else {
              quitarDeLista(compId);
            }
          }
        })
        .catch(err => console.error("componentes-lookup error:", err));
    });
  }

  const btnResetPlano = document.getElementById("btn-reset-plano");
  if (btnResetPlano) {
    btnResetPlano.addEventListener("click", () => {
      const cont = document.getElementById("plano-container");
      if (!cont) return;
      const url = cont.dataset.inicialUrl;
      cont.innerHTML = `<object type="image/svg+xml" data="${url}" class="w-100"></object>`;
    });
  }

  // ================= REPUESTOS =================
  window.cargarRepuestos = function () {
    const cont = document.getElementById("repuestos-list");
    if (!cont) return;

    let url = "";
    if (diagnosticoId) {
      // modo con diagnóstico guardado
      url = cont.dataset.withIdTemplate.replace("0", diagnosticoId);
    } else {
      // modo preview
      const compIds = Array.from(document.querySelectorAll('input[name="componentes_seleccionados"]:checked'))
                           .map(cb => cb.value);
      const marca = document.getElementById("id_marca")?.value || "";
      const modelo = document.getElementById("id_modelo")?.value || "";
      const anio = document.getElementById("id_anio")?.value || "";

      const params = new URLSearchParams();
      compIds.forEach(c => params.append("componentes_ids", c));
      if (marca) params.append("marca", marca);
      if (modelo) params.append("modelo", modelo);
      if (anio) params.append("anio", anio);

      url = cont.dataset.previewUrl + "?" + params.toString();
    }

    // fetch y render
    fetch(url)
      .then(r => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(data => {
        cont.innerHTML = "";
        if (!data.repuestos || data.repuestos.length === 0) {
          cont.innerHTML = "<p class='text-muted'>No hay repuestos sugeridos.</p>";
          return;
        }
        data.repuestos.forEach(r => {
          const div = document.createElement("div");
          div.classList.add("card", "mb-2", "p-2");
          div.innerHTML = `
  <label class="form-check">
    <input type="checkbox"
           class="form-check-input repuesto-check"
           data-id="${r.id}"
           data-stock-id="${r.repuesto_stock_id || ''}"
           data-precio="${r.precio_venta || 0}"
           data-nombre="${escapeHtml(r.nombre)}"
           data-oem="${escapeHtml(r.oem || '')}">
    <b>${escapeHtml(r.nombre)}</b> (${escapeHtml(r.oem || "sin OEM")})<br>
    <small>${escapeHtml(r.sku || "")} • ${escapeHtml(r.posicion || "")}</small><br>
    Stock: ${r.disponible} – 💰 $${(r.precio_venta || 0).toFixed(0)}
  </label>
  <div class="mt-1">
      <label class="form-label small mb-0">Cantidad</label>
      <input type="number"
             class="form-control form-control-sm repuesto-cantidad"
             data-id="${r.id}"
             min="1"
             value="1"
             style="max-width:80px;">
    </div>
  </div>
`;
          cont.appendChild(div);
        });
      })
      .catch(err => {
        cont.innerHTML = `<div class="alert alert-warning">Error cargando repuestos: ${escapeHtml(err.message)}</div>`;
      });
  };

  // Prepara JSON de repuestos seleccionados para enviar en el formulario
  function prepararRepuestosParaEnvio() {
  const repuestos = [];
  document.querySelectorAll("#repuestos-list input.repuesto-check:checked").forEach(chk => {
    const cantidadInput = document.querySelector(
      `#repuestos-list input.repuesto-cantidad[data-id="${chk.dataset.id}"]`
    );
    const cantidad = cantidadInput ? parseInt(cantidadInput.value) || 1 : 1;
    repuestos.push({
      id: chk.dataset.id,
      repuesto_stock_id: chk.dataset.stockId || null,
      cantidad: cantidad,
      precio_unitario: parseFloat(chk.dataset.precio || 0),
      nombre: chk.dataset.nombre || '',
      oem: chk.dataset.oem || ''
    });
  });
  const hidden = document.getElementById("repuestos-json");
  if (hidden) {
    hidden.value = JSON.stringify(repuestos);
    console.log("✅ repuestos-json listo:", hidden.value);
  } else {
    console.warn("⚠️ No se encontró el input hidden #repuestos-json");
  }

  // Detiene aquí el flujo para inspeccionar en consola
  //debugger;
}


  // ==================== AGREGAR / TABLA (opcional ajax) ====================
  window.agregarRepuesto = function (repuestoId, stockId) {
    if (!diagnosticoId) {
      alert("⚠️ Guarda el diagnóstico antes de agregar repuestos.");
      return;
    }
    const cont = document.getElementById("repuestos-list");
    fetch(`/diagnostico/${diagnosticoId}/agregar-repuesto/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": CSRF,
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify({
        repuesto_id: repuestoId,
        repuesto_stock_id: stockId,
        cantidad: 1
      })
    })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        alert("❌ " + data.error);
        return;
      }
      cargarTablaRepuestos();
      if (cont) {
        const flash = document.createElement('div');
        flash.className = 'alert alert-success small mt-2';
        flash.textContent = 'Repuesto agregado al diagnóstico';
        cont.prepend(flash);
        setTimeout(()=> flash.remove(), 2000);
      }
    })
    .catch(err => {
      alert("Error al agregar repuesto: " + err.message);
    });
  };

  window.cargarTablaRepuestos = function () {
    if (!diagnosticoId) {
      document.getElementById("tabla-contenido").innerHTML =
        "<p class='text-muted'>Guarda el diagnóstico y vuelve para ver repuestos agregados.</p>";
      return;
    }
    fetch(`/diagnostico/${diagnosticoId}/repuestos/`, { headers: { 'Accept': 'application/json' } })
      .then(res => res.json())
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
            <tr>
              <td>${escapeHtml(r.nombre)}</td>
              <td>${escapeHtml(r.oem || "-")}</td>
              <td>${Number(r.cantidad)}</td>
              <td>$${Number(r.precio_unitario || 0).toFixed(0)}</td>
              <td>$${Number(r.subtotal || 0).toFixed(0)}</td>
            </tr>
          `;
        });
        tabla += `
            </tbody>
          </table>
          <h5 class="text-end">💰 Total: $${Number(data.total || 0).toFixed(0)}</h5>
        `;
        cont.innerHTML = tabla;
      })
      .catch(err => {
        const cont = document.getElementById("tabla-contenido");
        cont.innerHTML = `<div class="alert alert-danger">Error cargando repuestos: ${escapeHtml(err.message)}</div>`;
      });
  };

  // ==================== ACCIONES (tu bloque IIFE) ====================
  (function() {
    const UL_SELECCIONADOS = document.getElementById('lista-seleccionados');
    const UL_ACCIONES = document.getElementById('acciones-para-componentes');
    const HIDDEN_ACC = document.getElementById('acciones_componentes_json');
    const TOTAL_MO = document.getElementById('total_mano_obra');
    if (!UL_SELECCIONADOS || !UL_ACCIONES || !HIDDEN_ACC) return;

    const ANCLA = document.getElementById('acciones-endpoints');
    const URL_TPL = ANCLA ? ANCLA.dataset.accionesUrlTemplate : '/car/acciones-lookup/0/';
    function buildAccionesUrl(compId) {
      return URL_TPL.replace(/0\/?$/, String(compId) + '/');
    }

    const ACC = {};
    const CLP = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });

    function updateHiddenAndTotal() {
      const payload = Object.entries(ACC)
        .map(([id, v]) => ({
          componente_id: parseInt(id),
          accion_id: v.accion_id ? parseInt(v.accion_id) : null,
          precio: (v.precio ?? '').toString()
        }))
        .filter(x => x.accion_id);
      HIDDEN_ACC.value = JSON.stringify(payload);
      const sum = payload.reduce((acc, it) => acc + (parseFloat(it.precio || 0) || 0), 0);
      if (TOTAL_MO) TOTAL_MO.textContent = CLP.format(sum);
    }

    async function loadAccionesForComponent(compId) {
      const urls = [buildAccionesUrl(compId), buildAccionesUrl(compId).replace(/\/$/, '')];
      for (const u of urls) {
        try {
          const res = await fetch(u);
          if (!res.ok) continue;
          const data = await res.json();
          return (data.ok && data.acciones) ? data.acciones : [];
        } catch (_) {}
      }
      return [];
    }

    function parseCompIdFromLi(li) {
      const m = (li.id || '').match(/^comp-li-(.+)$/);
      return m ? m[1] : null;
    }
    function getNombreFromLi(li) {
      const btn = li.querySelector('button');
      if (!btn) return (li.textContent || '').trim();
      const full = (li.textContent || '').trim();
      const btnTxt = (btn.textContent || '').trim();
      return full.replace(btnTxt, '').trim();
    }

    async function ensureMirrorRow(compId, nombre) {
      compId = String(compId);
      ACC[compId] = ACC[compId] || { nombre, accion_id: null, precio: '' };
      let li = UL_ACCIONES.querySelector(`li[data-componente-id="${compId}"]`);
      if (!li) {
        li = document.createElement('li');
        li.className = 'list-group-item';
        li.setAttribute('data-componente-id', compId);
        li.innerHTML = `
          <div class="row g-2 align-items-end">
            <div class="col-12 col-md-4">
              <div class="fw-semibold">${nombre}</div>
              <div class="text-muted small">ID: ${compId}</div>
            </div>
            <div class="col-12 col-md-4">
              <label class="form-label mb-0">Acción</label>
              <select class="form-select form-select-sm accion-select">
                <option value="">-- Seleccione --</option>
              </select>
            </div>
            <div class="col-8 col-md-3">
              <label class="form-label mb-0">Precio</label>
              <input type="number" step="0.01" class="form-control form-control-sm accion-precio" placeholder="0.00">
              <small class="text-muted">Vacío/0 usa precio base</small>
            </div>
            <div class="col-4 col-md-1 text-end">
              <button type="button" class="btn btn-outline-secondary btn-sm limpiar-accion">×</button>
            </div>
          </div>
        `;
        UL_ACCIONES.appendChild(li);

        const sel = li.querySelector('.accion-select');
        const inp = li.querySelector('.accion-precio');
        const btn = li.querySelector('.limpiar-accion');
        sel.addEventListener('change', () => {
          const opt = sel.options[sel.selectedIndex];
          const base = opt?.getAttribute('data-precio') || '';
          if (base && (!inp.value || inp.value === '0' || inp.value === '0.00')) {
            inp.value = base;
          }
          ACC[compId].accion_id = sel.value || null;
          if (!ACC[compId].precio && inp.value) {
            ACC[compId].precio = inp.value;
          }
          updateHiddenAndTotal();
        });
        inp.addEventListener('input', () => {
          ACC[compId].precio = inp.value;
          updateHiddenAndTotal();
        });
        btn.addEventListener('click', () => {
          sel.value = '';
          inp.value = '';
          ACC[compId].accion_id = null;
          ACC[compId].precio = '';
          updateHiddenAndTotal();
        });
      }
      const select = li.querySelector('.accion-select');
      if (select && select.options.length <= 1) {
        const acciones = await loadAccionesForComponent(compId);
        select.innerHTML = `<option value="">-- Seleccione --</option>` +
          acciones.map(a => `<option value="${a.accion_id}" data-precio="${a.precio_base ?? ''}">${a.accion_nombre}</option>`).join('');
      }
    }

    function removeMirrorRow(compId) {
      compId = String(compId);
      delete ACC[compId];
      const li = UL_ACCIONES.querySelector(`li[data-componente-id="${compId}"]`);
      if (li) li.remove();
      updateHiddenAndTotal();
    }

    function bootstrapFromCurrentLis() {
      UL_SELECCIONADOS.querySelectorAll('li[id^="comp-li-"]').forEach(li => {
        const compId = parseCompIdFromLi(li);
        if (!compId) return;
        const nombre = getNombreFromLi(li);
        ensureMirrorRow(compId, nombre);
      });
    }
    bootstrapFromCurrentLis();

    const observer = new MutationObserver(muts => {
      muts.forEach(m => {
        m.addedNodes.forEach(n => {
          if (n.nodeType !== 1) return;
          if (!/^comp-li-/.test(n.id || '')) return;
          const compId = parseCompIdFromLi(n);
          if (!compId) return;
          const nombre = getNombreFromLi(n);
          ensureMirrorRow(compId, nombre);
        });
        m.removedNodes.forEach(n => {
          if (n.nodeType !== 1) return;
          if (!/^comp-li-/.test(n.id || '')) return;
          const compId = parseCompIdFromLi(n);
          if (!compId) return;
          removeMirrorRow(compId);
        });
      });
    });
    observer.observe(UL_SELECCIONADOS, { childList: true });
    document.querySelector('form')?.addEventListener('submit', updateHiddenAndTotal);
  })();

  // Antes de enviar el form: preparar repuestos seleccionados
  const form = document.querySelector("#form-ingreso");
if (form) {
  form.addEventListener("submit", function(e) {
    prepararRepuestosParaEnvio();

    // corta el flujo la primera vez para inspeccionar
    //e.preventDefault();
    //console.log("🛑 Submit detenido. Verifica #repuestos-json en consola.");
    //console.log("Contenido hidden:", document.getElementById("repuestos-json")?.value);

    // 👉 cuando confirmes que funciona, comenta estas 2 líneas (preventDefault + console.log)
    // para que el submit vuelva a funcionar normalmente
  });
}
// ---------------------- BUSCAR VEHICULO POR PLACA ----------------------



//
}); // fin DOMContentLoaded

