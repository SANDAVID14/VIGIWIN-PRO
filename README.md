# VIGI-WIN PRO v1.0
## Sistema Inteligente de Vigilancia de Puertas, Personas y Vehículos para Windows 10 y Windows 11

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20Qt-emerald.svg)](https://www.qt.io/)
[![Vision](https://img.shields.io/badge/Vision-OpenCV%205.0-red.svg)](https://opencv.org/)
[![Tests](https://img.shields.io/badge/Tests-62%2F62%20PASS-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20Owner-green.svg)]()

---

### Resumen del Proyecto
**VIGI-WIN PRO** es una aplicación de escritorio profesional en español desarrollada para Windows 10 (64-bit) y Windows 11. Proporciona vigilancia inteligente de accesos mediante cámaras USB y canales de grabadores DVR/NVR o IP mediante protocolo RTSP con transporte TCP.

### Características Principales
- **Página de Login y Conmutación de Usuario en Caliente (RBAC):**
  - Pantalla modal de autenticación segura obligatoria al iniciar la aplicación con validación SHA-256.
  - Botón **«🔄 Cambiar Usuario»** integrado en la cabecera superior para conmutar de operador o administrador sin cerrar ni salir del sistema.
  - Adaptación dinámica inmediata de permisos, menús y módulos bloqueados según el rol autenticado.
- **Modo Multi-Cámara Cuadrícula (Grid 2x2 / 1x1):**
  - Conmutador interactivo entre vista individual (1x1) y visualización simultánea de 4 canales (2x2).
  - Tarjetas de vídeo interactivas con estados en tiempo real (En línea, Alerta, Puerta Abierta/Cerrada).
  - Selección de canal activo con un clic y expansión instantánea a pantalla completa con doble clic.
- **Captura Forense Automática de Instantáneas (Snapshots JPG):**
  - Generación automática de instantáneas JPEG de alta resolución con franja forense estampada en cada alarma o detección.
  - Almacenamiento local seguro en `~/.vigiwinpro/snapshots/` con vinculación directa en SQLite.
  - Panel visor de evidencias en la pestaña Historial con inspección modal a tamaño completo y guardado independiente.
- **Vigilancia Inteligente de Puertas y Talanqueras:**
  - Calibración visual de referencia cerrada para perspectiva frontal y lateral.
  - Detección de variación de posición: si cambia al menos un **10%**, se declara el estado «Abierto».
  - Validación temporal para eliminar falsas alarmas por parpadeos o ruidos lumínicos.
  - Temporizador en tiempo real: valor inicial de **60 segundos (1 minuto)**, ajustable por el usuario en minutos o segundos.
  - Alarma prioritaria visual y sonora al superar el umbral consecutivo.
  - Aviso al detectar el cierre con botón **«Aceptar»** obligatorio y registro en auditoría.
  - Estado de «Incertidumbre» cuando las condiciones de iluminación u oclusión no permiten verificar el estado con confianza.
- **Detección Independiente de Personas y Vehículos:**
  - Interruptores independientes para activar o desactivar cada módulo por separado.
  - Desactivar personas no afecta vehículos ni puertas.
  - Sensibilidad configurable (10% a 100%), delimitación ROI, persistencia y cooldown antispam.
- **Sistema Centralizado de Alertas Prioritarias (Topmost):**
  - Ventana flotante en la esquina inferior derecha de Windows sobre la barra de tareas.
  - Mecanismo *non-activating* (`WA_ShowWithoutActivating`): no roba el foco del teclado ni interrumpe la escritura en Word, Excel o navegadores.
  - Botones de acción: «Aceptar», «Silenciar», «Ver» y generador de audio PCM integrado.
- **Diseño Gráfico Profesional Slate 950 + Emerald:**
  - Réplica fiel del diseño moderno, oscuro y estilizado del archivo `Backend vigiwin.html`.
  - 5 Pestañas: Vigilancia en Directo, Historial y Alertas, Administración y RBAC, Gestor de Código, y Suite de Tests (24 Puntos).
- **Persistencia y Seguridad Local:**
  - Base de datos SQLite local en `~/.vigiwinpro/vigiwin.db`.
  - Roles RBAC: Administrador, Operador y Auditor.
  - Copias de seguridad en formato JSON con validación criptográfica SHA-256.
  - Exportación de auditoría completa a CSV con rutas de evidencias fotográficas.

---

### Ejecución Rápida

#### 1. Iniciar la Aplicación Directamente
```powershell
python run_app.py
```

#### 2. Ejecutar la Suite de Pruebas Automatizadas (62 pruebas / 24 puntos)
```powershell
python -m pytest tests/ -v
```

#### 3. Ejecutar Verificación y Auto-Reparación
```powershell
python installer\bootstrap.py
```

#### 4. Asistente Gráfico de Instalación
```powershell
python installer\vigiwin_installer.py
```

#### 5. Compilar el Paquete con PyInstaller
```powershell
installer\build.bat
```

---

### Estructura del Proyecto
```
prueba 4 con antigravity/
├── vigiwin/                     # Paquete principal de la aplicación Python
│   ├── __init__.py
│   ├── main.py                 # Punto de entrada de la aplicación
│   ├── core/                   # Núcleo de persistencia, audio y seguridad
│   │   ├── config.py           # Configuración central y rutas ~/.vigiwinpro
│   │   ├── database.py         # Motor SQLite (events, cameras, settings, audit)
│   │   ├── audio.py            # Generador y reproductor de sonido PCM nativo Windows
│   │   ├── rbac.py             # Control de acceso basado en roles
│   │   └── backup.py           # Copias de seguridad con checksum SHA-256
│   ├── vision/                 # Motores de procesamiento de vídeo e IA local
│   │   ├── camera_stream.py    # Captura USB, RTSP (TCP) y simulador sintético ~30 FPS
│   │   ├── door_detector.py    # Detector de puertas (10% variación, 60s timer, debounce)
│   │   ├── object_detector.py  # Detección independiente de personas y vehículos
│   │   └── camera_manager.py   # Orquestador multi-cámara
│   └── ui/                     # Interfaces gráficas PySide6 (Tema Slate 950 + Emerald)
│       ├── styles.py           # Estilos QSS inspirados en Backend vigiwin.html
│       ├── main_window.py      # Ventana principal y barra superior
│       ├── login_dialog.py     # Diálogo modal de inicio de sesión y conmutación en caliente
│       ├── surveillance_tab.py # Pestaña 1: Vigilancia en directo, grid 2x2/1x1 y controles
│       ├── history_tab.py      # Pestaña 2: Historial, visor forense de evidencias y CSV
│       ├── admin_tab.py        # Pestaña 3: Roles RBAC, backup y cámaras RTSP
│       ├── code_tab.py         # Pestaña 4: Gestor de código y auto-repair
│       ├── tests_tab.py        # Pestaña 5: Suite de Tests 24P interactiva
│       ├── alert_overlay.py    # Ventana flotante Topmost abajo a la derecha
│       └── door_dialog.py      # Diálogo con botón «Aceptar» al cerrarse la puerta
├── tests/                      # Suite de pruebas con pytest (62 pruebas automatizadas)
│   ├── test_24_points_suite.py # Validación de los 24 puntos de control obligatorios
│   ├── test_camera_stream.py   # Pruebas de captura de vídeo y simulación
│   ├── test_database.py        # Pruebas de SQLite, persistencia y CSV
│   ├── test_door_detector.py   # Pruebas del algoritmo de puerta y temporizador
│   ├── test_object_detector.py # Pruebas de interruptores independientes y sensibilidad
│   ├── test_rbac_backup.py     # Pruebas de autenticación y backup SHA-256
│   ├── test_rbac_full.py       # Pruebas exhaustivas de RBAC, permisos y branding
│   ├── test_dvr_device_multicam.py # Pruebas de canales multi-cámara en grabadores DVR
│   ├── test_login_and_switch_user.py # Pruebas de inicio de sesión y cambio en caliente
│   └── test_snapshots_and_multicam.py # Pruebas de cuadrícula 2x2 y capturas forenses
├── installer/                  # Componentes de empaquetado e instalación
│   ├── bootstrap.py            # Script de auto-reparación e integridad
│   ├── build.bat               # Compilador batch PyInstaller
│   ├── vigiwin_installer.py    # Asistente gráfico de instalación para Windows
│   └── installer_script.iss    # Script para Inno Setup 6
├── docs/                       # Documentación profesional completa en español
│   ├── ARQUITECTURA.md         # Documento de arquitectura técnica y flujos
│   ├── MANUAL_USUARIO.md       # Manual de uso para personal no técnico
│   ├── MANUAL_ADMINISTRACION.md# Manual de administración, DVR/NVR y backups
│   ├── MATRIZ_PRUEBAS_24P.md   # Matriz de verificación empírica de 24 puntos
│   └── DEPENDENCIAS_Y_LICENCIAS.md # Licencias comerciales y requisitos hardware
├── Backend vigiwin.html        # Prototipo visual y de simulación web original
├── requirements.txt            # Dependencias del proyecto
├── run_app.py                  # Script lanzador directo
└── README.md                   # Este documento
```
