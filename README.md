# 🚀 ProjectTeam 100

## Plan de Proyecto con Equipo Multidisciplinario Inteligente

ProjectTeam 100 es una aplicación que utiliza inteligencia artificial para generar planes de proyecto completos con equipos multidisciplinarios optimizados. Basándose en la descripción de tu proyecto, la IA selecciona automáticamente los profesionales necesarios y genera un plan detallado paso a paso.

---

## ✨ Características

### 🎯 Análisis Inteligente
- Preguntas de clarificación personalizadas según tu proyecto
- Sistema de preguntas una por una para máxima precisión

### 👥 Equipo Multidisciplinario Automático
- Selección automática de profesionales según el tipo de proyecto
- Perfiles detallados con habilidades, experiencia y responsabilidades
- Porcentaje de dedicación sugerido por rol

### 📄 PDF Profesional
- Portada elegante con información del proyecto
- Índice navegable
- Marca de agua "ProjectTeam 100"
- Diseño moderno con colores profesionales

### 📊 Contenido del Plan
| Sección | Descripción |
|---------|-------------|
| Resumen Ejecutivo | Visión general del proyecto |
| Equipo Asignado | Profesionales con roles y habilidades |
| Objetivos y Alcance | Qué incluye y qué no incluye |
| Fases del Proyecto | Paso a paso detallado |
| Recursos Necesarios | Humanos, técnicos e infraestructura |
| Análisis de Riesgos | Identificación y mitigación |
| Métricas de Éxito | KPIs para medir el progreso |
| Recomendaciones | Consejos del equipo experto |
| **[Opcional]** Costos | Proyección de presupuesto en USD |
| **[Opcional]** Cronograma | Tiempos y ruta crítica |

### ⚙️ Niveles de Detalle
- **Básico**: Overview general
- **Detallado**: Paso a paso con entregables
- **Ultra-Detallado**: Sub-tareas, responsables y dependencias

### 🌍 Multiidioma y Multiregión
- Español e Inglés
- 7 regiones: Latinoamérica, Norteamérica, Europa, Asia, África, Oceanía, Global

---

## 📁 Estructura del Proyecto

```
projectteam_100/
├── app.py              ← Servidor Flask principal
├── project_engine.py   ← Motor de análisis y generación
├── pdf_generator.py    ← Generador de PDF profesional
├── email_sender.py     ← Módulo de envío de emails
├── config.py           ← Configuración y constantes
├── requirements.txt    ← Dependencias Python
├── .env.example        ← Ejemplo de variables de entorno
├── .env                ← Tu configuración (créalo tú)
└── templates/
    └── index.html      ← Interfaz web moderna
```

---

## 🔧 Instalación

### 1. Crea la carpeta del proyecto
```bash
mkdir projectteam_100
cd projectteam_100
```

### 2. Coloca todos los archivos en la estructura indicada

### 3. Crea el archivo `.env`
```bash
cp .env.example .env
```

Edita `.env` y agrega tu API key:
```
ANTHROPIC_API_KEY=tu-api-key-aqui
```

### 4. Crea un entorno virtual e instala dependencias
```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Ejecuta la aplicación
```bash
python app.py
```

### 6. Abre en el navegador
```
http://localhost:5000
```

---

## 📧 Configuración de Email (Opcional)

Para enviar PDFs por email, configura las credenciales SMTP en `.env`:

### Para Gmail:
1. Activa la verificación en 2 pasos en tu cuenta de Google
2. Ve a: https://myaccount.google.com/apppasswords
3. Genera una contraseña de aplicación para "Mail"
4. Configura en `.env`:

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password-de-16-caracteres
```

**Nota**: Si no configuras el email, el PDF aún se puede descargar directamente.

---

## 🎮 Cómo Usar

### Paso 1: Datos Iniciales
- Nombre del proyecto
- Descripción detallada
- Industria
- Ubicación
- Región de enfoque

### Paso 2: Preguntas de Clarificación
- Responde 5 preguntas generadas por IA
- Cada respuesta mejora la precisión del plan
- Las preguntas son específicas para tu proyecto

### Paso 3: Opciones del Plan
- Selecciona nivel de detalle (Básico/Detallado/Ultra)
- Marca si quieres proyección de costos
- Marca si quieres cronograma
- Ingresa tu email

### Paso 4: Resultado
- Descarga el PDF profesional
- Recíbelo por email (si configuraste SMTP)
- Inicia un nuevo proyecto

---

## 💡 Ejemplos de Uso

### Proyecto de Software
```
Nombre: App de Gestión de Inventarios
Descripción: Desarrollar una aplicación web para pequeñas empresas que permita
controlar inventarios, generar reportes y alertas de stock bajo.
Industria: Tecnología / Software
Ubicación: Madrid, España
Región: Europa
```

### Proyecto de Negocio
```
Nombre: Cadena de Cafeterías Especiales
Descripción: Abrir una cadena de 5 cafeterías con concepto de café de
especialidad en zonas premium de la ciudad.
Industria: Alimentos y Bebidas
Ubicación: Ciudad de México
Región: Latinoamérica
```

### Proyecto de Marketing
```
Nombre: Campaña de Lanzamiento Producto
Descripción: Campaña integral de marketing digital para el lanzamiento de
una nueva línea de productos de skincare orgánico.
Industria: Marketing / Publicidad
Ubicación: Los Angeles, USA
Región: Norteamérica
```

---

## 🔌 API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Página principal |
| `/api/generate-questions` | POST | Genera preguntas de clarificación |
| `/api/submit-answer` | POST | Envía respuesta a una pregunta |
| `/api/generate-project` | POST | Genera el proyecto completo |
| `/api/generate-pdf` | POST | Genera el PDF y envía por email |
| `/api/download-pdf/<session_id>` | GET | Descarga el PDF |

---

## 🛠️ Tecnologías

- **Backend**: Flask (Python)
- **IA**: Claude (Anthropic API)
- **PDF**: ReportLab
- **Frontend**: HTML5 + CSS3 + JavaScript (Vanilla)

---

## 📄 Licencia

Este proyecto es propietario. Todos los derechos reservados.

---

## 🤝 Soporte

Si encuentras algún problema:
1. Verifica que tu API key sea válida
2. Revisa que el archivo `.env` esté correctamente configurado
3. Asegúrate de tener todas las dependencias instaladas

---

**© 2024 ProjectTeam 100** - Plan de Proyecto con Equipo Multidisciplinario Inteligente 🚀
