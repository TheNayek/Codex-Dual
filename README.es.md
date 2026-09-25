# Dos cuentas de Codex. Dos sesiones independientes de la aplicación.

v0.1.1 · [English](README.md) · [Origen y atribución](docs/PROVENANCE.md)

`doctor` analiza el `config.toml` de cada perfil registrado y muestra únicamente el selector del sandbox, sin cambiar ajustes. Si aparecen avisos UAC repetidos o un error al abrir la aplicación tras actualizarla, consulta la [guía de Windows](docs/WINDOWS.md). Son problemas distintos: el ejecutable correcto ya se usaba en la primera versión; la mitigación del sandbox procede de una investigación separada de la configuración local. El diagnóstico no verifica la configuración efectiva ni garantiza eliminar UAC.

Codex Dual inicia perfiles separados de Codex con Python 3.11 o posterior, sin dependencias. Abre tu aplicación principal como siempre e inicia el perfil `alt` en paralelo. Cada perfil usa rutas distintas para `CODEX_HOME` y los datos de Electron. Inicia sesión en cada uno mediante la interfaz normal de Codex.

**Instalación con Codex:** pega este mensaje en una tarea de Codex:

> Instala Codex Dual siguiendo https://github.com/TheNayek/Codex-Dual/blob/main/INSTALL.md . Conserva intacta mi cuenta y configuración actual. Muéstrame las rutas previstas antes de iniciar nada.

**Inicio rápido en Windows (PowerShell):**

```powershell
git clone https://github.com/TheNayek/Codex-Dual.git
cd Codex-Dual
python dual.py init --root "$env:LOCALAPPDATA\CodexDualProfiles"
python dual.py doctor
python dual.py plan alt
python dual.py launch alt
```

`plan` muestra el ejecutable, los argumentos y las rutas sin crear carpetas del perfil. `launch` crea las carpetas del perfil aislado y abre un proceso. En Windows, Codex Dual busca el ejecutable real `app/ChatGPT.exe` del paquete Codex. Si hay ambigüedad, indica `--exe` con la ruta absoluta. `Codex.exe` es el actualizador y no sirve para iniciar la aplicación.

El soporte de Codex Desktop es **experimental y depende de detalles internos** que pueden cambiar con una actualización. Esta versión no se ha validado iniciando una aplicación real. La separación de perfiles **no constituye aislamiento de seguridad del sistema operativo**: ambos procesos tienen los permisos de tu usuario.

Para registrar otro perfil: `python dual.py add trabajo --home RUTA_ABSOLUTA --user-data RUTA_ABSOLUTA`. Las rutas pueden corresponder a una instalación aislada existente; no se copian archivos ni credenciales. `list` enumera perfiles, `doctor` comprueba la configuración y `launch trabajo --dry-run` muestra el plan. `init` crea `dual.local.json`, ignorado por Git, sin sobrescribir uno existente.

El proceso secundario conserva las variables habituales del sistema y elimina las variables heredadas `CODEX_*`, `OPENAI_*` y `AZURE_OPENAI_*` antes de establecer las rutas del perfil. Codex Dual no lee claves, cookies ni datos de uso, y no cambia la configuración global. No incluyas secretos en los argumentos: `plan` los muestra literalmente.

También se puede iniciar la CLI donde haya un ejecutable directo: `python dual.py launch alt --surface cli --exe RUTA_ABSOLUTA -- --help`. En Linux y macOS, pasa un ejecutable explícito para Desktop y comprueba que la versión instalada respete las variables de aislamiento. Si la configuración de un perfil nuevo falla por permisos elevados en Windows, elige el modo **sin elevación** mediante el flujo normal de Codex; Codex Dual no altera UAC ni las opciones de seguridad.

La CLI funciona en primer plano y devuelve su código de salida. En Windows, los lanzadores `.cmd` y `.bat` no se admiten: indica un `codex.exe` directo con `--exe`. Las pruebas sin conexión: `python -m unittest discover -s tests -v`. Usan rutas sintéticas y simulan el lanzamiento de procesos. El mecanismo se investigó con ayuda de [Zoltak-Dev/ai-multi-instance](https://github.com/Zoltak-Dev/ai-multi-instance), distribuido bajo MIT. Codex Dual es una implementación independiente limitada a Codex y no es un producto oficial de OpenAI.
