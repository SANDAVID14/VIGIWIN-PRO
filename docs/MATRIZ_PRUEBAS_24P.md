# MATRIZ DE PRUEBAS Y RESULTADOS (24 PUNTOS DE CONTROL)
## VIGI-WIN PRO v1.0 - Verificación Técnica Integral

---

### Resumen de Ejecución
- **Fecha de Verificación:** 21 de Octubre de 2026
- **Entorno de Prueba:** Windows 10 / Windows 11 (64-bit), Python 3.12.7
- **Herramientas:** `pytest 9.1.1`, Suite Diagnóstica Interactiva Interna
- **Total de Pruebas Automatizadas:** 43 Pruebas
- **Tasa de Aprobación:** 100% (43 Pasadas / 0 Fallidas)

---

### Matriz Detallada de los 24 Puntos de Control Obligatorios

| # | Punto de Control / Escenario | Módulo Validado | Criterio de Aceptación | Resultado |
| :---: | :--- | :--- | :--- | :---: |
| **1** | Permisos de usuario en `C:\Users` | Sistema Operativo | Capacidad de escritura en el directorio personal | **PASS** |
| **2** | Estructura de directorio `~/.vigiwinpro` | `config.py` | Creación automática de carpeta protegida y subcarpeta `backups/` | **PASS** |
| **3** | Conexión a Base de Datos SQLite | `database.py` | Apertura de conexión SQLite válida a `vigiwin.db` | **PASS** |
| **4** | Esquema de tabla `events` | `database.py` | Clave primaria autoincremental y campos de auditoría | **PASS** |
| **5** | Esquema de tabla `settings` | `database.py` | Persistencia clave-valor JSON de configuración | **PASS** |
| **6** | Módulo `PySide6.QtWidgets` en Windows | GUI Framework | Inicialización de QApplication y widgets Qt | **PASS** |
| **7** | Importación de OpenCV y códecs | `cv2` | Acceso a captura de vídeo, transformaciones y códecs | **PASS** |
| **8** | Módulo de cálculo matricial NumPy | `numpy` | Procesamiento de arrays multidimensionales de imagen | **PASS** |
| **9** | DatabaseManager con fallback | `database.py` | Auto-creación de tablas y fallback de directorio | **PASS** |
| **10** | Módulo `CentralizedAlertOverlay` | `alert_overlay.py` | Ventana flotante Topmost e interfaz gráfica | **PASS** |
| **11** | Script de auto-reparación (`bootstrap.py`) | `installer/bootstrap.py`| Validación e instalación desatendida de componentes | **PASS** |
| **12** | Motor de captura a 30 FPS | `camera_stream.py` | Generación e ingestión estable de fotogramas | **PASS** |
| **13** | Selector de perspectiva (Frontal / Lateral) | `door_detector.py` | Conmutación de algoritmos de proyección angular | **PASS** |
| **14** | Superposición de delimitación ROI | `camera_manager.py` | Marcado visual punteado de la zona de interés | **PASS** |
| **15** | Switch independiente de Personas | `object_detector.py` | Desactivar personas no afecta vehículos ni puertas | **PASS** |
| **16** | Switch independiente de Vehículos | `object_detector.py` | Desactivar vehículos no afecta personas ni puertas | **PASS** |
| **17** | Temporizador del sensor de puerta | `door_detector.py` | Medición en segundos reales transcurridos | **PASS** |
| **18** | Alarma crítica a 60 segundos (1 minuto) | `door_detector.py` | Disparo de estado de alarma al superar umbral | **PASS** |
| **19** | Superposición Taskbar (sin robar foco) | `alert_overlay.py` | `WA_ShowWithoutActivating` y posicionamiento abajo a la derecha | **PASS** |
| **20** | Registro automático de auditoría | `database.py` | Registro de inserción, confirmación y cambios en `audit_log` | **PASS** |
| **21** | Exportación de registros en CSV | `database.py` | Generación de archivo `.csv` con formato UTF-8 con BOM | **PASS** |
| **22** | Compatibilidad Inno Setup (`.iss`) | `installer_script.iss` | Script de compilador de instalador nativo Windows | **PASS** |
| **23** | Compilador batch de PyInstaller | `build.bat` | Automatización de construcción del ejecutable | **PASS** |
| **24** | Empaquetado autónomo ejecutable | `vigiwin_installer.py` | Asistente de instalación gráfica autónomo | **PASS** |

---

### Verificación de Casos Especiales

1. **Variación de Posición de al menos 10%:**
   - La prueba unitaria `test_door_open_variation_threshold_10pct` demostró que desplazamientos estructurales superiores al 10% provocan inmediatamente el cambio de estado a `"ABIERTO"`.
2. **Restablecimiento y Aviso de Cierre:**
   - La prueba `test_door_closure_detection_and_reset` comprobó que al retornar a la posición de referencia, el temporizador vuelve a `00:00` y se genera el evento `just_closed=True`, abriendo el diálogo con botón «Aceptar».
3. **Condiciones Lumínicas e Incertidumbre:**
   - La prueba `test_door_uncertainty_handling` verificó que si la cámara se tapa o la imagen es completamente negra, el sistema declara `"INCERTIDUMBRE"` y no afirma falsamente que la puerta esté abierta o cerrada.
