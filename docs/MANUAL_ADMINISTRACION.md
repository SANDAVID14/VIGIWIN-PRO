# MANUAL DE ADMINISTRACIÓN - VIGI-WIN PRO v1.0
## Gestión del Sistema, Grabadores DVR/NVR, Redes RTSP y Seguridad

---

### 1. Control de Acceso Basado en Roles (RBAC)
El sistema dispone de tres perfiles predefinidos almacenados en la base de datos local con contraseñas seguras bajo hash criptográfico SHA-256:

| Rol | Privilegios | Uso Típico |
| :--- | :--- | :--- |
| **Administrador** | Acceso total: agregar cámaras, configurar umbrales, backups, compilación. | Jefe de seguridad / Administrador IT |
| **Operador de Seguridad** | Monitoreo en vivo, control de simulación, confirmación y acuse de alarmas. | Guardia de turno / Operador de garita |
| **Auditor** | Consulta de historial de eventos, logs de auditoría y exportación a CSV. | Control interno / Auditoría de accesos |

---

### 2. Conexión de Grabadores DVR/NVR y Cámaras IP (RTSP sobre TCP)
Para agregar una nueva cámara o canal desde la **Pestaña 3 (Administración & RBAC)**:

1. Ingrese el **ID de Cámara** (ejemplo: `CAM_02`).
2. Indique un **Nombre descriptivo** (ejemplo: `Portón Vehicular Calle Norte`).
3. En **Tipo de Conexión**, seleccione `RTSP (DVR/NVR sobre TCP)`.
4. Ingrese la URL de flujo RTSP del fabricante:
   - **Hikvision / Hilook:** `rtsp://admin:clave@192.168.1.100:554/Streaming/Channels/101`
   - **Dahua:** `rtsp://admin:clave@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0`
   - **Cámara USB Local:** Seleccione `Webcam USB` e ingrese el índice numérico (`0`, `1`, etc.).
5. Presione **«Guardar / Activar Cámara»**. El sistema iniciará la captura y aplicará los detectores correspondientes.

> [!NOTE]
> La aplicación utiliza internamente el transporte TCP en FFmpeg (`rtsp_transport;tcp`) para evitar el pixelado y la pérdida de cuadros habitual en conexiones UDP.

---

### 3. Copias de Seguridad (Backup) y Restauración
Para salvaguardar la configuración y los datos históricos ante cambios de equipo o mantenimiento:

1. **Crear Copia de Seguridad:**
   - En la Pestaña 3, presione **«Descargar Backup de Ajustes y DB (JSON)»**.
   - Elija la carpeta de destino (ejemplo: disco externo o pendrive).
   - El sistema generará un archivo `.json` que incluye un código de autenticidad criptográfico SHA-256 (`checksum_sha256`).
2. **Restaurar Copia:**
   - Presione **«Restaurar Configuración desde Copia»**.
   - Seleccione el archivo JSON previamente exportado.
   - El sistema comprobará primero la integridad del archivo. Si el archivo fue alterado o está corrupto, la restauración se cancelará para proteger la base de datos. Si es válido, se aplicarán todas las cámaras y configuraciones previas.

---

### 4. Ubicación de Archivos de Datos y Persistencia
Los datos del usuario se conservan separados de la carpeta de instalación:
- **Base de datos SQLite:** `C:\Users\<Usuario>\.vigiwinpro\vigiwin.db`
- **Carpeta de Evidencias Forenses:** `C:\Users\<Usuario>\.vigiwinpro\snapshots\`
- **Carpeta de Backups Locales:** `C:\Users\<Usuario>\.vigiwinpro\backups\`
- Toda la base de datos y evidencias fotográficas sobreviven a actualizaciones, reinicios de Windows y reinstalaciones del ejecutable.

---

### 5. Compilación del Ejecutable Autónomo (.exe)
Para generar el ejecutable empaquetado para distribución:
1. Ejecute el script `installer\build.bat` en una consola con privilegios normales de Windows.
2. El script comprobará dependencias mediante `installer\bootstrap.py` y compilará la aplicación con PyInstaller utilizando `VigiWinPro.spec`.
3. El ejecutable autónomo y todos sus módulos se depositarán en: `dist\VigiWinPro\VigiWinPro.exe`.
4. Para generar el instalador de instalación guiada para clientes finales, abra `installer\installer_script.iss` en Inno Setup y compile.
