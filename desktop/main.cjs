const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("node:child_process");
const net = require("node:net");
const path = require("node:path");

app.setName("Nexo Stock");
const hasSingleInstance = app.requestSingleInstanceLock();
if (!hasSingleInstance) app.quit();

let mainWindow;
let backend;
let backendUrl = "";
let isShuttingDown = false;
let allowQuit = false;

function findAvailablePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const port = probe.address().port;
      probe.close(error => error ? reject(error) : resolve(port));
    });
  });
}

function backendFiles() {
  if (app.isPackaged) {
    const appRoot = path.join(process.resourcesPath, "app-files");
    return {
      appRoot,
      executable: path.join(process.resourcesPath, "backend", "nexo-stock-server.exe"),
      args: []
    };
  }
  const appRoot = path.resolve(__dirname, "..");
  return {
    appRoot,
    executable: process.env.NEXO_PYTHON || "python",
    args: [path.join(appRoot, "server.py")]
  };
}

async function startBackend() {
  const port = await findAvailablePort();
  const files = backendFiles();
  const dataRoot = path.join(app.getPath("userData"), "data");
  backendUrl = `http://localhost:${port}`;
  backend = spawn(files.executable, files.args, {
    cwd: files.appRoot,
    windowsHide: true,
    stdio: "ignore",
    env: {
      ...process.env,
      NEXO_STOCK_PORT: String(port),
      NEXO_STOCK_APP_DIR: files.appRoot,
      NEXO_STOCK_DATA_DIR: dataRoot
    }
  });

  const startupError = new Promise((_, reject) => {
    backend.once("error", reject);
    backend.once("exit", code => {
      if (!isShuttingDown) reject(new Error(`El servidor local terminó durante el inicio (${code ?? "sin código"}).`));
    });
  });
  const ready = (async () => {
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
      if (backend.exitCode !== null) throw new Error("El servidor local no pudo iniciarse.");
      try {
        const response = await fetch(`${backendUrl}/api/health`, { signal: AbortSignal.timeout(800) });
        if (response.ok) return;
      } catch { /* Espera hasta que SQLite y HTTP estén listos. */ }
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    throw new Error("El servidor local tardó demasiado en iniciar.");
  })();
  await Promise.race([ready, startupError]);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 860,
    minHeight: 600,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: "#101416",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  mainWindow.webContents.on("will-navigate", (event, target) => {
    if (!target.startsWith(backendUrl + "/")) event.preventDefault();
  });
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.on("closed", () => { mainWindow = null; });
  mainWindow.loadURL(backendUrl);
}

async function stopBackend() {
  if (!backend || backend.exitCode !== null) return;
  isShuttingDown = true;
  try {
    await fetch(`${backendUrl}/api/shutdown`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
      signal: AbortSignal.timeout(1200)
    });
  } catch { /* El proceso se cerrará de forma forzada si no responde. */ }
  await Promise.race([
    new Promise(resolve => backend.once("exit", resolve)),
    new Promise(resolve => setTimeout(resolve, 1500))
  ]);
  if (backend.exitCode === null) backend.kill();
}

app.on("before-quit", event => {
  if (allowQuit || !backend || backend.exitCode !== null) return;
  event.preventDefault();
  if (isShuttingDown) return;
  isShuttingDown = true;
  stopBackend().finally(() => {
    allowQuit = true;
    app.quit();
  });
});

app.on("second-instance", () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

app.whenReady().then(async () => {
  try {
    await startBackend();
    createWindow();
  } catch (error) {
    dialog.showErrorBox(
      "No se pudo abrir Nexo Stock",
      `El servidor local de datos no inició. Cierra cualquier otra instancia y vuelve a abrir la app.\n\n${error.message}`
    );
    app.quit();
  }
});

app.on("window-all-closed", () => app.quit());
