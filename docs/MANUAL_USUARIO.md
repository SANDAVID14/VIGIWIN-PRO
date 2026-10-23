# MANUAL DE USUARIO - VIGI-WIN PRO v1.0
## Guía Completa de Operación para Personal de Seguridad y Operadores

---

### 1. Introducción
**VIGI-WIN PRO** es una aplicación diseñada para facilitar la vigilancia de accesos en tiempo real sin necesidad de conocimientos técnicos ni programación. Toda la interacción se realiza mediante botones, interruptores y controles visuales en español.

---

### 2. Cómo Iniciar la Aplicación y Autenticación (Login)
1. Haga doble clic en el acceso directo de **VIGI-WIN PRO** en el Escritorio o en `VigiWinPro.exe`.
2. **Pantalla de Inicio de Sesión (Login Modal):**
   - El sistema solicitará obligatoriamente usuario y contraseña antes de permitir el acceso.
   - Dispone de chips de acceso rápido (`👑 Admin`, `🛡️ Operador`, `📋 Auditor`) para cargar credenciales por defecto.
   - Botón con icono de ojo (`👁`) para alternar la visibilidad de la contraseña.
   - Detección de Bloqueo de Mayúsculas (Caps Lock) y confirmación con tecla Enter.
3. Una vez autenticado, se cargará la interfaz en modo oscuro Slate 950 con los privilegios correspondientes.

---

### 3. Conmutación en Caliente de Usuario («🔄 Cambiar Usuario»)
Sin necesidad de cerrar la aplicación ni interrumpir la grabación de cámaras:
1. En la barra superior (cabecera), presione el botón **«🔄 Cambiar Usuario»**.
2. Aparecerá el diálogo modal de conmutación. Ingrese las credenciales del nuevo usuario (o seleccione su chip).
3. Al pulsar **«Iniciar Sesión»**:
   - La sesión anterior se cierra limpiamente y se registra en la tabla de auditoría.
   - La nueva sesión toma vigencia al instante, actualizando el distintivo superior de usuario y rol.
   - Las pestañas y controles restringidos se adaptan de inmediato según la matriz de permisos.

---

### 4. Pestaña 1: Vigilancia en Directo y Modo Multi-Cámara

#### 4.1 Modos de Visualización (1x1 vs 2x2)
En la parte superior derecha de la vista de vídeo encontrará los conmutadores de cuadrícula:
- **«⏹ 1x1 Individual»:** Muestra la cámara seleccionada a gran tamaño con todos los controles operativos.
- **«⊞ 2x2 Cuadrícula»:** Muestra simultáneamente hasta 4 cámaras activas en tiempo real.
  - Cada cuadrante muestra el nombre de la cámara, estado (● EN LÍNEA / FALLO / ALERTA) y contador de FPS.
  - Al hacer **un clic** en cualquier recuadro, la cámara queda seleccionada con un marco brillante verde esmeralda y sus controles se sincronizan en el panel lateral.
  - Al hacer **doble clic** sobre cualquier recuadro en cuadrícula, la cámara se maximiza instantáneamente a modo **1x1 Individual**.

#### 4.2 Calibración y Temporizador de Puerta
- **Selección de Cámara:** Menú desplegable o selección interactiva en la cuadrícula.
- **Perspectiva:** Puede seleccionar entre **«Vista Frontal»** y **«Vista Lateral»** según el ángulo de instalación.
- **Marco ROI:** Permite encender o apagar la visualización de la zona de interés de detección.
- **Calibrar Cerrado:** Cuando la puerta esté completamente cerrada y despejada, presione el botón **«Calibrar Cerrado»** para establecer el 0% de variación de referencia.
- **Temporizador de Puerta:** Arriba a la derecha del cuadro de vídeo:
  - *Verde (00:00):* Puerta Cerrada.
  - *Ámbar (00:25):* Puerta Abierta.
  - *Rojo Pulsante (01:00):* ALARMA CRÍTICA (tiempo máximo superado).

---

### 5. Qué Hacer ante una Alerta
Cuando una puerta permanezca abierta más de 60 segundos (o el tiempo configurado), o se detecte una persona o vehículo:

1. **Alerta en Esquina Inferior Derecha:** Aparecerá una ventana flotante sobre la barra de tareas de Windows emitiendo un sonido de alarma, sin robar el foco de otras aplicaciones.
2. **Instantánea Forense Automática:** El sistema captura automáticamente una imagen `.jpg` del fotograma exacto con marca de agua pericial (fecha, hora, cámara y tipo de evento).
3. **Acciones Disponibles:**
   - **«Aceptar»:** Confirma que usted ha tomado conocimiento de la alerta. Quedará registrada la confirmación con fecha, hora y usuario en el historial.
   - **«Silenciar»:** Detiene el aviso acústico sin cerrar la alerta de inmediato.
   - **«Ver»:** Abre la pestaña de vigilancia para observar el evento en directo.

---

### 6. Aviso de Cierre de Puerta
Cuando la puerta sea cerrada:
- El temporizador se reiniciará inmediatamente a `00:00`.
- Se emitirá una campanada suave de confirmación.
- Aparecerá un cuadro de diálogo informando: *"La puerta ha sido cerrada correctamente. Tiempo total de apertura: XX segundos"*.
- Presione el botón **«Aceptar»** para validar el cierre y registrarlo en auditoría.

---

### 7. Interruptores Independientes de Personas y Vehículos
En el panel lateral derecho:
- **«Detectar Personas»:** Active o desactive la casilla según desee recibir alertas de personas. Al desactivarla, el indicador cambiará a `DESACTIVADO`.
- **«Detectar Vehículos»:** Active o desactive la casilla de vehículos de forma independiente.
- **Sensibilidad:** Deslice la barra entre 10% y 100% para afinar la sensibilidad de detección.
- **Tiempo Máximo Abierta:** Puede modificar el valor en segundos (por defecto 60 segundos / 1 minuto) para adaptarlo a las necesidades operativas de cada portón.

---

### 8. Pestaña 2: Historial, Evidencias Forenses y Exportación CSV
- **Registro Permanente:** Todos los eventos quedan guardados de forma permanente en SQLite con 8 columnas detalladas.
- **Columna Evidencia:** Los eventos con captura disponen de un distintivo **«📸 Ver Foto»**.
- **Panel Lateral de Vista Previa:** Al seleccionar cualquier evento, se muestra la miniatura de la captura con su fecha, tipo y resolución.
- **Inspección a Tamaño Completo:** Al hacer clic en **«Ver en Grande»** o en el distintivo de la tabla, se abre el visor forense modal a pantalla completa con opción de zoom y **«Guardar Como...»**.
- **Abrir Carpeta de Evidencias:** Botón directo **«📁 Abrir Carpeta»** para abrir en el Explorador de Windows la carpeta `~/.vigiwinpro/snapshots/`.
- **Búsqueda y Filtros:** Busque por texto libre o filtre por *Puerta, Persona, Vehículo, Fallo de Cámara o Sistema*.
- **Exportación CSV:** Genera una hoja de cálculo completa que incluye los enlaces a las evidencias fotográficas para auditorías legales o peritajes.
