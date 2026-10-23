# ARQUITECTURA TÉCNICA - VIGI-WIN PRO v1.0
## Sistema Inteligente de Vigilancia de Puertas, Personas y Vehículos para Windows 10 y Windows 11

---

### 1. Presentación Ejecutiva del Proyecto
**VIGI-WIN PRO v1.0** es una solución de escritorio profesional diseñada para la supervisión automatizada de accesos, puertas, portones y talanqueras, así como la detección desacoplada de personas y vehículos mediante cámaras conectadas a DVR/NVR o IP (protocolo RTSP sobre TCP) y cámaras USB locales.

El software está concebido para ser operado y administrado íntegramente mediante interfaces visuales amigables, garantizando que el propietario no requiera conocimientos de programación. Su arquitectura es 100% local, privada y autónoma, sin dependencias de servicios en la nube de pago ni necesidad de conectividad permanente a Internet.

---

### 2. Diagrama de Arquitectura Modular

```
+---------------------------------------------------------------------------------------+
|                                    CAPA DE PRESENTACIÓN (GUI)                        |
|                                         PySide6 (Qt)                                  |
|                                                                                       |
|  +--------------------+  +--------------------+  +--------------------+  +---------+  |
|  | Tab 1: Vigilancia  |  | Tab 2: Historial   |  | Tab 3: Admin/RBAC  |  | Tab 4/5:|  |
|  | en Directo         |  | y Evidencias (.jpg)|  | y Cámaras RTSP     |  | Código /|  |
|  | (Grid 2x2/1x1, ROI)|  | (Visor Fullscreen) |  | (Backup SHA-256)   |  | Tests 24|  |
|  +--------------------+  +--------------------+  +--------------------+  +---------+  |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | CONTROL DE SESIÓN Y LOGIN MODAL (LoginDialog)                                   |  |
|  | - Validación obligatoria al inicio (Admin, Operador, Auditor)                    |  |
|  | - Conmutación de usuario en caliente («🔄 Cambiar Usuario») sin reiniciar app    |  |
|  +---------------------------------------------------------------------------------+  |
|  | SISTEMA CENTRALIZADO DE ALERTAS PRIORITARIAS (CentralizedAlertOverlay)           |  |
|  | - Ventana flotante Topmost abajo a la derecha de Windows (Taskbar aware)         |  |
|  | - Non-Activating (WA_ShowWithoutActivating / No roba el foco de Word/Excel)      |  |
|  | - Captura automática de instantánea pericial (.jpg) con marca de agua            |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                              CAPA DE VISIÓN ARTIFICIAL (OpenCV)                       |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | CameraManager (Orquestador Multi-Cámara)                                        |  |
|  |  ├── CameraStream: Captura USB / RTSP (TCP) / Simulador sintético ~30 FPS        |  |
|  |  ├── DoorDetector:                                                              |  |
|  |  │     ├── Calibración de estado cerrado (Frontal / Lateral)                    |  |
|  |  │     ├── Variación estructural (Umbral >= 10% activa "Abierto")                |  |
|  |  │     ├── Validación temporal (Debounce multi-frame)                           |  |
|  |  │     ├── Temporizador de tiempo real (Inicial 60s / 1 min ajustable)          |  |
|  |  │     └── Detección de incertidumbre (Calidad lumínica / Oclusión)             |  |
|  |  └── ObjectDetector:                                                            |  |
|  |        ├── Módulo Personas: Switch independiente, Sensibilidad, ROI, Antispam    |  |
|  |        └── Módulo Vehículos: Switch independiente, Sensibilidad, ROI, Antispam   |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                               CAPA DE PERSISTENCIA Y CORE                             |
|                                                                                       |
|  +------------------------------------+  +-----------------------------------------+  |
|  | DatabaseManager (SQLite Local)     |  | BackupManager                           |  |
|  | - ~/.vigiwinpro/vigiwin.db         |  | - Volcado JSON + DB SQLite              |  |
|  | - Tablas: events, cameras,         |  | - Validación criptográfica SHA-256      |  |
|  |   settings, users, audit_log       |  | - Restauración y protección ante fallos |  |
|  +------------------------------------+  +-----------------------------------------+  |
|  +------------------------------------+  +-----------------------------------------+  |
|  | RBACManager                        |  | AudioManager (Windows Native winsound)  |  |
|  | - Roles: Admin, Operador, Auditor  |  | - Generación en memoria PCM sin wavs ext|  |
|  | - Contraseñas seguras SHA-256      |  | - Sirena crítica, Chimes y Avisos suaves|  |
|  +------------------------------------+  +-----------------------------------------+  |
+---------------------------------------------------------------------------------------+
```

