// static/js/plano-interactivo.js
document.addEventListener('DOMContentLoaded', function () {
  const container = document.getElementById('plano-container');

  // 1) Asigna data-part automáticamente = id si no existe (sólo a elementos con id)
  container.querySelectorAll('svg [id]').forEach(function (el) {
    if (!el.hasAttribute('data-part')) {
      el.setAttribute('data-part', el.id);
    }
    // accesible al foco por teclado
    el.setAttribute('tabindex', '0');
  });

  // 2) Delegación de eventos: clicks dentro del SVG
  container.addEventListener('click', function (evt) {
    const el = evt.target.closest('[data-part]');
    if (!el) return;
    evt.preventDefault();

    const part = el.getAttribute('data-part');
    if (!part) return;

    fetch(`/componentes/lookup/?part=${encodeURIComponent(part)}`)
      .then(resp => resp.json())
      .then(data => {
        const panel = document.getElementById('part-info');
        const name = document.getElementById('part-name');
        const list = document.getElementById('part-children');
        list.innerHTML = '';

        if (data.found) {
          name.textContent = `${data.parent.nombre} (${data.parent.codigo})`;

          if (data.children && data.children.length) {
            data.children.forEach(c => {
              const li = document.createElement('li');
              // OJO: nuestra URL es /componentes/<id>/editar/, no /edit/
              li.innerHTML = `<a href="/componentes/${c.id}/editar/">${c.nombre}</a> — <small>${c.codigo}</small>`;
              list.appendChild(li);
            });
          } else {
            const li = document.createElement('li');
            li.textContent = 'Sin subcomponentes registrados.';
            list.appendChild(li);
          }
        } else {
          name.textContent = `No existe componente: ${part}`;
          const li = document.createElement('li');
          li.innerHTML = `Puedes <a href="/componentes/nuevo/">crear uno nuevo</a>`;
          list.appendChild(li);
        }
        panel.style.display = 'block';
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      })
      .catch(() => {
        alert('No se pudo consultar el componente. Revisa la URL /componentes/lookup/.');
      });
  });

  // 3) Teclado: Enter/Espacio activa la selección también
  container.addEventListener('keydown', function (evt) {
    if (evt.key !== 'Enter' && evt.key !== ' ') return;
    const el = evt.target.closest('[data-part]');
    if (!el) return;
    el.click();
  });
});
