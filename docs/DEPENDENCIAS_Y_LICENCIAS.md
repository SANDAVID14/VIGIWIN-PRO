# DEPENDENCIAS, LICENCIAS Y REQUISITOS DE HARDWARE
## VIGI-WIN PRO v1.0 - Evaluación Técnico-Legal y Compatibilidad

---

### 1. Evaluación de Dependencias y Licencias
Todo el software ha sido diseñado utilizando componentes de código abierto con licencias permisivas comerciales, asegurando que el propietario tenga plena propiedad y derecho de uso sin incurrir en regalías, suscripciones recurrentes ni violaciones de copyright:

| Componente / Librería | Versión Probada | Licencia de Distribución | Impacto / Restricciones |
| :--- | :--- | :--- | :--- |
| **Python** | 3.12.7 / 3.8+ | Python Software Foundation License (PSFL) | Gratuita, código abierto, apta para uso comercial sin cánones. |
| **PySide6 (Qt for Python)** | 6.12.0 / 6.5+ | GNU Lesser General Public License v3 (LGPLv3) | Permite distribución comercial mediante enlace dinámico sin obligar a abrir el código del software propietario. |
| **OpenCV (opencv-python)** | 5.0.0.93 / 4.8+ | Apache License 2.0 | Gratuita, permisiva, procesamiento de visión artificial local sin conexión. |
| **NumPy** | 2.5.4 / 1.24+ | BSD 3-Clause License | Permisiva, sin restricciones para cálculos matriciales locales. |
| **SQLite3** | Integrado | Dominio Público (Public Domain) | Almacenamiento local ultraligero y robusto sin servidor ni mantenimiento. |
| **PyInstaller** | 6.22.3 | GPLv2 con Excepción Especial de Empaquetado | Permite empaquetar aplicaciones propietarias sin exigir licencia GPL al ejecutable final. |
| **Inno Setup** | 6.x | Jordan Russell License (Similar a BSD) | Software libre para creación de instaladores `.exe` comerciales en Windows. |

> [!IMPORTANT]
> **Sin Servicios de Pago ni Telemetría Externa:**
> VIGI-WIN PRO no realiza llamadas a APIs externas de pago, no transmite imágenes a la nube y funciona 100% desconectado de Internet.

---

### 2. Requisitos Mínimos y Recomendados de Hardware

#### Requisitos Mínimos (1 a 2 Cámaras)
- **Sistema Operativo:** Windows 10 (64-bit, versión 1909 o superior) o Windows 11.
- **Procesador (CPU):** Intel Core i3 (4ª generación o superior) o AMD Ryzen 3 / equivalente a 2.0 GHz.
- **Memoria RAM:** 4 GB de memoria física.
- **Almacenamiento:** 500 MB de espacio libre en disco para la aplicación y base de datos de eventos.
- **Cámaras Soportadas:** Cualquier cámara web USB compatible con Windows UVC o cámara IP / NVR que emita flujo de vídeo RTSP H.264.

#### Requisitos Recomendados (4 a 8 Cámaras Simultáneas)
- **Sistema Operativo:** Windows 10 / Windows 11 (64-bit).
- **Procesador (CPU):** Intel Core i5 / i7 (8ª generación o superior) o AMD Ryzen 5 / 7.
- **Memoria RAM:** 8 GB o 16 GB de RAM.
- **Almacenamiento:** Disco de estado sólido (SSD) con 2 GB libres para histórico prolongado de auditoría.
- **Red:** Conexión cableada Ethernet Gigabit (1000 Mbps) para el enlace con DVR/NVR mediante switches PoE.
