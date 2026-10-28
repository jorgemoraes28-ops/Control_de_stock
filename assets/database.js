(function () {
  const keys = [
    "nexo-stock-products",
    "nexo-stock-movements",
    "nexo-stock-suppliers",
    "nexo-stock-vehicles",
    "nexo-stock-users",
    "nexo-stock-settings",
    "nexo-stock-audit",
    "nexo-stock-email-simulations"
  ];
  const nativeGet = localStorage.getItem.bind(localStorage);
  const nativeSet = localStorage.setItem.bind(localStorage);
  const nativeRemove = localStorage.removeItem.bind(localStorage);
  let saveQueue = Promise.resolve();
  function markDatabaseFailure() {
    window.dispatchEvent(new CustomEvent("nexo-database-error"));
  }

  function applyCollections(collections) {
    for (const key of keys) {
      if (Object.prototype.hasOwnProperty.call(collections, key)) {
        nativeSet(key, JSON.stringify(collections[key]));
      } else {
        nativeRemove(key);
      }
    }
  }

  const ready = (async () => {
    try {
      const response = await fetch("/api/bootstrap", { cache: "no-store" });
      if (!response.ok) throw new Error("El servidor de base de datos no está disponible.");
      let snapshot = await response.json();

      if (!snapshot.initialized) {
        const legacy = {};
        for (const key of keys) {
          const value = nativeGet(key);
          if (value !== null) {
            try { legacy[key] = JSON.parse(value); } catch { /* Se conserva intacto si no es JSON válido. */ }
          }
        }
        if (Object.keys(legacy).length) {
          const imported = await fetch("/api/import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ collections: legacy })
          });
          if (!imported.ok) throw new Error("No se pudieron migrar los datos guardados en este navegador.");
          snapshot = (await imported.json()).bootstrap;
        }
      }

      if (snapshot.initialized) applyCollections(snapshot.collections || {});
      return { available: true, initialized: Boolean(snapshot.initialized) };
    } catch (error) {
      console.error("Nexo Stock: se usará el almacenamiento local del navegador.", error);
      markDatabaseFailure();
      return { available: false, initialized: false };
    }
  })();

  window.appDatabase = {
    ready,
    saveAll(collections) {
      saveQueue = saveQueue.then(async () => {
        const state = await ready;
        if (!state.available) return;
        const response = await fetch("/api/import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ collections }),
          keepalive: true
        });
        if (!response.ok) throw new Error("No se pudo guardar el estado inicial de SQLite.");
      }).catch(error => {
        console.error("Nexo Stock: error al inicializar SQLite.", error);
        markDatabaseFailure();
      });
      return saveQueue;
    },
    save(key, serializedValue) {
      if (!keys.includes(key)) return Promise.resolve();
      saveQueue = saveQueue.then(async () => {
        const state = await ready;
        if (!state.available) return;
        const value = JSON.parse(serializedValue);
        const response = await fetch("/api/collections/" + encodeURIComponent(key), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value }),
          keepalive: true
        });
        if (!response.ok) throw new Error("La base local rechazó el guardado de " + key + ".");
      }).catch(error => {
        console.error("Nexo Stock: error al guardar en SQLite.", error);
        markDatabaseFailure();
      });
      return saveQueue;
    }
  };
})();
