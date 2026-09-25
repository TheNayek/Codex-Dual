# Dos cuentas de Codex. Dos accesos directos.

v0.2.0 · [English](README.md) · [Origen y atribución](docs/PROVENANCE.md)

Abre tu cuenta principal como siempre y la segunda desde su propio acceso
directo. Codex Dual separa los datos de ambas cuentas y prepara la instalación
para el uso diario. El flujo recomendado incluye la configuración del sandbox
que evitó los avisos UAC repetidos en la instalación del mantenedor.
Requiere Python 3.11+, sin paquetes adicionales.

## Dale esto a Codex

> Instala Codex Dual siguiendo https://github.com/TheNayek/Codex-Dual/blob/main/INSTALL.md . Conserva mis cuentas y datos existentes. Configura las dos instalaciones de Codex con el sandbox sin elevación recomendado para evitar el problema de aprovisionamiento repetido, manteniendo los límites del workspace y las aprobaciones. Entiendo que tiene menor aislamiento que el modo elevado. Crea un acceso directo de escritorio para abrir la segunda cuenta con doble clic. Conserva los accesos que ya funcionen. Muéstrame los cambios previstos y verifica el resultado.

El [procedimiento de instalación](INSTALL.md) indica qué configurar, cómo
comprobarlo y cómo deshacerlo. El agente hace ese ajuste autorizado una vez;
el lanzador no cambia los permisos cada vez que abres Codex.

## Uso diario

- **Cuenta principal:** tu icono habitual de Codex.
- **Segunda cuenta:** el nuevo acceso `Codex - alt`.
- Inicia sesión por separado. No se copian credenciales.

No hace falta escribir comandos cada vez. El acceso usa un lanzador sin consola
y busca el ejecutable instalado en cada apertura. Mantén la carpeta del repo y
Python donde los instalaste; si los mueves, vuelve a crear el acceso.

## La configuración para evitar el problema de UAC

El flujo recomendado establece `windows.sandbox = "unelevated"` en **ambas
cuentas** antes del uso diario. Fue necesario en el entorno del mantenedor para
evitar que el aprovisionamiento del sandbox elevado interrumpiera el trabajo.
No desactiva UAC ni habilita acceso total: conserva límites de archivos y las
aprobaciones existentes, aunque ofrece menor aislamiento que el sandbox elevado.
[Procedimiento y documentación oficial](docs/WINDOWS.md).

No significa que todas las versiones necesiten esa mitigación ni que deban
desaparecer las solicitudes legítimas de permisos. Si tu organización exige el
modo elevado, hay que resolver esa compatibilidad antes de adoptar este flujo.

## Comandos de instalación opcionales

Desde el repo clonado, se ejecutan una vez. Sigue [INSTALL.md](INSTALL.md) para
configurar y comprobar ambas cuentas antes de abrirlas:

```powershell
python dual.py init --root "$env:LOCALAPPDATA\CodexDualProfiles"
python dual.py plan alt
# Aplicar el ajuste del sandbox de INSTALL.md y después:
python dual.py doctor
python shortcut.py alt
python shortcut.py alt --apply
```

`shortcut.py` muestra primero lo que va a crear; con `--apply` crea el acceso
sin abrir Codex ni sobrescribir accesos existentes. `--desktop-dir` permite elegir
otra carpeta existente. Los demás comandos siguen disponibles para diagnósticos
o uso de CLI; consulta [README.md](README.md).

## Respecto al lanzador original

[ai-multi-instance](https://github.com/Zoltak-Dev/ai-multi-instance) también
ofrece accesos directos y añade menú, gestión de perfiles, consumo y soporte
para Claude. Dual se centra en Codex, accesos directos, instalación verificable
y diagnóstico; no incluye ese menú ni la consulta de consumo. Si tu instalación
actual ya funciona, puedes conservarla y aplicar las mismas pautas de sandbox.

El mecanismo de separación y el ejecutable proceden de la investigación con ese
proyecto MIT; la implementación de Dual se escribió por separado. El soporte
Desktop depende de detalles internos y sigue siendo experimental. Las pruebas
no inician Codex ni sustituyen comprobar ambas sesiones reales. Codex Dual no
es un producto oficial de OpenAI.