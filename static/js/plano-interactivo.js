document.addEventListener("DOMContentLoaded", function () {
    const zonas = document.querySelectorAll("svg [id]");

    zonas.forEach(zona => {
        zona.addEventListener("mouseenter", function () {
            zona.style.stroke = "red";
            zona.style.strokeWidth = "2";
            zona.style.cursor = "pointer";
        });

        zona.addEventListener("mouseleave", function () {
            zona.style.stroke = "none";
        });

        zona.addEventListener("click", function () {
            const idComponente = zona.id;

            fetch(`/car/componentes-lookup/?part=${idComponente}`)
                .then(res => res.json())
                .then(data => {
                    if (data.found) {
                        if (data.children && data.children.length > 0) {
                            alert(`✅ Componente: ${data.parent.nombre}\nHijos: ${data.children.map(c => c.nombre).join(", ")}`);
                        } else {
                            alert(`✅ Componente: ${data.parent.nombre}\n(No tiene hijos)`);
                        }
                    } else {
                        alert("❌ Componente no encontrado");
                    }
                })
                .catch(err => {
                    console.error("Error:", err);
                });
        });
    });
});
