import os
import random
import io
import time
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_file
import anthropic
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import re

# =============================================================================
# CONFIGURACIÓN Y VARIABLES DE ENTORNO
# =============================================================================

# Cargar variables del archivo .env
load_dotenv()

# Configuración del modelo de IA
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-sonnet-4-20250514"
MAX_TOKENS = 500

# Inicializar cliente Anthropic
if ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    # Para desarrollo sin API key o primera ejecución
    client = None
    print("ADVERTENCIA: ANTHROPIC_API_KEY no encontrada. La IA no funcionará correctamente.")

# =============================================================================
# HTML TEMPLATE
# =============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIMULMARKET 100 - Massive AI Focus Group</title>
    <style>
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #ec4899;
            --background: #f8fafc;
            --surface: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        body {
            background-color: var(--background);
            color: var(--text-primary);
            line-height: 1.6;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Header */
        header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            z-index: 10;
        }

        .logo {
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .logo span {
            background: white;
            color: var(--primary);
            padding: 0.1rem 0.4rem;
            border-radius: 6px;
            font-size: 1rem;
        }

        .tagline {
            font-size: 0.9rem;
            opacity: 0.9;
            display: none;
        }

        @media (min-width: 768px) {
            .tagline { display: block; }
        }

        .status-badge {
            background: rgba(255, 255, 255, 0.2);
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .status-badge.active::before {
            content: '';
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            display: block;
            box-shadow: 0 0 8px #10b981;
        }

        /* Main Layout */
        main {
            display: flex;
            flex: 1;
            overflow: hidden;
        }

        /* Sidebar / Controls */
        .controls {
            width: 350px;
            background: var(--surface);
            border-right: 1px solid var(--border);
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            overflow-y: auto;
            flex-shrink: 0;
            z-index: 5;
        }

        .panel-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        label {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-secondary);
        }

        input, select, textarea {
            padding: 0.75rem;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.95rem;
            transition: all 0.2s;
            background: var(--background);
        }

        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
            background: white;
        }

        textarea {
            resize: vertical;
            min-height: 100px;
        }

        .range-container {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 1rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 0.5rem;
            font-size: 1rem;
        }

        .btn:hover {
            background: var(--primary-dark);
            transform: translateY(-1px);
        }

        .btn:disabled {
            background: var(--text-secondary);
            cursor: not-allowed;
            transform: none;
        }

        .btn-secondary {
            background: white;
            color: var(--primary);
            border: 1px solid var(--primary);
            margin-top: 0.5rem;
        }

        .btn-secondary:hover {
            background: #f0fdf4;
            transform: translateY(-1px);
        }

        .btn-secondary.hidden {
            display: none;
        }

        .btn-secondary.visible {
            display: flex;
        }

        .info-box {
            background: #eff6ff;
            border: 1px solid #dbeafe;
            border-radius: 8px;
            padding: 1rem;
            font-size: 0.85rem;
            color: #1e40af;
        }

        /* Visualization Area */
        .visualization {
            flex: 1;
            background: #f1f5f9;
            padding: 2rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .debate-container {
            width: 100%;
            max-width: 900px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 100%;
        }

        .debate-header {
            background: white;
            padding: 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 2;
        }

        .debate-title {
            font-size: 1.25rem;
            font-weight: 700;
        }

        .debate-stats {
            display: flex;
            gap: 1rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .stat {
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }

        .debate-content {
            padding: 2rem;
            overflow-y: auto;
            flex: 1;
            scroll-behavior: smooth;
        }

        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-secondary);
            text-align: center;
            padding: 2rem;
        }

        .empty-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }

        /* Messages */
        .message {
            margin-bottom: 1.5rem;
            animation: fadeIn 0.5s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message-header {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin-bottom: 0.5rem;
        }

        .avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: #e0e7ff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }

        .agent-name {
            font-weight: 700;
            font-size: 0.95rem;
        }

        .agent-number {
            background: var(--border);
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
            font-size: 0.7rem;
            color: var(--text-secondary);
        }

        .message-text {
            background: #f8fafc;
            padding: 1rem;
            border-radius: 0 12px 12px 12px;
            margin-left: 48px;
            border-left: 3px solid transparent;
            font-size: 0.95rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .round-divider {
            display: flex;
            align-items: center;
            margin: 2rem 0;
            color: var(--text-secondary);
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .round-divider::before, .round-divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border);
            margin: 0 1rem;
        }

        /* Resumen */
        .resumen {
            background: linear-gradient(to right, #f8fafc, #eff6ff);
            border: 1px solid #dbeafe;
            border-radius: 12px;
            padding: 2rem;
            margin-top: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }

        .resumen-title {
            font-size: 1.4rem;
            color: #1e40af;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .resumen-content {
            white-space: pre-line;
            font-size: 1rem;
        }

        /* Loading */
        .spinner {
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        @media (max-width: 900px) {
            main { flex-direction: column; overflow: auto; }
            .controls { width: 100%; border-right: none; border-bottom: 1px solid var(--border); }
            .visualization { padding: 1rem; }
        }
    </style>
</head>
<body>
    <header>
        <div class="logo">
            🤖 SIMUL<span>MARKET</span> 100
        </div>
        <div class="tagline" id="tagline">Massive AI Focus Group Simulator</div>
        <div class="status-badge" id="status-badge">Ready</div>
    </header>

    <main>
        <aside class="controls">
            <div class="panel-title">
                <span id="panel-title">⚙️ Configuration</span>
            </div>

            <div class="form-group">
                <label for="idioma" id="label-idioma">Idioma / Language</label>
                <select id="idioma">
                    <option value="es">Español</option>
                    <option value="en">English</option>
                </select>
            </div>

            <div class="form-group">
                <label for="producto">Producto / Servicio</label>
                <textarea id="producto" placeholder="Describe tu producto aquí. Ej: Una app de delivery de comida saludable por suscripción mensual..."></textarea>
            </div>

            <div class="form-group">
                <label for="region" id="label-region">Región del Panel</label>
                <select id="region">
                    {% for key, val in regiones.items() %}
                    <option value="{{ key }}">{{ val.nombre }} / {{ val.nombre_en }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="form-group">
                <label for="cantidad_agentes" id="label-agentes">Cantidad de Agentes (10-100)</label>
                <div class="range-container">
                    <input type="range" id="cantidad_agentes" min="10" max="100" step="10" value="30" oninput="this.nextElementSibling.value = this.value">
                    <output>30</output>
                </div>
            </div>

            <div class="form-group">
                <label for="rondas" id="label-rondas">Rondas de Debate (2-5)</label>
                <div class="range-container">
                    <input type="range" id="rondas" min="2" max="5" value="3" oninput="this.nextElementSibling.value = this.value">
                    <output>3</output>
                </div>
            </div>

            <div class="info-box">
                <span id="tiempo-estimado">⏱️ ~2 min</span>
            </div>

            <button id="btn-iniciar" class="btn">
                🎭 Iniciar Focus Group
            </button>

            <button id="btn-pdf" class="btn btn-secondary hidden">
                📥 Descargar Informe PDF
            </button>
        </aside>

        <section class="visualization">
            <div class="debate-container">
                <div class="debate-header">
                    <div class="debate-title" id="debate-title">Sala de Debate</div>
                    <div class="debate-stats">
                        <div class="stat">👥 <span id="stat-agentes">0</span></div>
                        <div class="stat">💬 <span id="stat-msgs">0</span></div>
                    </div>
                </div>
                <div class="debate-content" id="debate-content">
                    <div class="empty-state">
                        <span class="empty-icon">👋</span>
                        <p id="empty-text">Describe tu producto y haz clic en<br><strong>"Iniciar Focus Group"</strong></p>
                    </div>
                </div>
            </div>
        </section>
    </main>

    <script>
        const btnIniciar = document.getElementById('btn-iniciar');
        const btnPdf = document.getElementById('btn-pdf');
        const productoInput = document.getElementById('producto');
        const cantidadSelect = document.getElementById('cantidad_agentes');
        const rondasSelect = document.getElementById('rondas');
        const regionSelect = document.getElementById('region');
        const idiomaSelect = document.getElementById('idioma');
        const debateContent = document.getElementById('debate-content');
        const statusBadge = document.getElementById('status-badge');
        const tiempoSpan = document.getElementById('tiempo-estimado');

        const textos = {
            es: {
                tagline: "Simulador Masivo de Focus Group con IA",
                panelTitle: "⚙️ Configuración",
                placeholder: "Describe tu producto aquí. Ej: Una app de delivery de comida saludable...",
                idioma: "Idioma / Language",
                region: "Región del Panel",
                agentes: "Cantidad de Agentes (10-100)",
                rondas: "Rondas de Debate (2-5)",
                debateTitle: "Sala de Debate",
                esperando: "Listo",
                emptyText: 'Describe tu producto y haz clic en<br><strong>"Iniciar Focus Group"</strong>',
                btnIniciar: "🎭 Iniciar Focus Group",
                btnAnalizando: "Analizando...",
                enProgreso: "En progreso...",
                error: "Error",
                consultando: "Consultando a",
                profesionales: "profesionales de",
                rondasDe: "rondas de debate",
                debatieron: "profesionales debatieron en",
                rondas2: "rondas",
                resumenTitulo: "📊 Resumen Ejecutivo",
                tiempo: "min",
                opiniones: "opiniones",
                btnPdf: "📥 Descargar Informe PDF",
                btnPdfDescargando: "Generando PDF..."
            },
            en: {
                tagline: "Massive AI Focus Group Simulator",
                panelTitle: "⚙️ Configuration",
                placeholder: "Describe your product here. Ex: A healthy food delivery app...",
                idioma: "Language",
                region: "Panel Region",
                agentes: "Number of Agents (10-100)",
                rondas: "Debate Rounds (2-5)",
                debateTitle: "Debate Room",
                esperando: "Ready",
                emptyText: 'Describe your product and click<br><strong>"Start Focus Group"</strong>',
                btnIniciar: "🎭 Start Focus Group",
                btnAnalizando: "Analyzing...",
                enProgreso: "In progress...",
                error: "Error",
                consultando: "Consulting",
                profesionales: "professionals from",
                rondasDe: "rounds of debate",
                debatieron: "professionals debated in",
                rondas2: "rounds",
                resumenTitulo: "📊 Executive Summary",
                tiempo: "min",
                opiniones: "opiniones",
                btnPdf: "📥 Download PDF Report",
                btnPdfDescargando: "Generating PDF..."
            }
        };

        const regionNames = {
            es: {
                'global': '🌐 Global',
                'latam': '🌎 Latinoamérica',
                'norteamerica': '🇺🇸 Norteamérica',
                'europa': '🇪🇺 Europa',
                'asia': '🌏 Asia',
                'africa': '🌍 África',
                'oceania': '🦘 Oceanía'
            },
            en: {
                'global': '🌐 Global',
                'latam': '🌎 Latin America',
                'norteamerica': '🇺🇸 North America',
                'europa': '🇪🇺 Europe',
                'asia': '🌏 Asia',
                'africa': '🌍 Africa',
                'oceania': '🦘 Oceania'
            }
        };

        function cambiarIdioma() {
            const idioma = idiomaSelect.value;
            const t = textos[idioma];

            document.getElementById('tagline').textContent = t.tagline;
            document.getElementById('panel-title').textContent = t.panelTitle;
            productoInput.placeholder = t.placeholder;
            document.getElementById('label-idioma').textContent = t.idioma;
            document.getElementById('label-region').textContent = t.region;
            document.getElementById('label-agentes').textContent = t.agentes;
            document.getElementById('label-rondas').textContent = t.rondas;
            document.getElementById('debate-title').textContent = t.debateTitle;
            statusBadge.textContent = t.esperando;
            document.getElementById('empty-text').innerHTML = t.emptyText;
            btnIniciar.innerHTML = t.btnIniciar;
            btnPdf.innerHTML = t.btnPdf;

            actualizarTiempo();
        }

        function actualizarTiempo() {
            const idioma = idiomaSelect.value;
            const t = textos[idioma];
            const agentes = parseInt(cantidadSelect.value);
            const rondas = parseInt(rondasSelect.value);
            const total = agentes * rondas;
            const minutos = Math.max(1, Math.ceil(total * 0.5 / 60));
            const minutosMax = Math.ceil(total * 1 / 60);
            tiempoSpan.textContent = '~' + minutos + '-' + minutosMax + ' ' + t.tiempo + ' (' + total + ' ' + t.opiniones + ')';
        }

        idiomaSelect.addEventListener('change', cambiarIdioma);
        cantidadSelect.addEventListener('change', actualizarTiempo);
        rondasSelect.addEventListener('change', actualizarTiempo);
        actualizarTiempo();

        btnIniciar.addEventListener('click', async () => {
            const producto = productoInput.value.trim();
            const cantidad = parseInt(cantidadSelect.value);
            const rondas = parseInt(rondasSelect.value);
            const region = regionSelect.value;
            const idioma = idiomaSelect.value;
            const t = textos[idioma];

            if (!producto) {
                alert(idioma === 'es' ? 'Por favor, describe tu producto primero' : 'Please describe your product first');
                return;
            }

            btnIniciar.disabled = true;
            btnIniciar.innerHTML = '<span class="spinner"></span> ' + t.btnAnalizando;
            statusBadge.textContent = t.enProgreso;
            statusBadge.classList.add('active');
            btnPdf.classList.remove('visible');

            const regionNombre = regionNames[idioma][region];

            debateContent.innerHTML = '<div class="empty-state"><span class="empty-icon">🤔</span><p>' + t.consultando + ' ' + cantidad + ' ' + t.profesionales + ' ' + regionNombre + '...<br><small>' + rondas + ' ' + t.rondasDe + '</small></p></div>';

            try {
                const response = await fetch('/iniciar-debate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        producto: producto,
                        cantidad_agentes: cantidad,
                        rondas: rondas,
                        region: region,
                        idioma: idioma
                    })
                });

                const data = await response.json();

                if (data.success) {
                    mostrarDebate(data.debate, data.resumen, data.total_agentes, data.total_rondas, data.region, idioma);
                    statusBadge.textContent = data.region + ' ✓';
                    statusBadge.classList.remove('active');

                    // Mostrar botón de PDF
                    btnPdf.classList.add('visible');
                    btnPdf.innerHTML = t.btnPdf;
                } else {
                    throw new Error(data.error);
                }

            } catch (error) {
                debateContent.innerHTML = '<div class="empty-state"><span class="empty-icon">❌</span><p>' + t.error + ': ' + error.message + '</p></div>';
                statusBadge.textContent = t.error;
                statusBadge.classList.remove('active');
            }

            btnIniciar.disabled = false;
            btnIniciar.innerHTML = t.btnIniciar;
        });

        // Evento para descargar PDF
        btnPdf.addEventListener('click', async () => {
            const idioma = idiomaSelect.value;
            const t = textos[idioma];

            btnPdf.disabled = true;
            btnPdf.innerHTML = '<span class="spinner"></span> ' + t.btnPdfDescargando;

            try {
                const response = await fetch('/descargar-pdf');

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;

                    // Obtener nombre del archivo del header o usar uno por defecto
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = 'SimulMarket_Reporte.pdf';
                    if (contentDisposition) {
                        const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                        if (match && match[1]) {
                            filename = match[1].replace(/['"]/g, '');
                        }
                    }

                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                } else {
                    const data = await response.json();
                    throw new Error(data.error || 'Error al generar PDF');
                }
            } catch (error) {
                alert((idioma === 'es' ? 'Error al descargar PDF: ' : 'Error downloading PDF: ') + error.message);
            }

            btnPdf.disabled = false;
            btnPdf.innerHTML = t.btnPdf;
        });

        function mostrarDebate(mensajes, resumen, totalAgentes, totalRondas, regionNombre, idioma) {
            const t = textos[idioma];

            let html = '<p style="color: var(--text-secondary); margin-bottom: 1rem; font-size: 0.85rem;">📊 ' + totalAgentes + ' ' + t.debatieron + ' ' + totalRondas + ' ' + t.rondas2 + ' (' + regionNombre + '):</p>';

            let rondaActual = 0;

            for (let i = 0; i < mensajes.length; i++) {
                const msg = mensajes[i];

                if (msg.ronda !== rondaActual) {
                    rondaActual = msg.ronda;
                    const rondaTexto = idioma === 'es' ? 'Ronda' : 'Round';
                    const deTexto = idioma === 'es' ? 'de' : 'of';
                    html += '<div class="round-divider">🔄 ' + rondaTexto + ' ' + rondaActual + ' ' + deTexto + ' ' + totalRondas + '</div>';
                }

                html += '<div class="message">';
                html += '<div class="message-header">';
                html += '<div class="avatar" style="background: ' + msg.color + '22;">' + msg.emoji + '</div>';
                html += '<span class="agent-name" style="color: ' + msg.color + '">' + msg.nombre + '</span>';
                html += '<span class="agent-number">#' + msg.numero + '</span>';
                html += '</div>';
                html += '<div class="message-text" style="border-left-color: ' + msg.color + '">' + msg.texto + '</div>';
                html += '</div>';
            }

            if (resumen) {
                html += '<div class="resumen">';
                html += '<h3 class="resumen-title">' + t.resumenTitulo + ' - ' + regionNombre + '</h3>';
                html += '<div class="resumen-content">' + resumen + '</div>';
                html += '</div>';
            }

            debateContent.innerHTML = html;
            debateContent.scrollTop = 0;
        }
    </script>
</body>
</html>"""

# =============================================================================
# DATOS Y LÓGICA DE AGENTES
# =============================================================================

IDIOMAS = {
    "es": {
        "nombre": "Español",
        "instruccion": "Responde EN ESPAÑOL",
        "estilo": "Usa expresiones naturales en español"
    },
    "en": {
        "nombre": "English",
        "instruccion": "Respond IN ENGLISH",
        "estilo": "Use natural English expressions"
    }
}

REGIONES = {
    "global": {
        "nombre": "Global",
        "nombre_en": "Global",
        "descripcion": "Profesionales de todo el mundo"
    },
    "latam": {
        "nombre": "Latinoamérica",
        "nombre_en": "Latin America",
        "descripcion": "Profesionales de México, Centroamérica y Sudamérica"
    },
    "norteamerica": {
        "nombre": "Norteamérica",
        "nombre_en": "North America",
        "descripcion": "Profesionales de Estados Unidos y Canadá"
    },
    "europa": {
        "nombre": "Europa",
        "nombre_en": "Europe",
        "descripcion": "Profesionales de la Unión Europea y Reino Unido"
    },
    "asia": {
        "nombre": "Asia",
        "nombre_en": "Asia",
        "descripcion": "Profesionales de Asia Oriental, Sudeste Asiático e India"
    },
    "africa": {
        "nombre": "África",
        "nombre_en": "Africa",
        "descripcion": "Profesionales del continente africano"
    },
    "oceania": {
        "nombre": "Oceanía",
        "nombre_en": "Oceania",
        "descripcion": "Profesionales de Australia, Nueva Zelanda y el Pacífico"
    }
}

NOMBRES_POR_REGION = {
    "latam": {
        "masculinos": ["Carlos", "Miguel", "Juan", "Pedro", "Luis", "José", "Antonio", "Francisco",
                       "Alejandro", "Diego", "Santiago", "Mateo", "Sebastián", "Andrés", "Ricardo"],
        "femeninos": ["María", "Ana", "Carmen", "Laura", "Patricia", "Gabriela", "Valentina",
                      "Camila", "Sofía", "Isabella", "Fernanda", "Daniela", "Carolina", "Andrea", "Lucía"]
    },
    "norteamerica": {
        "masculinos": ["James", "John", "Michael", "David", "Robert", "William", "Richard",
                       "Joseph", "Thomas", "Christopher", "Charles", "Daniel", "Matthew", "Anthony", "Brian"],
        "femeninos": ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
                      "Jessica", "Sarah", "Karen", "Emily", "Ashley", "Kimberly", "Michelle", "Amanda"]
    },
    "europa": {
        "masculinos": ["Hans", "Pierre", "Giovanni", "Marco", "Stefan", "Erik", "Olivier",
                       "Henrik", "Lukas", "Matteo", "François", "Klaus", "Andreas", "Peter", "Sven"],
        "femeninos": ["Sophie", "Marie", "Anna", "Emma", "Giulia", "Ingrid", "Isabelle",
                      "Katarina", "Margot", "Elena", "Franziska", "Astrid", "Chiara", "Beatrice", "Helene"]
    },
    "asia": {
        "masculinos": ["Takeshi", "Wei", "Raj", "Hiroshi", "Chen", "Vikram", "Kenji",
                       "Ming", "Arjun", "Yuki", "Jin", "Sanjay", "Taro", "Huang", "Pradeep"],
        "femeninos": ["Yuki", "Mei", "Priya", "Sakura", "Lin", "Aisha", "Hana",
                      "Xia", "Deepa", "Akiko", "Jing", "Kavita", "Noriko", "Ying", "Ananya"]
    },
    "africa": {
        "masculinos": ["Kwame", "Oluwaseun", "Tendai", "Chidi", "Kofi", "Amara", "Tunde",
                       "Babatunde", "Emeka", "Sipho", "Jelani", "Adeolu", "Mandla", "Chinedu", "Olumide"],
        "femeninos": ["Amina", "Fatima", "Zara", "Chioma", "Aisha", "Nala", "Adaeze",
                      "Folake", "Thandiwe", "Nneka", "Wanjiku", "Adanna", "Lindiwe", "Ngozi", "Oluchi"]
    },
    "oceania": {
        "masculinos": ["Jack", "Oliver", "William", "Noah", "Liam", "Thomas", "James",
                       "Ethan", "Lucas", "Mason", "Harry", "Charlie", "Oscar", "Leo", "Archer"],
        "femeninos": ["Charlotte", "Olivia", "Amelia", "Isla", "Mia", "Ava", "Grace",
                      "Sophie", "Chloe", "Emily", "Ella", "Lily", "Ruby", "Zoe", "Harper"]
    }
}

CULTURA_POR_REGION = {
    "latam": {
        "contexto": "Latinoamérica",
        "contexto_en": "Latin America",
        "estilo_es": "Usa expresiones latinas como 'mira', 'fíjate que', 'la verdad es que'. Sé cálido y directo.",
        "estilo_en": "Use warm, relationship-focused communication style typical of Latin American professionals.",
        "valores": "relaciones personales, familia, flexibilidad, calidez"
    },
    "norteamerica": {
        "contexto": "Estados Unidos y Canadá",
        "contexto_en": "United States and Canada",
        "estilo_es": "Sé directo y orientado a resultados. Usa términos como 'ROI', 'bottom line', 'scalability'.",
        "estilo_en": "Be direct and results-oriented. Use terms like 'ROI', 'bottom line', 'scalability', 'game-changer'.",
        "valores": "eficiencia, resultados, innovación, datos"
    },
    "europa": {
        "contexto": "Europa",
        "contexto_en": "Europe",
        "estilo_es": "Equilibra pragmatismo con reflexión. Menciona regulaciones y sostenibilidad.",
        "estilo_en": "Balance pragmatism with deep reflection. Mention regulations, sustainability, and quality.",
        "valores": "calidad, sostenibilidad, regulación, equilibrio"
    },
    "asia": {
        "contexto": "Asia",
        "contexto_en": "Asia",
        "estilo_es": "Combina respeto por la tradición con visión de futuro. Piensa en largo plazo.",
        "estilo_en": "Combine respect for tradition with future vision. Think long-term and consider group harmony.",
        "valores": "armonía, largo plazo, tecnología, respeto"
    },
    "africa": {
        "contexto": "África",
        "contexto_en": "Africa",
        "estilo_es": "Combina optimismo emprendedor con pragmatismo. Piensa en soluciones innovadoras.",
        "estilo_en": "Combine entrepreneurial optimism with pragmatism. Think about innovative, mobile-first solutions.",
        "valores": "comunidad, resiliencia, innovación, emprendimiento"
    },
    "oceania": {
        "contexto": "Australia y Oceanía",
        "contexto_en": "Australia and Oceania",
        "estilo_es": "Sé relajado pero profesional. Valora autenticidad y equilibrio vida-trabajo.",
        "estilo_en": "Be relaxed but professional. Value authenticity, work-life balance, and sustainability.",
        "valores": "autenticidad, equilibrio, sostenibilidad, franqueza"
    },
    "global": {
        "contexto": "perspectiva global",
        "contexto_en": "global perspective",
        "estilo_es": "Combina perspectivas de diferentes culturas. Piensa en mercados internacionales.",
        "estilo_en": "Combine perspectives from different cultures. Think about international markets.",
        "valores": "diversidad, adaptabilidad, escalabilidad"
    }
}

PROFESIONES = {
    "es": [
        {"titulo": "Ingeniero/a de Software", "campo": "tecnología", "perspectiva": "analiza arquitectura técnica y escalabilidad"},
        {"titulo": "Médico/a", "campo": "salud", "perspectiva": "evalúa impacto en salud y evidencia científica"},
        {"titulo": "Abogado/a", "campo": "derecho", "perspectiva": "revisa términos legales y protección al consumidor"},
        {"titulo": "Contador/a Público", "campo": "finanzas", "perspectiva": "analiza estructura de costos y ROI"},
        {"titulo": "Director/a de Marketing", "campo": "marketing", "perspectiva": "evalúa posicionamiento y propuesta de valor"},
        {"titulo": "Gerente de Operaciones", "campo": "operaciones", "perspectiva": "analiza logística y eficiencia operativa"},
        {"titulo": "Psicólogo/a", "campo": "RRHH", "perspectiva": "evalúa comportamiento del consumidor"},
        {"titulo": "Chef Ejecutivo", "campo": "gastronomía", "perspectiva": "analiza calidad y presentación"},
        {"titulo": "Periodista", "campo": "medios", "perspectiva": "cuestiona afirmaciones y busca transparencia"},
        {"titulo": "Arquitecto/a", "campo": "diseño", "perspectiva": "evalúa diseño funcional y estética"},
        {"titulo": "Economista", "campo": "economía", "perspectiva": "analiza impacto de mercado y tendencias"},
        {"titulo": "Científico/a de Datos", "campo": "análisis", "perspectiva": "busca métricas y evidencia estadística"},
        {"titulo": "Director/a Financiero", "campo": "finanzas", "perspectiva": "evalúa modelo de negocio y riesgos"},
        {"titulo": "Consultor/a de Negocios", "campo": "consultoría", "perspectiva": "analiza ventaja competitiva"},
        {"titulo": "Gerente de Producto", "campo": "producto", "perspectiva": "evalúa product-market fit"},
        {"titulo": "Especialista UX/UI", "campo": "experiencia", "perspectiva": "analiza usabilidad y diseño"},
        {"titulo": "Emprendedor/a", "campo": "startups", "perspectiva": "evalúa oportunidad de mercado"},
        {"titulo": "Investigador/a", "campo": "I+D", "perspectiva": "busca innovación y evidencia"},
        {"titulo": "Director/a de RRHH", "campo": "talento", "perspectiva": "evalúa impacto organizacional"},
        {"titulo": "Analista de Riesgos", "campo": "riesgos", "perspectiva": "identifica amenazas potenciales"},
    ],
    "en": [
        {"titulo": "Software Engineer", "campo": "technology", "perspectiva": "analyzes technical architecture and scalability"},
        {"titulo": "Physician", "campo": "healthcare", "perspectiva": "evaluates health impact and scientific evidence"},
        {"titulo": "Attorney", "campo": "legal", "perspectiva": "reviews legal terms and consumer protection"},
        {"titulo": "CPA", "campo": "finance", "perspectiva": "analyzes cost structure and ROI"},
        {"titulo": "Marketing Director", "campo": "marketing", "perspectiva": "evaluates positioning and value proposition"},
        {"titulo": "Operations Manager", "campo": "operations", "perspectiva": "analyzes logistics and operational efficiency"},
        {"titulo": "Psychologist", "campo": "HR", "perspectiva": "evaluates consumer behavior"},
        {"titulo": "Executive Chef", "campo": "culinary", "perspectiva": "analyzes quality and presentation"},
        {"titulo": "Journalist", "campo": "media", "perspectiva": "questions claims and seeks transparency"},
        {"titulo": "Architect", "campo": "design", "perspectiva": "evaluates functional design and aesthetics"},
        {"titulo": "Economist", "campo": "economics", "perspectiva": "analyzes market impact and trends"},
        {"titulo": "Data Scientist", "campo": "analytics", "perspectiva": "seeks metrics and statistical evidence"},
        {"titulo": "CFO", "campo": "corporate finance", "perspectiva": "evaluates business model and risks"},
        {"titulo": "Business Consultant", "campo": "consulting", "perspectiva": "analyzes competitive advantage"},
        {"titulo": "Product Manager", "campo": "product", "perspectiva": "evaluates product-market fit"},
        {"titulo": "UX/UI Specialist", "campo": "experience", "perspectiva": "analyzes usability and design"},
        {"titulo": "Entrepreneur", "campo": "startups", "perspectiva": "evaluates market opportunity"},
        {"titulo": "Researcher", "campo": "R&D", "perspectiva": "seeks innovation and evidence"},
        {"titulo": "HR Director", "campo": "talent", "perspectiva": "evaluates organizational impact"},
        {"titulo": "Risk Analyst", "campo": "risk", "perspectiva": "identifies potential threats"},
    ]
}

PERSONALIDADES = {
    "es": [
        {"tipo": "Escéptico", "emoji": "🤨", "color": "#e74c3c", "comportamiento": "cuestiona todo, exige evidencia"},
        {"tipo": "Visionario", "emoji": "🚀", "color": "#27ae60", "comportamiento": "identifica potencial e innovación"},
        {"tipo": "Analítico", "emoji": "📊", "color": "#3498db", "comportamiento": "requiere datos y métricas"},
        {"tipo": "Pragmático", "emoji": "⚡", "color": "#f39c12", "comportamiento": "enfocado en resultados prácticos"},
        {"tipo": "Conservador", "emoji": "🛡️", "color": "#9b59b6", "comportamiento": "evalúa riesgos, prefiere lo probado"},
        {"tipo": "Estratégico", "emoji": "🎯", "color": "#1abc9c", "comportamiento": "piensa en largo plazo"},
        {"tipo": "Detallista", "emoji": "🔍", "color": "#34495e", "comportamiento": "examina cada aspecto"},
        {"tipo": "Orientado al ROI", "emoji": "💰", "color": "#f1c40f", "comportamiento": "todo debe justificarse económicamente"},
        {"tipo": "Innovador", "emoji": "💡", "color": "#2ecc71", "comportamiento": "busca disrupción"},
        {"tipo": "Centrado en Cliente", "emoji": "👥", "color": "#e67e22", "comportamiento": "prioriza experiencia del usuario"},
    ],
    "en": [
        {"tipo": "Skeptic", "emoji": "🤨", "color": "#e74c3c", "comportamiento": "questions everything, demands evidence"},
        {"tipo": "Visionary", "emoji": "🚀", "color": "#27ae60", "comportamiento": "identifies potential and innovation"},
        {"tipo": "Analytical", "emoji": "📊", "color": "#3498db", "comportamiento": "requires data and metrics"},
        {"tipo": "Pragmatic", "emoji": "⚡", "color": "#f39c12", "comportamiento": "focused on practical results"},
        {"tipo": "Conservative", "emoji": "🛡️", "color": "#9b59b6", "comportamiento": "evaluates risks, prefers proven solutions"},
        {"tipo": "Strategic", "emoji": "🎯", "color": "#1abc9c", "comportamiento": "thinks long-term"},
        {"tipo": "Detail-oriented", "emoji": "🔍", "color": "#34495e", "comportamiento": "examines every aspect"},
        {"tipo": "ROI-focused", "emoji": "💰", "color": "#f1c40f", "comportamiento": "everything must be economically justified"},
        {"tipo": "Innovator", "emoji": "💡", "color": "#2ecc71", "comportamiento": "seeks disruption"},
        {"tipo": "Customer-centric", "emoji": "👥", "color": "#e67e22", "comportamiento": "prioritizes user experience"},
    ]
}

NIVELES_EXPERIENCIA = {
    "es": [
        {"anos": 5, "nivel": "Senior"},
        {"anos": 8, "nivel": "Senior+"},
        {"anos": 10, "nivel": "Especialista"},
        {"anos": 12, "nivel": "Director"},
        {"anos": 15, "nivel": "Ejecutivo"},
        {"anos": 18, "nivel": "Consultor Senior"},
        {"anos": 20, "nivel": "Experto Principal"},
    ],
    "en": [
        {"anos": 5, "nivel": "Senior"},
        {"anos": 8, "nivel": "Senior+"},
        {"anos": 10, "nivel": "Specialist"},
        {"anos": 12, "nivel": "Director"},
        {"anos": 15, "nivel": "Executive"},
        {"anos": 18, "nivel": "Senior Consultant"},
        {"anos": 20, "nivel": "Principal Expert"},
    ]
}

def generar_agentes(cantidad=100, region="global", idioma="es"):
    agentes = {}
    random.seed(42)

    if region == "global":
        todos_masculinos = []
        todos_femeninos = []
        for reg in NOMBRES_POR_REGION.values():
            todos_masculinos.extend(reg["masculinos"])
            todos_femeninos.extend(reg["femeninos"])
        nombres_masculinos = todos_masculinos
        nombres_femeninos = todos_femeninos
        regiones_usar = list(CULTURA_POR_REGION.keys())
    else:
        nombres_masculinos = NOMBRES_POR_REGION.get(region, NOMBRES_POR_REGION["latam"])["masculinos"]
        nombres_femeninos = NOMBRES_POR_REGION.get(region, NOMBRES_POR_REGION["latam"])["femeninos"]
        regiones_usar = [region]

    cultura_base = CULTURA_POR_REGION.get(region, CULTURA_POR_REGION["global"])
    profesiones = PROFESIONES[idioma]
    personalidades = PERSONALIDADES[idioma]
    niveles = NIVELES_EXPERIENCIA[idioma]
    idioma_config = IDIOMAS[idioma]

    for i in range(cantidad):
        es_mujer = random.choice([True, False])
        nombre = random.choice(nombres_femeninos if es_mujer else nombres_masculinos)
        profesion = random.choice(profesiones)
        personalidad = random.choice(personalidades)
        experiencia = random.choice(niveles)

        if region == "global":
            cultura = CULTURA_POR_REGION[random.choice([r for r in regiones_usar if r != "global"])]
        else:
            cultura = cultura_base

        agente_id = f"agente_{i+1:03d}"

        if idioma == "es":
            nombre_completo = f"{nombre} - {profesion['titulo']} ({experiencia['anos']} años)"
            contexto = cultura["contexto"]
            estilo = cultura["estilo_es"]
        else:
            nombre_completo = f"{nombre} - {profesion['titulo']} ({experiencia['anos']} yrs)"
            contexto = cultura["contexto_en"]
            estilo = cultura["estilo_en"]

        if idioma == "es":
            sistema = f"""Eres {nombre}, {profesion['titulo']} con {experiencia['anos']} años de experiencia.

CONTEXTO CULTURAL: {contexto}

PERFIL PROFESIONAL:
- Nivel: {experiencia['nivel']}
- Especialidad: {profesion['campo']}
- Enfoque: {profesion['perspectiva']}

PERSONALIDAD ({personalidad['tipo']}):
- {personalidad['comportamiento']}

ESTILO: {estilo}

INSTRUCCIONES:
- {idioma_config['instruccion']}
- Sé breve pero contundente (2-3 oraciones)
- Habla como profesional experimentado
- Habla en primera persona"""
        else:
            sistema = f"""You are {nombre}, a {profesion['titulo']} with {experiencia['anos']} years of experience.

CULTURAL CONTEXT: {contexto}

PROFESSIONAL PROFILE:
- Level: {experiencia['nivel']}
- Specialty: {profesion['campo']}
- Focus: {profesion['perspectiva']}

PERSONALITY ({personalidad['tipo']}):
- {personalidad['comportamiento']}

STYLE: {estilo}

INSTRUCTIONS:
- {idioma_config['instruccion']}
- Be brief but impactful (2-3 sentences)
- Speak as an experienced professional
- Use first person"""

        agentes[agente_id] = {
            "nombre": nombre_completo,
            "emoji": personalidad["emoji"],
            "color": personalidad["color"],
            "sistema": sistema,
            "idioma": idioma
        }

    return agentes

# Inicializar agentes
AGENTES = generar_agentes(100, "global", "es")

def actualizar_agentes(cantidad=100, region="global", idioma="es"):
    global AGENTES
    random.seed()
    AGENTES = generar_agentes(cantidad, region, idioma)
    return AGENTES

def generar_respuesta_agente(agente_id, producto, historial):
    if not client:
        return "Error: No API Key configured"

    agente = AGENTES[agente_id]
    idioma = agente.get("idioma", "es")

    historial_reciente = historial[-3:] if len(historial) > 3 else historial

    if idioma == "es":
        contexto = ""
        if historial_reciente:
            contexto = "\n\nOPINIONES DE OTROS PROFESIONALES:\n"
            for msg in historial_reciente:
                contexto += f"- {msg['nombre']}: {msg['texto'][:80]}...\n"

        prompt = f"""PRODUCTO/SERVICIO A EVALUAR:
{producto}{contexto}

Da tu opinión profesional (2-3 oraciones):"""
    else:
        contexto = ""
        if historial_reciente:
            contexto = "\n\nOTHER PROFESSIONALS' OPINIONS:\n"
            for msg in historial_reciente:
                contexto += f"- {msg['nombre']}: {msg['texto'][:80]}...\n"

        prompt = f"""PRODUCT/SERVICE TO EVALUATE:
{producto}{contexto}

Give your professional opinion (2-3 sentences):"""

    try:
        mensaje = client.messages.create(
            model=MODEL_NAME,
            max_tokens=150,
            system=agente["sistema"],
            messages=[{"role": "user", "content": prompt}]
        )
        return mensaje.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"

def generar_resumen(producto, historial, region="global", idioma="es"):
    if not client:
        return "Error: No API Key configured"

    if idioma == "es":
        region_nombre = REGIONES.get(region, REGIONES["global"])["nombre"]
    else:
        region_nombre = REGIONES.get(region, REGIONES["global"])["nombre_en"]

    opiniones = "\n".join([f"- {m['emoji']} {m['nombre']}: {m['texto'][:100]}" for m in historial[:20]])

    if idioma == "es":
        prompt = f"""Eres un analista senior. Revisaste opiniones de {len(historial)} profesionales de {region_nombre} sobre:

PRODUCTO/SERVICIO: {producto}

MUESTRA DE OPINIONES:
{opiniones}

Genera un RESUMEN EJECUTIVO:
1. 🎯 VEREDICTO GENERAL
2. 📊 CONSENSO (% positivo/negativo/neutral)
3. ✅ TOP 3 FORTALEZAS
4. ⚠️ TOP 3 PREOCUPACIONES
5. 🌍 CONSIDERACIONES REGIONALES
6. 💡 RECOMENDACIÓN ESTRATÉGICA

Responde en español."""
    else:
        prompt = f"""You are a senior analyst. You reviewed opinions from {len(historial)} professionals from {region_nombre} about:

PRODUCT/SERVICE: {producto}

SAMPLE OPINIONS:
{opiniones}

Generate an EXECUTIVE SUMMARY:
1. 🎯 GENERAL VERDICT
2. 📊 CONSENSUS (% positive/negative/neutral)
3. ✅ TOP 3 STRENGTHS
4. ⚠️ TOP 3 CONCERNS
5. 🌍 REGIONAL CONSIDERATIONS
6. 💡 STRATEGIC RECOMMENDATION

Respond in English."""

    try:
        mensaje = client.messages.create(
            model=MODEL_NAME,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return mensaje.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"

# =============================================================================
# FUNCIONES AUXILIARES Y PDF
# =============================================================================

def limpiar_emoji(texto):
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642"
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"
        u"\u3030"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub('', texto)


def generar_pdf(producto, debate, resumen, region, idioma, total_agentes, total_rondas):
    """Genera un PDF con el debate y las conclusiones"""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    # Estilos personalizados
    titulo_style = ParagraphStyle(
        'TituloPersonalizado',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=20,
        textColor=colors.HexColor('#6366f1'),
        alignment=TA_CENTER
    )

    subtitulo_style = ParagraphStyle(
        'SubtituloPersonalizado',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.HexColor('#4B5563'),
        alignment=TA_CENTER
    )

    seccion_style = ParagraphStyle(
        'SeccionPersonalizado',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#1F2937'),
        borderColor=colors.HexColor('#6366f1'),
        borderWidth=0,
        borderPadding=5,
        leftIndent=0
    )

    agente_nombre_style = ParagraphStyle(
        'AgenteNombre',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6366f1'),
        fontName='Helvetica-Bold',
        spaceBefore=10
    )

    mensaje_style = ParagraphStyle(
        'Mensaje',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#374151'),
        leftIndent=15,
        spaceBefore=3,
        spaceAfter=8,
        alignment=TA_JUSTIFY
    )

    resumen_style = ParagraphStyle(
        'Resumen',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1F2937'),
        spaceBefore=5,
        spaceAfter=5,
        alignment=TA_JUSTIFY,
        leading=14
    )

    ronda_style = ParagraphStyle(
        'Ronda',
        parent=styles['Heading3'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.white,
        backColor=colors.HexColor('#6366f1'),
        alignment=TA_CENTER,
        borderPadding=8
    )

    story = []

    # Título principal
    titulo_texto = "SIMULMARKET 100" if idioma == "es" else "SIMULMARKET 100"
    story.append(Paragraph(titulo_texto, titulo_style))

    subtitulo_texto = "Reporte de Focus Group con IA" if idioma == "es" else "AI Focus Group Report"
    story.append(Paragraph(subtitulo_texto, subtitulo_style))

    # Información del análisis
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    info_texto = f"Fecha: {fecha} | Region: {region} | Agentes: {total_agentes} | Rondas: {total_rondas}"
    story.append(Paragraph(info_texto, styles['Normal']))
    story.append(Spacer(1, 20))

    # Producto analizado
    producto_titulo = "PRODUCTO/SERVICIO ANALIZADO" if idioma == "es" else "ANALYZED PRODUCT/SERVICE"
    story.append(Paragraph(producto_titulo, seccion_style))

    producto_limpio = limpiar_emoji(producto)
    story.append(Paragraph(producto_limpio, resumen_style))
    story.append(Spacer(1, 15))

    # Línea divisora
    story.append(Paragraph("<hr/>", styles['Normal']))

    # Sección de debate
    debate_titulo = "DEBATE PROFESIONAL" if idioma == "es" else "PROFESSIONAL DEBATE"
    story.append(Paragraph(debate_titulo, seccion_style))
    story.append(Spacer(1, 10))

    ronda_actual = 0
    for msg in debate:
        # Mostrar divisor de ronda
        if msg.get('ronda', 1) != ronda_actual:
            ronda_actual = msg.get('ronda', 1)
            ronda_texto = f"Ronda {ronda_actual} de {total_rondas}" if idioma == "es" else f"Round {ronda_actual} of {total_rondas}"
            story.append(Paragraph(ronda_texto, ronda_style))

        # Nombre del agente
        nombre_limpio = limpiar_emoji(msg['nombre'])
        story.append(Paragraph(f"#{msg.get('numero', '')} - {nombre_limpio}", agente_nombre_style))

        # Mensaje del agente
        texto_limpio = limpiar_emoji(msg['texto'])
        story.append(Paragraph(texto_limpio, mensaje_style))

    # Nueva página para el resumen
    story.append(PageBreak())

    # Sección de resumen ejecutivo
    resumen_titulo = "RESUMEN EJECUTIVO" if idioma == "es" else "EXECUTIVE SUMMARY"
    story.append(Paragraph(resumen_titulo, titulo_style))
    story.append(Spacer(1, 20))

    # Procesar el resumen para mostrarlo mejor
    resumen_limpio = limpiar_emoji(resumen)
    lineas_resumen = resumen_limpio.split('\n')

    for linea in lineas_resumen:
        linea = linea.strip()
        if linea:
            # Detectar títulos de sección (líneas con : o mayúsculas)
            if linea.endswith(':') or (linea.isupper() and len(linea) < 50):
                story.append(Spacer(1, 10))
                story.append(Paragraph(f"<b>{linea}</b>", resumen_style))
            else:
                story.append(Paragraph(linea, resumen_style))

    story.append(Spacer(1, 30))

    # Pie de página
    footer_texto = "Generado por SimulMarket 100 - Focus Group con IA" if idioma == "es" else "Generated by SimulMarket 100 - AI Focus Group"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#9CA3AF'),
        alignment=TA_CENTER
    )
    story.append(Paragraph(footer_texto, footer_style))

    # Construir PDF
    doc.build(story)
    buffer.seek(0)

    return buffer

# =============================================================================
# FLASK APP
# =============================================================================

app = Flask(__name__)
ultimo_debate = {
    "debate": []
}

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, agentes=AGENTES, regiones=REGIONES, idiomas=IDIOMAS)

@app.route("/iniciar-debate", methods=["POST"])
def iniciar_debate():
    global ultimo_debate

    datos = request.get_json()
    producto = datos.get("producto", "")
    cantidad_agentes = datos.get("cantidad_agentes", 10)
    rondas = datos.get("rondas", 2)
    region = datos.get("region", "global")
    idioma = datos.get("idioma", "es")

    if not producto:
        error_msg = "Debes describir un producto" if idioma == "es" else "You must describe a product"
        return jsonify({"error": error_msg}), 400

    cantidad_agentes = min(cantidad_agentes, 100)
    rondas = min(max(rondas, 2), 5)

    agentes_actuales = actualizar_agentes(cantidad_agentes, region, idioma)

    todos_los_ids = list(agentes_actuales.keys())[:cantidad_agentes]

    historial = []

    for ronda in range(1, rondas + 1):
        for i, agente_id in enumerate(todos_los_ids):
            agente = agentes_actuales[agente_id]
            respuesta = generar_respuesta_agente(agente_id, producto, historial)

            mensaje = {
                "agente_id": agente_id,
                "nombre": agente["nombre"],
                "emoji": agente["emoji"],
                "color": agente["color"],
                "texto": respuesta,
                "numero": i + 1,
                "ronda": ronda
            }
            historial.append(mensaje)
            time.sleep(0.1) # Reducido un poco para agilidad

    resumen = generar_resumen(producto, historial, region, idioma)

    if idioma == "es":
        region_nombre = REGIONES.get(region, REGIONES["global"])["nombre"]
    else:
        region_nombre = REGIONES.get(region, REGIONES["global"])["nombre_en"]

    # Guardar datos para el PDF
    ultimo_debate = {
        "producto": producto,
        "debate": historial,
        "resumen": resumen,
        "region": region_nombre,
        "idioma": idioma,
        "total_agentes": cantidad_agentes,
        "total_rondas": rondas
    }

    return jsonify({
        "success": True,
        "debate": historial,
        "resumen": resumen,
        "total_agentes": cantidad_agentes,
        "total_rondas": rondas,
        "region": region_nombre,
        "idioma": idioma
    })

@app.route("/descargar-pdf", methods=["GET"])
def descargar_pdf():
    global ultimo_debate

    if not ultimo_debate["debate"]:
        return jsonify({"error": "No hay debate disponible para descargar"}), 400

    try:
        pdf_buffer = generar_pdf(
            ultimo_debate["producto"],
            ultimo_debate["debate"],
            ultimo_debate["resumen"],
            ultimo_debate["region"],
            ultimo_debate["idioma"],
            ultimo_debate["total_agentes"],
            ultimo_debate["total_rondas"]
        )

        # Generar nombre del archivo
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"SimulMarket_Reporte_{fecha}.pdf"

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nombre_archivo
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 SIMULMARKET 100 - Focus Group con 100 Agentes IA")
    print("="*60)
    print(f"\n📊 Agentes cargados: {len(AGENTES)}")
    print("🌍 Regiones:", ", ".join(REGIONES.keys()))
    print("🌐 Idiomas:", ", ".join(IDIOMAS.keys()))
    print("📥 Descarga PDF habilitada")
    print("📍 Abre tu navegador en: http://localhost:5000")
    print("🛑 Para detener: Ctrl+C\n")

    app.run(host="0.0.0.0", port=5000, debug=True)