---

### 3. Especificaciones de Módulos Principales

#### 3.1 Captura de Vídeo y Soporte RTSP (TCP)
Para evitar la pérdida masiva de fotogramas e interrupciones en flujos de cámaras IP y grabadores DVR/NVR, el módulo `CameraStream` configura explícitamente el protocolo de transporte TCP mediante la variable de entorno FFmpeg:
```python
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
```
Adicionalmente, dispone de un generador sintético parametrizado para permitir la verificación integral en entornos sin cámara física conectada.

#### 3.2 Algoritmo de Vigilancia de Puertas (10% de Variación y 60s)
1. **Calibración:** Almacena la firma estructural de bordes (`cv2.Canny`) y escala de grises de la zona delimitada (ROI) en la posición de reposo ("cerrado").
2. **Cálculo de Variación:** Compara el fotograma en curso con la referencia mediante diferencia de gradientes y correlación estructural, calculando un porcentaje $\Delta \in [0\%, 100\%]$.
3. **Umbral del 10%:** Si $\Delta \ge 10.0\%$, se produce la transición al estado "ABIERTO".
4. **Validación Temporal (Debouncing):** Se requieren 4 fotogramas consecutivos (~130 ms) confirmando el estado para evitar falsos positivos por parpadeos de luces o artefactos de compresión.
5. **Temporizador en Tiempo Real:** Utiliza `time.monotonic()` para medir el tiempo real transcurrido, con un valor inicial de 60 segundos (1 minuto) configurable por el usuario.
6. **Alarma y Cierre:** Si supera 60 segundos, activa la alarma visual y acústica prioritaria. Al detectar el cierre de la puerta, emite un aviso en pantalla que requiere pulsar «Aceptar» y registra el ciclo completo en auditoría.
7. **Incertidumbre:** Si el contraste es casi nulo o los niveles de luminosidad son extremos (< 15 o > 240), el sistema declara estado de "INCERTIDUMBRE" en lugar de emitir falsos juicios.

#### 3.3 Detección Desacoplada de Personas y Vehículos
- Cada cámara cuenta con interruptores independientes (`chk_person`, `chk_vehicle`).
- Desactivar la detección de personas no altera el funcionamiento de vehículos ni el temporizador de puerta.
- Incorpora filtrado espacial por ROI, persistencia mínima (1.0s) antes de generar alarma, y período de enfriamiento (cooldown antispam de 15s) para impedir alertas repetitivas por la misma presencia continua.

#### 3.4 Sistema Centralizado de Alertas Flotantes Topmost
- Ubicado en la esquina inferior derecha de la pantalla principal, calculando el área de trabajo de Windows descontando la barra de tareas (`QApplication.primaryScreen().availableGeometry()`).
- Emplea los atributos `Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus` y `WA_ShowWithoutActivating` para permitir que el usuario continúe escribiendo en procesadores de texto, hojas de cálculo o navegadores web sin perder el foco del teclado.

#### 3.5 Almacenamiento y Estampado Forense de Instantáneas (Snapshots JPG)
- En cada evento crítico (puerta superando umbral, persona o vehículo detectado), `CameraManager.save_snapshot()` procesa el fotograma exacto.
- Estampa una franja inferior semitransparente con tipografía antialiasing conteniendo: marca temporal ISO-8601, ID de cámara, tipo de evento y metadatos periciales.
- Guarda la evidencia en `~/.vigiwinpro/snapshots/` con compresión JPEG optimizada y registra la ruta absoluta en la columna `snapshot_path` de SQLite.
- Pestaña Historial integra visor lateral de miniaturas, apertura directa en Explorador de Windows y diálogo modal `SnapshotViewerDialog` con zoom interactivo.

#### 3.6 Modo Cuadrícula Multi-Cámara (Grid 2x2 / 1x1)
- Permite la monitorización concurrente de hasta 4 canales simultáneos (`QGridLayout` 2x2).
- Cada celda está encapsulada en un componente `CameraGridTile` con renderizado de vídeo, badge de estado (En Línea / Alerta / Desconectado) y contador de FPS.
- Selección interactiva con marco verde esmeralda y maximización fluida a modo individual (1x1) mediante doble clic.

#### 3.7 Autenticación Inicial y Conmutación en Caliente (RBAC)
- Diálogo modal `LoginDialog` ejecutado antes de la inicialización de la ventana principal (`main.py`).
- Soporte de conmutación en caliente («🔄 Cambiar Usuario») sin cierre de procesos ni interrupción de la captura de cámaras.
- Auditoría automática de inicio, cambio de turno y cierre de sesión con marca de tiempo precisa en la base de datos local.
