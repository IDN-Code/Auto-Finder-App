"""
ProjectTeam 100 - Aplicación Unificada (main6.py)
Consolidates app.py, config.py, project_engine.py, pdf_generator.py, email_sender.py, and templates/index.html
"""
import os
import io
import re
import json
import smtplib
from datetime import datetime
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from functools import wraps

import requests
from flask import Flask, render_template_string, request, jsonify, send_file, session, redirect, url_for, flash
from dotenv import load_dotenv
import anthropic

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable, ListFlowable, ListItem
)
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF

# ==============================================================================
# CONFIGURATION
# ==============================================================================
load_dotenv()

# API Key de Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Firebase Web API Key
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")

# Configuración de Email (SMTP)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# Modelo de Claude
CLAUDE_MODEL = "claude-3-5-sonnet-20240620"  # Updated to a valid recent model or use the one from config if specific

# Regiones disponibles
REGIONS = {
    "latam": {
        "name": "Latinoamérica",
        "emoji": "🌎",
        "style": "Cálido, relacional, expresivo",
        "currency": "USD"
    },
    "northamerica": {
        "name": "Norteamérica",
        "emoji": "🇺🇸",
        "style": "Directo, orientado a resultados",
        "currency": "USD"
    },
    "europe": {
        "name": "Europa",
        "emoji": "🇪🇺",
        "style": "Equilibrado, reflexivo, regulatorio",
        "currency": "EUR"
    },
    "asia": {
        "name": "Asia",
        "emoji": "🌏",
        "style": "Respetuoso, largo plazo, tecnológico",
        "currency": "USD"
    },
    "africa": {
        "name": "África",
        "emoji": "🌍",
        "style": "Emprendedor, pragmático, comunitario",
        "currency": "USD"
    },
    "oceania": {
        "name": "Oceanía",
        "emoji": "🦘",
        "style": "Relajado pero profesional",
        "currency": "AUD"
    },
    "global": {
        "name": "Global",
        "emoji": "🌐",
        "style": "Diverso, internacional, adaptable",
        "currency": "USD"
    }
}

# Industrias disponibles
INDUSTRIES = [
    "Tecnología / Software",
    "Comercio / Retail",
    "Servicios Financieros",
    "Salud / Healthcare",
    "Educación",
    "Manufactura",
    "Construcción / Inmobiliario",
    "Alimentos y Bebidas",
    "Marketing / Publicidad",
    "Entretenimiento / Medios",
    "Transporte / Logística",
    "Turismo / Hospitalidad",
    "Energía / Recursos Naturales",
    "Agricultura",
    "Consultoría / Servicios Profesionales",
    "ONGs / Organizaciones sin fines de lucro",
    "Gobierno / Sector Público",
    "Otro"
]

# Niveles de detalle
DETAIL_LEVELS = {
    "basic": {
        "name": "Básico",
        "description": "Overview general del proyecto",
        "icon": "📋"
    },
    "detailed": {
        "name": "Detallado",
        "description": "Paso a paso con entregables",
        "icon": "📊"
    },
    "ultra": {
        "name": "Ultra-Detallado",
        "description": "Sub-tareas, responsables y dependencias",
        "icon": "🔬"
    }
}

# Colores del tema (moderno/profesional)
THEME_COLORS = {
    "primary": "#1E3A5F",      # Azul oscuro profesional
    "secondary": "#3498DB",    # Azul brillante
    "accent": "#00D4AA",       # Verde turquesa moderno
    "dark": "#0D1B2A",         # Casi negro
    "light": "#F8FAFC",        # Blanco suave
    "gradient_start": "#667eea",
    "gradient_end": "#764ba2"
}

# Colors for PDF
PRIMARY_COLOR = colors.HexColor("#1E3A5F")
SECONDARY_COLOR = colors.HexColor("#3498DB")
ACCENT_COLOR = colors.HexColor("#00D4AA")
DARK_COLOR = colors.HexColor("#0D1B2A")
LIGHT_COLOR = colors.HexColor("#F8FAFC")
GRADIENT_START = colors.HexColor("#667eea")
GRADIENT_END = colors.HexColor("#764ba2")


# ==============================================================================
# HTML TEMPLATES
# ==============================================================================
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Iniciar Sesion | ProjectTeam 100</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #0D1B2A 0%, #1E3A5F 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; color: #333; }
        .auth-container { max-width: 420px; width: 100%; background: white; border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); overflow: hidden; }
        .form-header { text-align: center; padding: 40px 30px 20px; background: white; }
        .logo { font-size: 48px; margin-bottom: 10px; display: block; }
        .form-header h1 { font-size: 24px; margin-bottom: 8px; color: #1E3A5F; font-weight: 700; }
        .form-header p { opacity: 0.7; font-size: 14px; margin: 0; }
        .form-body { padding: 0 30px 40px; }
        form { display: flex; flex-direction: column; gap: 20px; }
        .input-group { display: flex; flex-direction: column; gap: 8px; }
        .input-group label { font-weight: 600; color: #1E3A5F; font-size: 14px; }
        .input-group input { padding: 14px 16px; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 16px; transition: all 0.3s ease; }
        .input-group input:focus { outline: 0; border-color: #3498DB; box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1); }
        .submit-btn { background: linear-gradient(135deg, #1E3A5F, #3498DB); color: white; border: none; padding: 16px; font-size: 16px; font-weight: 600; border-radius: 10px; cursor: pointer; transition: transform 0.2s ease; margin-top: 10px; }
        .submit-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(52, 152, 219, 0.3); }
        .flash-messages { list-style: none; padding: 0 30px; margin: 0; }
        .flash { padding: 12px; margin-bottom: 15px; border-radius: 8px; text-align: center; font-size: 14px; font-weight: 500; }
        .flash.success { background-color: #d1fae5; color: #065f46; }
        .flash.danger { background-color: #fee2e2; color: #b91c1c; }
        .flash.warning { background-color: #fef3c7; color: #92400e; }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="form-header">
            <span class="logo">🚀</span>
            <h1>ProjectTeam 100</h1>
            <p>Ingresa para comenzar tu proyecto</p>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <ul class="flash-messages">
                    {% for category, message in messages %}
                        <li class="flash {{ category }}">{{ message }}</li>
                    {% endfor %}
                </ul>
            {% endif %}
        {% endwith %}
        <div class="form-body">
            <form action="{{ url_for('auth_login') }}" method="post">
                <div class="input-group">
                    <label for="email">Correo Electrónico</label>
                    <input type="email" name="email" id="email" required placeholder="tu@email.com">
                </div>
                <div class="input-group">
                    <label for="password">Contraseña</label>
                    <input type="password" name="password" id="password" required placeholder="••••••••">
                </div>
                <button type="submit" class="submit-btn">Entrar</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 ProjectTeam 100 - Plan de Proyecto Multidisciplinario</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #1E3A5F;
            --secondary: #3498DB;
            --accent: #00D4AA;
            --dark: #0D1B2A;
            --light: #F8FAFC;
            --gradient-start: #667eea;
            --gradient-end: #764ba2;
            --success: #10B981;
            --warning: #F59E0B;
            --error: #EF4444;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0D1B2A 0%, #1E3A5F 50%, #0D1B2A 100%);
            min-height: 100vh;
            color: #fff;
            overflow-x: hidden;
        }

        /* Animated Background */
        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            overflow: hidden;
        }

        .bg-animation::before {
            content: '';
            position: absolute;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at 20% 80%, rgba(102, 126, 234, 0.15) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(0, 212, 170, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 40% 40%, rgba(118, 75, 162, 0.1) 0%, transparent 50%);
            animation: bgMove 20s ease-in-out infinite;
        }

        @keyframes bgMove {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(-5%, -5%); }
        }

        /* Container */
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        /* Header */
        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .logo {
            font-size: 64px;
            margin-bottom: 10px;
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .title {
            font-size: 42px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent) 0%, var(--secondary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }

        .subtitle {
            font-size: 18px;
            color: rgba(255,255,255,0.7);
            font-weight: 300;
        }

        /* Progress Bar */
        .progress-container {
            margin-bottom: 30px;
            display: none;
        }

        .progress-bar {
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--secondary));
            width: 0%;
            transition: width 0.5s ease;
            border-radius: 3px;
        }

        .progress-text {
            text-align: center;
            margin-top: 10px;
            font-size: 14px;
            color: rgba(255,255,255,0.6);
        }

        /* Steps Indicator */
        .steps {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 40px;
        }

        .step {
            display: flex;
            align-items: center;
            gap: 10px;
            opacity: 0.4;
            transition: all 0.3s;
        }

        .step.active {
            opacity: 1;
        }

        .step.completed {
            opacity: 0.8;
        }

        .step-number {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(255,255,255,0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 14px;
            border: 2px solid transparent;
            transition: all 0.3s;
        }

        .step.active .step-number {
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            border-color: var(--accent);
        }

        .step.completed .step-number {
            background: var(--success);
        }

        .step-label {
            font-size: 13px;
            font-weight: 500;
        }

        /* Card */
        .card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 40px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
        }

        .card-title {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        /* Form Elements */
        .form-group {
            margin-bottom: 25px;
        }

        .form-label {
            display: block;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            color: rgba(255,255,255,0.9);
        }

        .form-input, .form-select, .form-textarea {
            width: 100%;
            padding: 16px 20px;
            border-radius: 12px;
            border: 2px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 16px;
            font-family: 'Inter', sans-serif;
            transition: all 0.3s;
        }

        .form-input:focus, .form-select:focus, .form-textarea:focus {
            outline: none;
            border-color: var(--accent);
            background: rgba(255,255,255,0.08);
            box-shadow: 0 0 0 4px rgba(0, 212, 170, 0.15);
        }

        .form-input::placeholder, .form-textarea::placeholder {
            color: rgba(255,255,255,0.4);
        }

        .form-select {
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2'%3E%3Cpolyline points='6,9 12,15 18,9'%3E%3C/polyline%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 16px center;
            padding-right: 50px;
        }

        .form-select option {
            background: var(--dark);
            color: #fff;
        }

        .form-textarea {
            min-height: 120px;
            resize: vertical;
        }

        /* Language Toggle */
        .language-toggle {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 30px;
        }

        .lang-btn {
            padding: 10px 24px;
            border-radius: 20px;
            border: 2px solid rgba(255,255,255,0.2);
            background: transparent;
            color: rgba(255,255,255,0.7);
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .lang-btn.active {
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            border-color: transparent;
            color: #fff;
        }

        /* Options Grid */
        .options-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 25px;
        }

        @media (max-width: 600px) {
            .options-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Checkbox Custom */
        .checkbox-wrapper {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 20px;
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            border: 2px solid rgba(255,255,255,0.1);
            cursor: pointer;
            transition: all 0.3s;
        }

        .checkbox-wrapper:hover {
            border-color: rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.05);
        }

        .checkbox-wrapper input {
            display: none;
        }

        .checkbox-wrapper input:checked + .checkbox-custom {
            background: var(--accent);
            border-color: var(--accent);
        }

        .checkbox-wrapper input:checked + .checkbox-custom::after {
            opacity: 1;
            transform: scale(1);
        }

        .checkbox-custom {
            width: 24px;
            height: 24px;
            border-radius: 6px;
            border: 2px solid rgba(255,255,255,0.3);
            background: transparent;
            position: relative;
            flex-shrink: 0;
            transition: all 0.3s;
        }

        .checkbox-custom::after {
            content: '✓';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) scale(0);
            color: var(--dark);
            font-weight: 700;
            font-size: 14px;
            opacity: 0;
            transition: all 0.2s;
        }

        .checkbox-label {
            font-size: 14px;
            font-weight: 500;
        }

        .checkbox-desc {
            font-size: 12px;
            color: rgba(255,255,255,0.5);
            margin-top: 2px;
        }

        /* Detail Level Cards */
        .detail-options {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 25px;
        }

        @media (max-width: 700px) {
            .detail-options {
                grid-template-columns: 1fr;
            }
        }

        .detail-card {
            padding: 20px;
            border-radius: 16px;
            border: 2px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.03);
            cursor: pointer;
            text-align: center;
            transition: all 0.3s;
        }

        .detail-card:hover {
            border-color: rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.05);
        }

        .detail-card.selected {
            border-color: var(--accent);
            background: rgba(0, 212, 170, 0.1);
        }

        .detail-icon {
            font-size: 32px;
            margin-bottom: 10px;
        }

        .detail-name {
            font-weight: 600;
            margin-bottom: 5px;
        }

        .detail-desc {
            font-size: 12px;
            color: rgba(255,255,255,0.5);
        }

        /* Buttons */
        .btn {
            padding: 16px 32px;
            border-radius: 12px;
            border: none;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
            color: #fff;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.4);
        }

        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: 2px solid rgba(255,255,255,0.2);
        }

        .btn-secondary:hover {
            background: rgba(255,255,255,0.15);
        }

        .btn-success {
            background: linear-gradient(135deg, var(--success), #059669);
            color: #fff;
        }

        .btn-block {
            width: 100%;
        }

        /* Question Card */
        .question-card {
            background: rgba(0, 212, 170, 0.1);
            border: 2px solid rgba(0, 212, 170, 0.3);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 25px;
        }

        .question-number {
            font-size: 12px;
            font-weight: 600;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }

        .question-text {
            font-size: 20px;
            font-weight: 600;
            line-height: 1.4;
        }

        /* Loading Spinner */
        .spinner {
            width: 24px;
            height: 24px;
            border: 3px solid rgba(255,255,255,0.3);
            border-top-color: #fff;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Status Messages */
        .status {
            padding: 16px 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .status-success {
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid rgba(16, 185, 129, 0.4);
        }

        .status-error {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.4);
        }

        .status-info {
            background: rgba(52, 152, 219, 0.2);
            border: 1px solid rgba(52, 152, 219, 0.4);
        }

        /* Summary Card */
        .summary-item {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        .summary-item:last-child {
            border-bottom: none;
        }

        .summary-label {
            color: rgba(255,255,255,0.6);
        }

        .summary-value {
            font-weight: 600;
        }

        /* Sections */
        .section {
            display: none;
        }

        .section.active {
            display: block;
            animation: fadeIn 0.5s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Footer */
        .footer {
            text-align: center;
            margin-top: 40px;
            color: rgba(255,255,255,0.4);
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>

    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo">🚀</div>
            <h1 class="title">ProjectTeam 100</h1>
            <p class="subtitle" id="subtitle">Plan de Proyecto con Equipo Multidisciplinario</p>
        </div>

        <!-- Language Toggle -->
        <div class="language-toggle">
            <button class="lang-btn active" data-lang="es" onclick="setLanguage('es')">🇪🇸 Español</button>
            <button class="lang-btn" data-lang="en" onclick="setLanguage('en')">🇺🇸 English</button>
        </div>

        <!-- Steps Indicator -->
        <div class="steps">
            <div class="step active" id="step1">
                <div class="step-number">1</div>
                <span class="step-label" data-es="Datos" data-en="Data">Datos</span>
            </div>
            <div class="step" id="step2">
                <div class="step-number">2</div>
                <span class="step-label" data-es="Preguntas" data-en="Questions">Preguntas</span>
            </div>
            <div class="step" id="step3">
                <div class="step-number">3</div>
                <span class="step-label" data-es="Opciones" data-en="Options">Opciones</span>
            </div>
            <div class="step" id="step4">
                <div class="step-number">4</div>
                <span class="step-label" data-es="Resultado" data-en="Result">Resultado</span>
            </div>
        </div>

        <!-- Progress Bar -->
        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <p class="progress-text" id="progressText"></p>
        </div>

        <!-- Section 1: Initial Data -->
        <div class="section active" id="section1">
            <div class="card">
                <h2 class="card-title">
                    <span>📋</span>
                    <span data-es="Información del Proyecto" data-en="Project Information">Información del Proyecto</span>
                </h2>

                <form id="initialForm">
                    <div class="form-group">
                        <label class="form-label" data-es="Nombre del Proyecto *" data-en="Project Name *">Nombre del Proyecto *</label>
                        <input type="text" class="form-input" id="projectName" required
                               data-placeholder-es="Ej: App de Delivery para Restaurantes"
                               data-placeholder-en="Ex: Restaurant Delivery App"
                               placeholder="Ej: App de Delivery para Restaurantes">
                    </div>

                    <div class="form-group">
                        <label class="form-label" data-es="Descripción del Proyecto *" data-en="Project Description *">Descripción del Proyecto *</label>
                        <textarea class="form-textarea" id="projectDescription" required
                                  data-placeholder-es="Describe tu proyecto, objetivos principales y qué problema resuelve..."
                                  data-placeholder-en="Describe your project, main objectives and what problem it solves..."
                                  placeholder="Describe tu proyecto, objetivos principales y qué problema resuelve..."></textarea>
                    </div>

                    <div class="options-grid">
                        <div class="form-group">
                            <label class="form-label" data-es="Industria *" data-en="Industry *">Industria *</label>
                            <select class="form-select" id="projectIndustry" required>
                                <option value="" data-es="Seleccionar industria..." data-en="Select industry...">Seleccionar industria...</option>
                                {% for industry in industries %}
                                <option value="{{ industry }}">{{ industry }}</option>
                                {% endfor %}
                            </select>
                        </div>

                        <div class="form-group">
                            <label class="form-label" data-es="Ubicación *" data-en="Location *">Ubicación *</label>
                            <input type="text" class="form-input" id="projectLocation" required
                                   data-placeholder-es="Ej: Ciudad de México, México"
                                   data-placeholder-en="Ex: New York, USA"
                                   placeholder="Ej: Ciudad de México, México">
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="form-label" data-es="Región de Enfoque *" data-en="Focus Region *">Región de Enfoque *</label>
                        <select class="form-select" id="projectRegion" required>
                            {% for key, region in regions.items() %}
                            <option value="{{ key }}">{{ region.emoji }} {{ region.name }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <button type="submit" class="btn btn-primary btn-block" id="btnStart">
                        <span data-es="Continuar" data-en="Continue">Continuar</span>
                        <span>→</span>
                    </button>
                </form>
            </div>
        </div>

        <!-- Section 2: Questions -->
        <div class="section" id="section2">
            <div class="card">
                <h2 class="card-title">
                    <span>❓</span>
                    <span data-es="Preguntas de Clarificación" data-en="Clarification Questions">Preguntas de Clarificación</span>
                </h2>

                <div class="question-card" id="questionCard">
                    <p class="question-number" id="questionNumber">Pregunta 1 de 5</p>
                    <p class="question-text" id="questionText">Cargando pregunta...</p>
                </div>

                <div class="form-group">
                    <textarea class="form-textarea" id="answerInput"
                              data-placeholder-es="Escribe tu respuesta aquí..."
                              data-placeholder-en="Write your answer here..."
                              placeholder="Escribe tu respuesta aquí..."></textarea>
                </div>

                <button class="btn btn-primary btn-block" id="btnAnswer" onclick="submitAnswer()">
                    <span data-es="Siguiente Pregunta" data-en="Next Question">Siguiente Pregunta</span>
                    <span>→</span>
                </button>
            </div>
        </div>

        <!-- Section 3: Options -->
        <div class="section" id="section3">
            <div class="card">
                <h2 class="card-title">
                    <span>⚙️</span>
                    <span data-es="Opciones del Plan" data-en="Plan Options">Opciones del Plan</span>
                </h2>

                <div class="form-group">
                    <label class="form-label" data-es="Nivel de Detalle" data-en="Detail Level">Nivel de Detalle</label>
                    <div class="detail-options">
                        <div class="detail-card" data-level="basic" onclick="selectDetailLevel('basic')">
                            <div class="detail-icon">📋</div>
                            <div class="detail-name" data-es="Básico" data-en="Basic">Básico</div>
                            <div class="detail-desc" data-es="Overview general" data-en="General overview">Overview general</div>
                        </div>
                        <div class="detail-card selected" data-level="detailed" onclick="selectDetailLevel('detailed')">
                            <div class="detail-icon">📊</div>
                            <div class="detail-name" data-es="Detallado" data-en="Detailed">Detallado</div>
                            <div class="detail-desc" data-es="Paso a paso" data-en="Step by step">Paso a paso</div>
                        </div>
                        <div class="detail-card" data-level="ultra" onclick="selectDetailLevel('ultra')">
                            <div class="detail-icon">🔬</div>
                            <div class="detail-name" data-es="Ultra-Detallado" data-en="Ultra-Detailed">Ultra-Detallado</div>
                            <div class="detail-desc" data-es="Sub-tareas y dependencias" data-en="Sub-tasks and dependencies">Sub-tareas y dependencias</div>
                        </div>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label" data-es="Incluir en el Plan" data-en="Include in Plan">Incluir en el Plan</label>
                    <div class="options-grid">
                        <label class="checkbox-wrapper">
                            <input type="checkbox" id="includeCosts">
                            <span class="checkbox-custom"></span>
                            <div>
                                <div class="checkbox-label" data-es="💰 Proyección de Costos" data-en="💰 Cost Projection">💰 Proyección de Costos</div>
                                <div class="checkbox-desc" data-es="Estimación de presupuesto en USD" data-en="Budget estimation in USD">Estimación de presupuesto en USD</div>
                            </div>
                        </label>
                        <label class="checkbox-wrapper">
                            <input type="checkbox" id="includeTimeline">
                            <span class="checkbox-custom"></span>
                            <div>
                                <div class="checkbox-label" data-es="📅 Cronograma" data-en="📅 Timeline">📅 Cronograma</div>
                                <div class="checkbox-desc" data-es="Tiempos y hitos del proyecto" data-en="Project times and milestones">Tiempos y hitos del proyecto</div>
                            </div>
                        </label>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label" data-es="Email para recibir el PDF *" data-en="Email to receive PDF *">Email para recibir el PDF *</label>
                    <input type="email" class="form-input" id="userEmail" required
                           data-placeholder-es="tu@email.com"
                           data-placeholder-en="your@email.com"
                           placeholder="tu@email.com">
                </div>

                <button class="btn btn-primary btn-block" id="btnGenerate" onclick="generateProject()">
                    <span data-es="🚀 Generar Plan de Proyecto" data-en="🚀 Generate Project Plan">🚀 Generar Plan de Proyecto</span>
                </button>
            </div>
        </div>

        <!-- Section 4: Result -->
        <div class="section" id="section4">
            <div class="card">
                <h2 class="card-title">
                    <span>✅</span>
                    <span data-es="¡Plan Generado!" data-en="Plan Generated!">¡Plan Generado!</span>
                </h2>

                <div class="status status-success" id="statusMessage">
                    <span>✅</span>
                    <span data-es="Tu plan de proyecto ha sido generado exitosamente." data-en="Your project plan has been generated successfully.">Tu plan de proyecto ha sido generado exitosamente.</span>
                </div>

                <div id="summaryInfo" style="margin-bottom: 30px;">
                    <div class="summary-item">
                        <span class="summary-label" data-es="Proyecto" data-en="Project">Proyecto</span>
                        <span class="summary-value" id="summaryName">-</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label" data-es="Tamaño del Equipo" data-en="Team Size">Tamaño del Equipo</span>
                        <span class="summary-value" id="summaryTeamSize">-</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label" data-es="Fases del Proyecto" data-en="Project Phases">Fases del Proyecto</span>
                        <span class="summary-value" id="summaryPhases">-</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label" data-es="Email de Entrega" data-en="Delivery Email">Email de Entrega</span>
                        <span class="summary-value" id="summaryEmail">-</span>
                    </div>
                </div>

                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <button class="btn btn-success" id="btnDownload" onclick="downloadPDF()" style="flex: 1;">
                        <span>📥</span>
                        <span data-es="Descargar PDF" data-en="Download PDF">Descargar PDF</span>
                    </button>
                    <button class="btn btn-secondary" onclick="startNew()" style="flex: 1;">
                        <span>🔄</span>
                        <span data-es="Nuevo Proyecto" data-en="New Project">Nuevo Proyecto</span>
                    </button>
                </div>
            </div>
        </div>

        <!-- Loading Overlay -->
        <div id="loadingOverlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 20px;">
            <div class="spinner" style="width: 50px; height: 50px; border-width: 4px;"></div>
            <p id="loadingText" style="font-size: 18px;">Procesando...</p>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>© 2024 ProjectTeam 100 - <span data-es="Todos los derechos reservados" data-en="All rights reserved">Todos los derechos reservados</span></p>
        </div>
    </div>

    <script>
        // Estado de la aplicación
        let state = {
            language: 'es',
            sessionId: null,
            questions: [],
            currentQuestionIndex: 0,
            answers: [],
            detailLevel: 'detailed',
            projectData: {}
        };

        // Traducciones
        const translations = {
            subtitle: { es: 'Plan de Proyecto con Equipo Multidisciplinario', en: 'Multidisciplinary Team Project Plan' },
            loading: { es: 'Procesando...', en: 'Processing...' },
            generatingQuestions: { es: 'Analizando proyecto y generando preguntas...', en: 'Analyzing project and generating questions...' },
            generatingProject: { es: 'Generando plan de proyecto con equipo experto...', en: 'Generating project plan with expert team...' },
            generatingPDF: { es: 'Creando documento PDF profesional...', en: 'Creating professional PDF document...' },
            questionOf: { es: 'Pregunta {0} de {1}', en: 'Question {0} of {1}' },
            nextQuestion: { es: 'Siguiente Pregunta', en: 'Next Question' },
            finishQuestions: { es: 'Finalizar Preguntas', en: 'Finish Questions' }
        };

        // Cambiar idioma
        function setLanguage(lang) {
            state.language = lang;

            // Actualizar botones de idioma
            document.querySelectorAll('.lang-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.lang === lang);
            });

            // Actualizar elementos con traducciones
            document.querySelectorAll('[data-es]').forEach(el => {
                el.textContent = el.getAttribute(`data-${lang}`);
            });

            // Actualizar placeholders
            document.querySelectorAll('[data-placeholder-es]').forEach(el => {
                el.placeholder = el.getAttribute(`data-placeholder-${lang}`);
            });

            // Actualizar subtítulo
            document.getElementById('subtitle').textContent = translations.subtitle[lang];
        }

        // Mostrar/ocultar loading
        function showLoading(text) {
            const overlay = document.getElementById('loadingOverlay');
            document.getElementById('loadingText').textContent = text || translations.loading[state.language];
            overlay.style.display = 'flex';
        }

        function hideLoading() {
            document.getElementById('loadingOverlay').style.display = 'none';
        }

        // Cambiar sección
        function goToSection(sectionNum) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.getElementById(`section${sectionNum}`).classList.add('active');

            document.querySelectorAll('.step').forEach((s, i) => {
                s.classList.remove('active', 'completed');
                if (i + 1 < sectionNum) s.classList.add('completed');
                if (i + 1 === sectionNum) s.classList.add('active');
            });
        }

        // Seleccionar nivel de detalle
        function selectDetailLevel(level) {
            state.detailLevel = level;
            document.querySelectorAll('.detail-card').forEach(card => {
                card.classList.toggle('selected', card.dataset.level === level);
            });
        }

        // Formulario inicial
        document.getElementById('initialForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            state.projectData = {
                name: document.getElementById('projectName').value,
                description: document.getElementById('projectDescription').value,
                industry: document.getElementById('projectIndustry').value,
                location: document.getElementById('projectLocation').value,
                region: document.getElementById('projectRegion').value
            };

            showLoading(translations.generatingQuestions[state.language]);

            try {
                const response = await fetch('/api/generate-questions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ...state.projectData,
                        language: state.language,
                        session_id: Date.now().toString()
                    })
                });

                const data = await response.json();

                if (data.success) {
                    state.sessionId = data.session_id;
                    state.questions = data.questions;
                    state.currentQuestionIndex = 0;
                    state.answers = [];

                    updateQuestionUI();
                    goToSection(2);
                    document.getElementById('progressContainer').style.display = 'block';
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                alert('Error de conexión: ' + error.message);
            }

            hideLoading();
        });

        // Actualizar UI de pregunta
        function updateQuestionUI() {
            const total = state.questions.length;
            const current = state.currentQuestionIndex + 1;

            document.getElementById('questionNumber').textContent =
                translations.questionOf[state.language].replace('{0}', current).replace('{1}', total);
            document.getElementById('questionText').textContent = state.questions[state.currentQuestionIndex];
            document.getElementById('answerInput').value = '';

            // Progress
            const progress = (current / total) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('progressText').textContent = `${current}/${total}`;

            // Botón
            const btnText = current === total ?
                translations.finishQuestions[state.language] :
                translations.nextQuestion[state.language];
            document.querySelector('#btnAnswer span[data-es]').textContent = btnText;
        }

        // Enviar respuesta
        async function submitAnswer() {
            const answer = document.getElementById('answerInput').value.trim();
            if (!answer) {
                alert(state.language === 'es' ? 'Por favor escribe una respuesta' : 'Please write an answer');
                return;
            }

            state.answers.push(answer);

            try {
                const response = await fetch('/api/submit-answer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        answer: answer,
                        question_index: state.currentQuestionIndex
                    })
                });

                const data = await response.json();

                if (data.success) {
                    if (data.has_more) {
                        state.currentQuestionIndex++;
                        updateQuestionUI();
                    } else {
                        // Todas las preguntas respondidas
                        document.getElementById('progressContainer').style.display = 'none';
                        goToSection(3);
                    }
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (error) {
                // Si falla el servidor, continuar localmente
                state.currentQuestionIndex++;
                if (state.currentQuestionIndex < state.questions.length) {
                    updateQuestionUI();
                } else {
                    document.getElementById('progressContainer').style.display = 'none';
                    goToSection(3);
                }
            }
        }

        // Generar proyecto
        async function generateProject() {
            const email = document.getElementById('userEmail').value.trim();
            if (!email) {
                alert(state.language === 'es' ? 'Por favor ingresa tu email' : 'Please enter your email');
                return;
            }

            showLoading(translations.generatingProject[state.language]);

            try {
                // Generar proyecto
                const projectResponse = await fetch('/api/generate-project', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        detail_level: state.detailLevel,
                        include_costs: document.getElementById('includeCosts').checked,
                        include_timeline: document.getElementById('includeTimeline').checked
                    })
                });

                const projectData = await projectResponse.json();

                if (!projectData.success) {
                    throw new Error(projectData.error);
                }

                // Generar PDF
                document.getElementById('loadingText').textContent = translations.generatingPDF[state.language];

                const pdfResponse = await fetch('/api/generate-pdf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        email: email
                    })
                });

                const pdfData = await pdfResponse.json();

                // Actualizar resumen
                document.getElementById('summaryName').textContent = state.projectData.name;
                document.getElementById('summaryTeamSize').textContent = projectData.team_size + ' profesionales';
                document.getElementById('summaryPhases').textContent = projectData.phases_count + ' fases';
                document.getElementById('summaryEmail').textContent = email;

                goToSection(4);

            } catch (error) {
                alert('Error: ' + error.message);
            }

            hideLoading();
        }

        // Descargar PDF
        function downloadPDF() {
            window.open(`/api/download-pdf/${state.sessionId}`, '_blank');
        }

        // Nuevo proyecto
        function startNew() {
            state = {
                language: state.language,
                sessionId: null,
                questions: [],
                currentQuestionIndex: 0,
                answers: [],
                detailLevel: 'detailed',
                projectData: {}
            };

            document.getElementById('initialForm').reset();
            document.getElementById('userEmail').value = '';
            document.getElementById('includeCosts').checked = false;
            document.getElementById('includeTimeline').checked = false;
            selectDetailLevel('detailed');
            goToSection(1);
        }

        // Ocultar loading al inicio
        document.getElementById('loadingOverlay').style.display = 'none';
    </script>
</body>
</html>"""


# ==============================================================================
# PROJECT ENGINE
# ==============================================================================
def get_anthropic_client():
    if ANTHROPIC_API_KEY:
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return None

def generate_clarification_questions(project_data: dict, language: str = "es") -> list:
    """Genera preguntas de clarificación."""
    client = get_anthropic_client()
    if not client:
        # Fallback if no key
        if language == "es":
            return [
                "¿Cuál es el presupuesto aproximado disponible para este proyecto?",
                "¿Cuál es el plazo ideal para completar el proyecto?",
                "¿Quiénes serán los usuarios o beneficiarios principales?",
                "¿Existe alguna restricción técnica o legal importante?",
                "¿Qué métricas definirán el éxito del proyecto?"
            ]
        else:
            return [
                "What is the approximate budget available for this project?",
                "What is the ideal timeline to complete the project?",
                "Who will be the main users or beneficiaries?",
                "Are there any important technical or legal constraints?",
                "What metrics will define the project's success?"
            ]

    lang_prompts = {
        "es": {
            "system": """Eres un consultor de proyectos experto. Tu tarea es analizar la descripción inicial de un proyecto y generar EXACTAMENTE 5 preguntas de clarificación estratégicas que ayudarán a definir mejor el proyecto.

Las preguntas deben:
1. Ser específicas al tipo de proyecto descrito
2. Ayudar a entender el alcance, recursos, y expectativas
3. Identificar posibles riesgos o consideraciones especiales
4. Clarificar el público objetivo o beneficiarios
5. Entender restricciones técnicas, legales o de mercado

Responde SOLO con un JSON array de 5 preguntas. Cada pregunta debe ser clara y directa.
Formato exacto: ["pregunta1", "pregunta2", "pregunta3", "pregunta4", "pregunta5"]""",
            "user": f"""Proyecto: {project_data.get('name', '')}
Descripción: {project_data.get('description', '')}
Industria: {project_data.get('industry', '')}
Ubicación: {project_data.get('location', '')}

Genera 5 preguntas de clarificación estratégicas para este proyecto."""
        },
        "en": {
            "system": """You are an expert project consultant. Your task is to analyze the initial project description and generate EXACTLY 5 strategic clarification questions that will help better define the project.

The questions should:
1. Be specific to the type of project described
2. Help understand scope, resources, and expectations
3. Identify potential risks or special considerations
4. Clarify the target audience or beneficiaries
5. Understand technical, legal, or market constraints

Respond ONLY with a JSON array of 5 questions. Each question must be clear and direct.
Exact format: ["question1", "question2", "question3", "question4", "question5"]""",
            "user": f"""Project: {project_data.get('name', '')}
Description: {project_data.get('description', '')}
Industry: {project_data.get('industry', '')}
Location: {project_data.get('location', '')}

Generate 5 strategic clarification questions for this project."""
        }
    }

    prompts = lang_prompts.get(language, lang_prompts["es"])

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            system=prompts["system"],
            messages=[{"role": "user", "content": prompts["user"]}]
        )

        content = response.content[0].text.strip()
        # Limpiar y parsear JSON
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        questions = json.loads(content)

        return questions[:5] if len(questions) >= 5 else questions

    except Exception as e:
        print(f"Error generando preguntas: {e}")
        # Retornar fallback
        if language == "es":
            return [
                "¿Cuál es el presupuesto aproximado disponible para este proyecto?",
                "¿Cuál es el plazo ideal para completar el proyecto?",
                "¿Quiénes serán los usuarios o beneficiarios principales?",
                "¿Existe alguna restricción técnica o legal importante?",
                "¿Qué métricas definirán el éxito del proyecto?"
            ]
        else:
            return [
                "What is the approximate budget available for this project?",
                "What is the ideal timeline to complete the project?",
                "Who will be the main users or beneficiaries?",
                "Are there any important technical or legal constraints?",
                "What metrics will define the project's success?"
            ]

def generate_project_team(project_data: dict, answers: list, language: str = "es") -> dict:
    """Genera el equipo multidisciplinario."""
    client = get_anthropic_client()
    if not client:
        # Fallback
        return {
            "team_size": 1,
            "team_summary": "Modo offline - Equipo básico",
            "professionals": [
                {
                    "role": "Project Manager",
                    "experience_years": "5+",
                    "key_skills": ["Management"],
                    "responsibilities": ["Coordination"],
                    "dedication_percentage": 100,
                    "profile_description": "General Manager"
                }
            ]
        }

    lang_prompts = {
        "es": {
            "system": """Eres un experto en gestión de proyectos y recursos humanos. Tu tarea es analizar un proyecto y determinar el equipo multidisciplinario ÓPTIMO necesario para ejecutarlo exitosamente.

Para cada profesional del equipo, debes incluir:
- Rol específico
- Años de experiencia recomendados
- Habilidades clave necesarias
- Responsabilidades principales en el proyecto
- Porcentaje de dedicación sugerido

El equipo debe ser realista y ajustado al tipo y escala del proyecto. No incluyas roles innecesarios.

Responde en formato JSON con esta estructura exacta:
{
    "team_size": número,
    "team_summary": "resumen breve del equipo",
    "professionals": [
        {
            "role": "nombre del rol",
            "experience_years": "X-Y años",
            "key_skills": ["skill1", "skill2", "skill3"],
            "responsibilities": ["resp1", "resp2"],
            "dedication_percentage": número,
            "profile_description": "descripción breve del perfil ideal"
        }
    ]
}""",
            "user": ""
        },
        "en": {
            "system": """You are an expert in project management and human resources. Your task is to analyze a project and determine the OPTIMAL multidisciplinary team needed to execute it successfully.

For each team professional, you must include:
- Specific role
- Recommended years of experience
- Key skills needed
- Main responsibilities in the project
- Suggested dedication percentage

The team must be realistic and adjusted to the type and scale of the project. Do not include unnecessary roles.

Respond in JSON format with this exact structure:
{
    "team_size": number,
    "team_summary": "brief team summary",
    "professionals": [
        {
            "role": "role name",
            "experience_years": "X-Y years",
            "key_skills": ["skill1", "skill2", "skill3"],
            "responsibilities": ["resp1", "resp2"],
            "dedication_percentage": number,
            "profile_description": "brief ideal profile description"
        }
    ]
}""",
            "user": ""
        }
    }

    prompts = lang_prompts.get(language, lang_prompts["es"])

    # Construir contexto completo
    questions_answers = "\n".join([f"P: {q}\nR: {a}" for q, a in zip(project_data.get('questions', []), answers)])

    user_content = f"""
PROYECTO: {project_data.get('name', '')}
DESCRIPCIÓN: {project_data.get('description', '')}
INDUSTRIA: {project_data.get('industry', '')}
UBICACIÓN: {project_data.get('location', '')}
REGIÓN: {project_data.get('region', '')}

INFORMACIÓN ADICIONAL (Preguntas y Respuestas):
{questions_answers}

Analiza este proyecto y genera el equipo multidisciplinario óptimo necesario.
"""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=3000,
            system=prompts["system"],
            messages=[{"role": "user", "content": user_content}]
        )

        content = response.content[0].text.strip()
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        team_data = json.loads(content)

        return team_data

    except Exception as e:
        print(f"Error generando equipo: {e}")
        return {
            "team_size": 5,
            "team_summary": "Equipo base para el proyecto",
            "professionals": [
                {
                    "role": "Project Manager",
                    "experience_years": "5-8 años",
                    "key_skills": ["Gestión de proyectos", "Liderazgo", "Comunicación"],
                    "responsibilities": ["Coordinación general", "Seguimiento de avances"],
                    "dedication_percentage": 100,
                    "profile_description": "Líder con experiencia en proyectos similares"
                }
            ]
        }

def generate_full_project(project_data: dict, team_data: dict, options: dict, language: str = "es") -> dict:
    """Genera el proyecto completo."""
    client = get_anthropic_client()
    if not client:
        return {"executive_summary": "Error: API Key no configurada", "phases": []}

    detail_level = options.get('detail_level', 'detailed')
    include_costs = options.get('include_costs', False)
    include_timeline = options.get('include_timeline', False)

    detail_instructions = {
        "basic": "Proporciona un overview general con fases principales y puntos clave.",
        "detailed": "Proporciona un plan detallado paso a paso con entregables específicos por fase.",
        "ultra": "Proporciona un plan ultra-detallado con sub-tareas específicas, responsables asignados del equipo, dependencias entre tareas, y criterios de aceptación."
    }

    cost_instruction = """
IMPORTANTE - PROYECCIÓN DE COSTOS:
Debes incluir una sección completa de costos con:
- Costo estimado por cada profesional del equipo (salario/honorarios)
- Costos de infraestructura y herramientas
- Costos operativos
- Contingencia recomendada
- TOTAL estimado en USD (rango mínimo - máximo basado en precios de mercado actuales)
""" if include_costs else ""

    timeline_instruction = """
IMPORTANTE - CRONOGRAMA:
Debes incluir una sección completa de tiempos con:
- Duración estimada de cada fase
- Hitos principales con fechas relativas
- Dependencias entre fases
- Tiempo total del proyecto
- Ruta crítica identificada
""" if include_timeline else ""

    lang_prompts = {
        "es": {
            "system": f"""Eres un equipo de {team_data.get('team_size', 10)} profesionales multidisciplinarios trabajando juntos para desarrollar un plan de proyecto COMPLETO y EJECUTABLE.

{detail_instructions.get(detail_level, detail_instructions['detailed'])}

{cost_instruction}

{timeline_instruction}

El plan debe ser PROFESIONAL, REALISTA y ACCIONABLE.

Responde en formato JSON con esta estructura:
{{
    "executive_summary": "resumen ejecutivo del proyecto (2-3 párrafos)",
    "objectives": ["objetivo 1", "objetivo 2", ...],
    "scope": {{
        "included": ["elemento incluido 1", ...],
        "excluded": ["elemento excluido 1", ...]
    }},
    "phases": [
        {{
            "phase_number": 1,
            "phase_name": "nombre de la fase",
            "description": "descripción",
            "duration": "duración estimada",
            "deliverables": ["entregable 1", ...],
            "tasks": [
                {{
                    "task_name": "nombre tarea",
                    "description": "descripción",
                    "responsible": "rol del responsable",
                    "duration": "duración",
                    "dependencies": ["dependencia 1", ...],
                    "subtasks": ["subtarea 1", ...],
                    "acceptance_criteria": ["criterio 1", ...]
                }}
            ],
            "milestones": ["hito 1", ...]
        }}
    ],
    "resources": {{
        "human": ["descripción recursos humanos"],
        "technical": ["herramienta/tecnología 1", ...],
        "infrastructure": ["infraestructura 1", ...]
    }},
    "risks": [
        {{
            "risk": "descripción del riesgo",
            "probability": "Alta/Media/Baja",
            "impact": "Alto/Medio/Bajo",
            "mitigation": "estrategia de mitigación"
        }}
    ],
    "success_metrics": ["métrica 1", ...],
    "recommendations": ["recomendación 1", ...],
    "costs": {{
        "team_costs": [
            {{"role": "rol", "monthly_cost": número, "duration_months": número, "total": número}}
        ],
        "infrastructure_costs": [
            {{"item": "elemento", "cost": número}}
        ],
        "operational_costs": [
            {{"item": "elemento", "monthly_cost": número, "duration_months": número, "total": número}}
        ],
        "contingency_percentage": número,
        "total_min": número,
        "total_max": número,
        "currency": "USD"
    }},
    "timeline": {{
        "total_duration": "duración total",
        "start_date": "fecha relativa de inicio",
        "end_date": "fecha relativa de fin",
        "critical_path": ["fase/tarea crítica 1", ...],
        "milestones_timeline": [
            {{"milestone": "nombre", "week": número}}
        ]
    }}
}}

NOTA: Solo incluye las secciones "costs" y "timeline" si fueron solicitadas específicamente.""",
            "user": ""
        },
        "en": {
            "system": f"""You are a team of {team_data.get('team_size', 10)} multidisciplinary professionals working together to develop a COMPLETE and EXECUTABLE project plan.

{detail_instructions.get(detail_level, detail_instructions['detailed'])}

{cost_instruction}

{timeline_instruction}

The plan must be PROFESSIONAL, REALISTIC, and ACTIONABLE.

Respond in JSON format with this structure:
{{
    "executive_summary": "project executive summary (2-3 paragraphs)",
    "objectives": ["objective 1", "objective 2", ...],
    "scope": {{
        "included": ["included element 1", ...],
        "excluded": ["excluded element 1", ...]
    }},
    "phases": [
        {{
            "phase_number": 1,
            "phase_name": "phase name",
            "description": "description",
            "duration": "estimated duration",
            "deliverables": ["deliverable 1", ...],
            "tasks": [
                {{
                    "task_name": "task name",
                    "description": "description",
                    "responsible": "responsible role",
                    "duration": "duration",
                    "dependencies": ["dependency 1", ...],
                    "subtasks": ["subtask 1", ...],
                    "acceptance_criteria": ["criterion 1", ...]
                }}
            ],
            "milestones": ["milestone 1", ...]
        }}
    ],
    "resources": {{
        "human": ["human resources description"],
        "technical": ["tool/technology 1", ...],
        "infrastructure": ["infrastructure 1", ...]
    }},
    "risks": [
        {{
            "risk": "risk description",
            "probability": "High/Medium/Low",
            "impact": "High/Medium/Low",
            "mitigation": "mitigation strategy"
        }}
    ],
    "success_metrics": ["metric 1", ...],
    "recommendations": ["recommendation 1", ...],
    "costs": {{
        "team_costs": [
            {{"role": "role", "monthly_cost": number, "duration_months": number, "total": number}}
        ],
        "infrastructure_costs": [
            {{"item": "element", "cost": number}}
        ],
        "operational_costs": [
            {{"item": "element", "monthly_cost": number, "duration_months": number, "total": number}}
        ],
        "contingency_percentage": number,
        "total_min": number,
        "total_max": number,
        "currency": "USD"
    }},
    "timeline": {{
        "total_duration": "total duration",
        "start_date": "relative start date",
        "end_date": "relative end date",
        "critical_path": ["critical phase/task 1", ...],
        "milestones_timeline": [
            {{"milestone": "name", "week": number}}
        ]
    }}
}}

NOTE: Only include "costs" and "timeline" sections if specifically requested.""",
            "user": ""
        }
    }

    prompts = lang_prompts.get(language, lang_prompts["es"])

    # Construir contexto completo
    questions_answers = "\n".join([f"P: {q}\nR: {a}" for q, a in zip(project_data.get('questions', []), project_data.get('answers', []))])

    team_info = "\n".join([f"- {p['role']}: {p['profile_description']}" for p in team_data.get('professionals', [])])

    user_content = f"""
PROYECTO: {project_data.get('name', '')}
DESCRIPCIÓN: {project_data.get('description', '')}
INDUSTRIA: {project_data.get('industry', '')}
UBICACIÓN: {project_data.get('location', '')}
REGIÓN: {project_data.get('region', '')}

INFORMACIÓN ADICIONAL:
{questions_answers}

EQUIPO ASIGNADO:
{team_info}

NIVEL DE DETALLE SOLICITADO: {detail_level.upper()}
INCLUIR COSTOS: {'SÍ' if include_costs else 'NO'}
INCLUIR CRONOGRAMA: {'SÍ' if include_timeline else 'NO'}

Desarrolla el plan de proyecto completo con el nivel de detalle solicitado.
"""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8000,
            system=prompts["system"],
            messages=[{"role": "user", "content": user_content}]
        )

        content = response.content[0].text.strip()
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        project_plan = json.loads(content)

        return project_plan

    except Exception as e:
        print(f"Error generando proyecto: {e}")
        return {
            "executive_summary": "Error generando el plan de proyecto. Por favor intente nuevamente.",
            "objectives": [],
            "phases": [],
            "risks": [],
            "error": str(e)
        }


# ==============================================================================
# FIREBASE AUTH
# ==============================================================================
class FirebaseAuth:
    def __init__(self):
        self.firebase_web_api_key = os.environ.get("FIREBASE_WEB_API_KEY")
        if not self.firebase_web_api_key:
            print("WARNING: FIREBASE_WEB_API_KEY no configurada")
        else:
            print("SUCCESS: Firebase Auth configurado")

    def login_user(self, email, password):
        if not self.firebase_web_api_key:
            return {'success': False, 'message': 'Servicio no configurado', 'user_data': None, 'error_code': 'SERVICE_NOT_CONFIGURED'}

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.firebase_web_api_key}"
        payload = {'email': email, 'password': password, 'returnSecureToken': True}

        try:
            response = requests.post(url, json=payload, timeout=8)
            response.raise_for_status()
            user_data = response.json()

            return {
                'success': True,
                'message': 'Bienvenido! Has iniciado sesion correctamente.',
                'user_data': {
                    'user_id': user_data['localId'],
                    'email': user_data['email'],
                    'display_name': user_data.get('displayName', email.split('@')[0]),
                    'id_token': user_data['idToken']
                },
                'error_code': None
            }
        except requests.exceptions.HTTPError as e:
            try:
                error_msg = e.response.json().get('error', {}).get('message', 'ERROR')
                if 'INVALID' in error_msg or 'EMAIL_NOT_FOUND' in error_msg:
                    return {'success': False, 'message': 'Correo o contraseña incorrectos', 'user_data': None, 'error_code': 'INVALID_CREDENTIALS'}
                elif 'TOO_MANY_ATTEMPTS' in error_msg:
                    return {'success': False, 'message': 'Demasiados intentos fallidos', 'user_data': None, 'error_code': 'TOO_MANY_ATTEMPTS'}
                else:
                    return {'success': False, 'message': 'Error de autenticacion', 'user_data': None, 'error_code': 'FIREBASE_ERROR'}
            except:
                return {'success': False, 'message': 'Error de conexion', 'user_data': None, 'error_code': 'CONNECTION_ERROR'}
        except Exception as e:
            print(f"Firebase auth error: {e}")
            return {'success': False, 'message': 'Error interno del servidor', 'user_data': None, 'error_code': 'UNEXPECTED_ERROR'}

    def set_user_session(self, user_data):
        session['user_id'] = user_data['user_id']
        session['user_name'] = user_data['display_name']
        session['user_email'] = user_data['email']
        session['id_token'] = user_data['id_token']
        session['login_time'] = datetime.now().isoformat()
        session.permanent = True

    def clear_user_session(self):
        important_data = {key: session.get(key) for key in ['timestamp'] if key in session}
        session.clear()
        for key, value in important_data.items():
            session[key] = value

    def is_user_logged_in(self):
        if 'user_id' not in session or session['user_id'] is None:
            return False
        if 'login_time' in session:
            try:
                login_time = datetime.fromisoformat(session['login_time'])
                time_diff = (datetime.now() - login_time).total_seconds()
                if time_diff > 7200:  # 2 horas maximo
                    return False
            except:
                pass
        return True

    def get_current_user(self):
        if not self.is_user_logged_in():
            return None
        return {
            'user_id': session.get('user_id'),
            'user_name': session.get('user_name'),
            'user_email': session.get('user_email'),
            'id_token': session.get('id_token')
        }

firebase_auth = FirebaseAuth()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not firebase_auth.is_user_logged_in():
            flash('Tu sesion ha expirado. Inicia sesion nuevamente.', 'warning')
            return redirect(url_for('auth_login_page'))
        return f(*args, **kwargs)
    return decorated_function


# ==============================================================================
# PDF GENERATOR
# ==============================================================================
class PDFGenerator:
    def __init__(self, language: str = "es"):
        self.language = language
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configura estilos personalizados"""
        # Título principal
        self.styles.add(ParagraphStyle(
            name='CoverTitle',
            parent=self.styles['Title'],
            fontSize=36,
            textColor=PRIMARY_COLOR,
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica-Bold'
        ))

        # Subtítulo de portada
        self.styles.add(ParagraphStyle(
            name='CoverSubtitle',
            parent=self.styles['Normal'],
            fontSize=18,
            textColor=SECONDARY_COLOR,
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica'
        ))

        # Encabezado de sección
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=PRIMARY_COLOR,
            spaceBefore=25,
            spaceAfter=15,
            fontName='Helvetica-Bold',
            borderColor=ACCENT_COLOR,
            borderWidth=2,
            borderPadding=5,
            leftIndent=10
        ))

        # Subencabezado
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=SECONDARY_COLOR,
            spaceBefore=15,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))

        # Texto normal personalizado
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=DARK_COLOR,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
            leading=16
        ))

        # Texto destacado
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.white,
            backColor=PRIMARY_COLOR,
            alignment=TA_CENTER,
            spaceBefore=5,
            spaceAfter=5,
            borderPadding=8
        ))

        # Número de fase
        self.styles.add(ParagraphStyle(
            name='PhaseNumber',
            parent=self.styles['Normal'],
            fontSize=24,
            textColor=ACCENT_COLOR,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER
        ))

        # Footer
        self.styles.add(ParagraphStyle(
            name='FooterStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.gray,
            alignment=TA_CENTER
        ))

    def _add_watermark(self, canvas_obj, doc):
        """Añade marca de agua diagonal en cada página"""
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica-Bold', 60)
        canvas_obj.setFillColor(colors.Color(0.9, 0.9, 0.9, alpha=0.3))
        canvas_obj.translate(letter[0]/2, letter[1]/2)
        canvas_obj.rotate(45)
        canvas_obj.drawCentredString(0, 0, "ProjectTeam 100")
        canvas_obj.restoreState()

        # Añadir header y footer
        self._add_header_footer(canvas_obj, doc)

    def _add_header_footer(self, canvas_obj, doc):
        """Añade header y footer a cada página"""
        canvas_obj.saveState()

        # Header - línea decorativa
        canvas_obj.setStrokeColor(ACCENT_COLOR)
        canvas_obj.setLineWidth(3)
        canvas_obj.line(50, letter[1] - 40, letter[0] - 50, letter[1] - 40)

        # Header text
        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.setFillColor(PRIMARY_COLOR)
        canvas_obj.drawString(50, letter[1] - 35, "ProjectTeam 100")
        canvas_obj.drawRightString(letter[0] - 50, letter[1] - 35,
                                   datetime.now().strftime("%d/%m/%Y"))

        # Footer
        canvas_obj.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
        canvas_obj.setLineWidth(1)
        canvas_obj.line(50, 40, letter[0] - 50, 40)

        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.setFillColor(colors.gray)
        canvas_obj.drawCentredString(letter[0]/2, 25, f"Pagina {doc.page}")

        canvas_obj.restoreState()

    def _create_cover_page(self, project_data: dict) -> list:
        """Crea la portada del documento"""
        elements = []

        # Espaciado inicial
        elements.append(Spacer(1, 2*inch))

        # Logo / Icono
        elements.append(Paragraph("ProjectTeam 100", ParagraphStyle(
            name='LogoText',
            fontSize=48,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=ACCENT_COLOR,
            fontName='Helvetica-Bold'
        )))

        # Subtítulo
        subtitle = "Plan de Proyecto Multidisciplinario" if self.language == "es" else "Multidisciplinary Project Plan"
        elements.append(Paragraph(subtitle, self.styles['CoverSubtitle']))

        elements.append(Spacer(1, 0.5*inch))

        # Línea decorativa
        elements.append(HRFlowable(
            width="60%",
            thickness=3,
            color=ACCENT_COLOR,
            spaceBefore=20,
            spaceAfter=40
        ))

        # Nombre del proyecto
        elements.append(Paragraph(
            f"<b>{project_data.get('name', 'Proyecto')}</b>",
            ParagraphStyle(
                name='ProjectName',
                fontSize=28,
                textColor=PRIMARY_COLOR,
                alignment=TA_CENTER,
                spaceAfter=30,
                fontName='Helvetica-Bold'
            )
        ))

        # Información del proyecto
        loc_label = "Ubicacion:" if self.language == "es" else "Location:"
        ind_label = "Industria:" if self.language == "es" else "Industry:"
        reg_label = "Region:" if self.language == "es" else "Region:"
        date_label = "Fecha:" if self.language == "es" else "Date:"

        info_data = [
            [loc_label, project_data.get('location', 'N/A')],
            [ind_label, project_data.get('industry', 'N/A')],
            [reg_label, project_data.get('region', 'N/A')],
            [date_label, datetime.now().strftime("%d/%m/%Y")],
        ]

        info_table = Table(info_data, colWidths=[2.5*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (0, -1), SECONDARY_COLOR),
            ('TEXTCOLOR', (1, 0), (1, -1), DARK_COLOR),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)

        elements.append(Spacer(1, 1.5*inch))

        # Nota de confidencialidad
        conf_text = "DOCUMENTO CONFIDENCIAL" if self.language == "es" else "CONFIDENTIAL DOCUMENT"
        elements.append(Paragraph(
            f"<i>{conf_text}</i>",
            ParagraphStyle(
                name='Confidential',
                fontSize=10,
                textColor=colors.gray,
                alignment=TA_CENTER
            )
        ))

        elements.append(PageBreak())
        return elements

    def _create_toc(self, has_costs: bool, has_timeline: bool) -> list:
        """Crea la tabla de contenidos"""
        elements = []

        toc_title = "Indice" if self.language == "es" else "Table of Contents"
        elements.append(Paragraph(toc_title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 20))

        sections = [
            ("1. " + ("Resumen Ejecutivo" if self.language == "es" else "Executive Summary"), "3"),
            ("2. " + ("Equipo del Proyecto" if self.language == "es" else "Project Team"), "4"),
            ("3. " + ("Objetivos y Alcance" if self.language == "es" else "Objectives and Scope"), "5"),
            ("4. " + ("Fases del Proyecto" if self.language == "es" else "Project Phases"), "6"),
            ("5. " + ("Recursos Necesarios" if self.language == "es" else "Required Resources"), "..."),
            ("6. " + ("Analisis de Riesgos" if self.language == "es" else "Risk Analysis"), "..."),
            ("7. " + ("Metricas de Exito" if self.language == "es" else "Success Metrics"), "..."),
            ("8. " + ("Recomendaciones" if self.language == "es" else "Recommendations"), "..."),
        ]

        if has_costs:
            sections.append(("9. " + ("Proyeccion de Costos" if self.language == "es" else "Cost Projection"), "..."))
        if has_timeline:
            idx = 10 if has_costs else 9
            sections.append((f"{idx}. " + ("Cronograma" if self.language == "es" else "Timeline"), "..."))

        toc_data = [[s[0], "." * 50, s[1]] for s in sections]
        toc_table = Table(toc_data, colWidths=[3*inch, 2.5*inch, 0.5*inch])
        toc_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), PRIMARY_COLOR),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.lightgrey),
            ('TEXTCOLOR', (2, 0), (2, -1), SECONDARY_COLOR),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(toc_table)

        elements.append(PageBreak())
        return elements

    def _create_executive_summary(self, project_plan: dict) -> list:
        """Crea la sección de resumen ejecutivo"""
        elements = []

        title = "Resumen Ejecutivo" if self.language == "es" else "Executive Summary"
        elements.append(Paragraph(title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 15))

        summary = project_plan.get('executive_summary', 'No disponible')
        elements.append(Paragraph(summary, self.styles['CustomBody']))

        # Objetivos
        objectives = project_plan.get('objectives', [])
        if objectives:
            obj_title = "Objetivos Principales" if self.language == "es" else "Main Objectives"
            elements.append(Paragraph(obj_title, self.styles['SubHeader']))

            for i, obj in enumerate(objectives, 1):
                elements.append(Paragraph(f"<b>{i}.</b> {obj}", self.styles['CustomBody']))

        elements.append(PageBreak())
        return elements

    def _create_team_section(self, team_data: dict) -> list:
        """Crea la sección del equipo"""
        elements = []

        title = "Equipo del Proyecto" if self.language == "es" else "Project Team"
        elements.append(Paragraph(title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 15))

        # Resumen del equipo
        summary = team_data.get('team_summary', '')
        if summary:
            elements.append(Paragraph(summary, self.styles['CustomBody']))
            elements.append(Spacer(1, 15))

        # Tamaño del equipo
        team_size = team_data.get('team_size', 0)
        size_text = f"Tamano del equipo: {team_size} profesionales" if self.language == "es" else f"Team size: {team_size} professionals"
        elements.append(Paragraph(f"<b>{size_text}</b>", self.styles['CustomBody']))
        elements.append(Spacer(1, 20))

        # Cada profesional
        for prof in team_data.get('professionals', []):
            # Caja para cada profesional
            role_style = ParagraphStyle(
                name='RoleTitle_' + str(hash(prof.get('role', ''))),
                fontSize=13,
                textColor=PRIMARY_COLOR,
                fontName='Helvetica-Bold'
            )

            prof_data = [
                [Paragraph(f"<b>{prof.get('role', 'Rol')}</b>", role_style)],
                [Paragraph(f"<i>{prof.get('profile_description', '')}</i>", self.styles['CustomBody'])],
                [Paragraph(f"<b>{'Experiencia:' if self.language == 'es' else 'Experience:'}</b> {prof.get('experience_years', 'N/A')}", self.styles['CustomBody'])],
                [Paragraph(f"<b>{'Dedicacion:' if self.language == 'es' else 'Dedication:'}</b> {prof.get('dedication_percentage', 100)}%", self.styles['CustomBody'])],
            ]

            # Skills
            skills = prof.get('key_skills', [])
            if skills:
                skills_text = ", ".join(skills)
                prof_data.append([Paragraph(f"<b>{'Habilidades:' if self.language == 'es' else 'Skills:'}</b> {skills_text}", self.styles['CustomBody'])])

            # Responsabilidades
            responsibilities = prof.get('responsibilities', [])
            if responsibilities:
                resp_text = " - ".join(responsibilities)
                prof_data.append([Paragraph(f"<b>{'Responsabilidades:' if self.language == 'es' else 'Responsibilities:'}</b> {resp_text}", self.styles['CustomBody'])])

            prof_table = Table(prof_data, colWidths=[6*inch])
            prof_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.95, 0.97, 1)),
                ('BOX', (0, 0), (-1, -1), 1, colors.Color(0.8, 0.85, 0.9)),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(prof_table)
            elements.append(Spacer(1, 15))

        elements.append(PageBreak())
        return elements

    def _create_scope_section(self, project_plan: dict) -> list:
        """Crea la sección de alcance"""
        elements = []

        title = "Objetivos y Alcance" if self.language == "es" else "Objectives and Scope"
        elements.append(Paragraph(title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 15))

        scope = project_plan.get('scope', {})

        # Incluido
        included = scope.get('included', [])
        if included:
            inc_title = "Incluido en el Alcance" if self.language == "es" else "Included in Scope"
            elements.append(Paragraph(inc_title, self.styles['SubHeader']))
            for item in included:
                elements.append(Paragraph(f"* {item}", self.styles['CustomBody']))
            elements.append(Spacer(1, 15))

        # Excluido
        excluded = scope.get('excluded', [])
        if excluded:
            exc_title = "Excluido del Alcance" if self.language == "es" else "Excluded from Scope"
            elements.append(Paragraph(exc_title, self.styles['SubHeader']))
            for item in excluded:
                elements.append(Paragraph(f"* {item}", self.styles['CustomBody']))

        elements.append(PageBreak())
        return elements

    def _create_phases_section(self, project_plan: dict, detail_level: str) -> list:
        """Crea la sección de fases del proyecto"""
        elements = []

        title = "Fases del Proyecto" if self.language == "es" else "Project Phases"
        elements.append(Paragraph(title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 15))

        phases = project_plan.get('phases', [])

        for phase in phases:
            # Header de fase
            phase_name_style = ParagraphStyle(
                name='PhaseName_' + str(phase.get('phase_number', '')),
                fontSize=16,
                textColor=PRIMARY_COLOR,
                fontName='Helvetica-Bold'
            )

            phase_header = [
                [Paragraph(f"<b>FASE {phase.get('phase_number', '')}</b>", self.styles['PhaseNumber']),
                 Paragraph(f"<b>{phase.get('phase_name', '')}</b>", phase_name_style)]
            ]

            phase_table = Table(phase_header, colWidths=[1*inch, 5*inch])
            phase_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.93, 0.97, 1)),
                ('BOX', (0, 0), (-1, -1), 2, ACCENT_COLOR),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(phase_table)
            elements.append(Spacer(1, 10))

            # Descripción
            elements.append(Paragraph(phase.get('description', ''), self.styles['CustomBody']))

            # Duración
            duration = phase.get('duration', '')
            if duration:
                dur_text = f"{'Duracion:' if self.language == 'es' else 'Duration:'} {duration}"
                elements.append(Paragraph(f"<b>{dur_text}</b>", self.styles['CustomBody']))

            # Entregables
            deliverables = phase.get('deliverables', [])
            if deliverables:
                del_title = "Entregables:" if self.language == "es" else "Deliverables:"
                elements.append(Paragraph(f"<b>{del_title}</b>", self.styles['CustomBody']))
                for d in deliverables:
                    elements.append(Paragraph(f"   * {d}", self.styles['CustomBody']))

            # Tareas (para nivel detallado y ultra)
            if detail_level in ['detailed', 'ultra']:
                tasks = phase.get('tasks', [])
                if tasks:
                    task_title = "Tareas:" if self.language == "es" else "Tasks:"
                    elements.append(Paragraph(f"<b>{task_title}</b>", self.styles['CustomBody']))

                    for task in tasks:
                        task_name = task.get('task_name', '')
                        responsible = task.get('responsible', '')
                        task_duration = task.get('duration', '')

                        task_text = f"<b>- {task_name}</b>"
                        if responsible:
                            task_text += f" | {'Responsable:' if self.language == 'es' else 'Responsible:'} {responsible}"
                        if task_duration:
                            task_text += f" | {task_duration}"

                        elements.append(Paragraph(task_text, self.styles['CustomBody']))

                        # Descripción de tarea
                        task_desc = task.get('description', '')
                        if task_desc:
                            elements.append(Paragraph(f"   <i>{task_desc}</i>", self.styles['CustomBody']))

                        # Subtareas (solo ultra)
                        if detail_level == 'ultra':
                            subtasks = task.get('subtasks', [])
                            if subtasks:
                                for st in subtasks:
                                    elements.append(Paragraph(f"      o {st}", self.styles['CustomBody']))

                            # Criterios de aceptación
                            criteria = task.get('acceptance_criteria', [])
                            if criteria:
                                crit_title = "Criterios de aceptacion:" if self.language == 'es' else "Acceptance criteria:"
                                elements.append(Paragraph(f"      <b>{crit_title}</b>", self.styles['CustomBody']))
                                for c in criteria:
                                    elements.append(Paragraph(f"      + {c}", self.styles['CustomBody']))

            # Hitos
            milestones = phase.get('milestones', [])
            if milestones:
                mil_title = "Hitos:" if self.language == "es" else "Milestones:"
                elements.append(Paragraph(f"<b>{mil_title}</b>", self.styles['CustomBody']))
                for m in milestones:
                    elements.append(Paragraph(f"   >> {m}", self.styles['CustomBody']))

            elements.append(Spacer(1, 25))

        elements.append(PageBreak())
        return elements

    def _create_resources_section(self, project_plan: dict) -> list:
        """Crea la sección de recursos"""
        elements = []

        title = "Recursos Necesarios" if self.language == "es" else "Required Resources"
        elements.append(Paragraph(title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 15))

        resources = project_plan.get('resources', {})

        # Recursos humanos
        human = resources.get('human', [])
        if human:
            h_title = "Recursos Humanos" if self.language == "es" else "Human Resources"
            elements.append(Paragraph(h_title, self.styles['SubHeader']))
            for h in human:
                elements.append(Paragraph(f"* {h}", self.styles['CustomBody']))
            elements.append(Spacer(1, 15))

        # Recursos técnicos
        technical = resources.get('technical', [])
        if technical:
            t_title = "Herramientas y Tecnologias" if self.language == "es" else "Tools and Technologies"
            elements.append(Paragraph(t_title, self.styles['SubHeader']))
            for t in technical:
                elements.append(Paragraph(f"* {t}", self.styles['CustomBody']))
            elements.append(Spacer(1, 15))

        # Infraestructura
        infrastructure = resources.get('infrastructure', [])
        if infrastructure:
            i_title = "Infraestructura" if self.language == "es" else "Infrastructure"
            elements.append(Paragraph(i_title, self.styles['SubHeader']))
            for i in infrastructure:
                elements.append(Paragraph(f"* {i}", self.styles['CustomBody']))

        elements.append(PageBreak())
        return elements

    def _create_risks_section(self, project_plan: dict) -> list:
        """Crea la sección de riesgos"""
        elements = []

        title = "Analisis de Riesgos" if self.language == "es" else "Risk Analysis"
        elements.append(Paragraph(title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 15))

        risks = project_plan.get('risks', [])

        if risks:
            # Tabla de riesgos
            header = [
                "Riesgo" if self.language == "es" else "Risk",
                "Prob." if self.language == "es" else "Prob.",
                "Impacto" if self.language == "es" else "Impact",
                "Mitigacion" if self.language == "es" else "Mitigation"
            ]

            risk_data = [header]
            for r in risks:
                risk_data.append([
                    Paragraph(r.get('risk', ''), self.styles['CustomBody']),
                    r.get('probability', 'N/A'),
                    r.get('impact', 'N/A'),
                    Paragraph(r.get('mitigation', ''), self.styles['CustomBody'])
                ])

            risk_table = Table(risk_data, colWidths=[2*inch, 0.7*inch, 0.7*inch, 2.5*inch])
            risk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (2, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 1), (-1, -1), colors.Color(0.98, 0.98, 0.98)),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(risk_table)

        elements.append(PageBreak())
        return elements

    def _create_metrics_section(self, project_plan: dict) -> list:
        """Crea la sección de métricas de éxito"""
        elements = []

        title = "Metricas de Exito" if self.language == "es" else "Success Metrics"
        elements.append(Paragraph(title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 15))

        metrics = project_plan.get('success_metrics', [])
        for i, m in enumerate(metrics, 1):
            elements.append(Paragraph(f"<b>{i}.</b> {m}", self.styles['CustomBody']))

        elements.append(Spacer(1, 30))

        # Recomendaciones
        rec_title = "Recomendaciones" if self.language == "es" else "Recommendations"
        elements.append(Paragraph(rec_title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 15))

        recommendations = project_plan.get('recommendations', [])
        for r in recommendations:
            elements.append(Paragraph(f"-> {r}", self.styles['CustomBody']))

        elements.append(PageBreak())
        return elements

    def _create_costs_section(self, project_plan: dict) -> list:
        """Crea la sección de costos"""
        elements = []

        title = "Proyeccion de Costos" if self.language == "es" else "Cost Projection"
        elements.append(Paragraph(title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 15))

        costs = project_plan.get('costs', {})

        if not costs:
            elements.append(Paragraph("No se genero proyeccion de costos.", self.styles['CustomBody']))
            return elements

        # Costos del equipo
        team_costs = costs.get('team_costs', [])
        if team_costs:
            tc_title = "Costos del Equipo" if self.language == "es" else "Team Costs"
            elements.append(Paragraph(tc_title, self.styles['SubHeader']))

            header = ["Rol", "$/Mes", "Meses", "Total USD"]
            tc_data = [header]
            for tc in team_costs:
                tc_data.append([
                    tc.get('role', ''),
                    f"${tc.get('monthly_cost', 0):,.0f}",
                    str(tc.get('duration_months', 0)),
                    f"${tc.get('total', 0):,.0f}"
                ])

            tc_table = Table(tc_data, colWidths=[2.5*inch, 1.2*inch, 0.8*inch, 1.5*inch])
            tc_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), SECONDARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(tc_table)
            elements.append(Spacer(1, 20))

        # Costos de infraestructura
        infra_costs = costs.get('infrastructure_costs', [])
        if infra_costs:
            ic_title = "Costos de Infraestructura" if self.language == "es" else "Infrastructure Costs"
            elements.append(Paragraph(ic_title, self.styles['SubHeader']))

            for ic in infra_costs:
                elements.append(Paragraph(f"* {ic.get('item', '')}: ${ic.get('cost', 0):,.0f} USD", self.styles['CustomBody']))
            elements.append(Spacer(1, 20))

        # Costos operativos
        op_costs = costs.get('operational_costs', [])
        if op_costs:
            oc_title = "Costos Operativos" if self.language == "es" else "Operational Costs"
            elements.append(Paragraph(oc_title, self.styles['SubHeader']))

            for oc in op_costs:
                elements.append(Paragraph(
                    f"* {oc.get('item', '')}: ${oc.get('monthly_cost', 0):,.0f}/mes x {oc.get('duration_months', 0)} meses = ${oc.get('total', 0):,.0f} USD",
                    self.styles['CustomBody']
                ))
            elements.append(Spacer(1, 20))

        # Contingencia y totales
        contingency = costs.get('contingency_percentage', 10)
        total_min = costs.get('total_min', 0)
        total_max = costs.get('total_max', 0)

        # Caja de totales
        totals_data = [
            [f"{'Contingencia:' if self.language == 'es' else 'Contingency:'}", f"{contingency}%"],
            [f"{'TOTAL ESTIMADO:' if self.language == 'es' else 'ESTIMATED TOTAL:'}",
             f"${total_min:,.0f} - ${total_max:,.0f} USD"]
        ]

        totals_table = Table(totals_data, colWidths=[2*inch, 3*inch])
        totals_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.95, 0.98, 0.95)),
            ('BOX', (0, 0), (-1, -1), 2, ACCENT_COLOR),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('TEXTCOLOR', (0, -1), (-1, -1), PRIMARY_COLOR),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ]))
        elements.append(totals_table)

        elements.append(PageBreak())
        return elements

    def _create_timeline_section(self, project_plan: dict) -> list:
        """Crea la sección de cronograma"""
        elements = []

        title = "Cronograma" if self.language == "es" else "Timeline"
        elements.append(Paragraph(title, self.styles['SectionHeader']))
        elements.append(Spacer(1, 15))

        timeline = project_plan.get('timeline', {})

        if not timeline:
            elements.append(Paragraph("No se genero cronograma.", self.styles['CustomBody']))
            return elements

        # Información general
        total_duration = timeline.get('total_duration', 'N/A')
        elements.append(Paragraph(
            f"<b>{'Duracion Total:' if self.language == 'es' else 'Total Duration:'}</b> {total_duration}",
            self.styles['CustomBody']
        ))

        start_date = timeline.get('start_date', 'A definir')
        end_date = timeline.get('end_date', 'A definir')
        elements.append(Paragraph(
            f"<b>{'Inicio:' if self.language == 'es' else 'Start:'}</b> {start_date} -> <b>{'Fin:' if self.language == 'es' else 'End:'}</b> {end_date}",
            self.styles['CustomBody']
        ))
        elements.append(Spacer(1, 20))

        # Ruta crítica
        critical_path = timeline.get('critical_path', [])
        if critical_path:
            cp_title = "Ruta Critica" if self.language == "es" else "Critical Path"
            elements.append(Paragraph(cp_title, self.styles['SubHeader']))
            cp_text = " -> ".join(critical_path)
            elements.append(Paragraph(cp_text, self.styles['CustomBody']))
            elements.append(Spacer(1, 20))

        # Hitos con timeline
        milestones_tl = timeline.get('milestones_timeline', [])
        if milestones_tl:
            mt_title = "Hitos del Proyecto" if self.language == "es" else "Project Milestones"
            elements.append(Paragraph(mt_title, self.styles['SubHeader']))

            header = [
                "Hito" if self.language == "es" else "Milestone",
                "Semana" if self.language == "es" else "Week"
            ]
            mt_data = [header]
            for m in milestones_tl:
                mt_data.append([m.get('milestone', ''), f"Semana {m.get('week', 'N/A')}"])

            mt_table = Table(mt_data, colWidths=[4*inch, 1.5*inch])
            mt_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(mt_table)

        return elements

    def generate_pdf(self, project_data: dict, team_data: dict, project_plan: dict, options: dict) -> BytesIO:
        """Genera el PDF completo"""
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=60,
            bottomMargin=50
        )

        elements = []

        # Portada
        elements.extend(self._create_cover_page(project_data))

        # Índice
        has_costs = options.get('include_costs', False) and 'costs' in project_plan
        has_timeline = options.get('include_timeline', False) and 'timeline' in project_plan
        elements.extend(self._create_toc(has_costs, has_timeline))

        # Resumen ejecutivo
        elements.extend(self._create_executive_summary(project_plan))

        # Equipo
        elements.extend(self._create_team_section(team_data))

        # Alcance
        elements.extend(self._create_scope_section(project_plan))

        # Fases
        detail_level = options.get('detail_level', 'detailed')
        elements.extend(self._create_phases_section(project_plan, detail_level))

        # Recursos
        elements.extend(self._create_resources_section(project_plan))

        # Riesgos
        elements.extend(self._create_risks_section(project_plan))

        # Métricas y Recomendaciones
        elements.extend(self._create_metrics_section(project_plan))

        # Costos (si aplica)
        if has_costs:
            elements.extend(self._create_costs_section(project_plan))

        # Cronograma (si aplica)
        if has_timeline:
            elements.extend(self._create_timeline_section(project_plan))

        # Construir PDF con marca de agua
        doc.build(elements, onFirstPage=self._add_watermark, onLaterPages=self._add_watermark)

        buffer.seek(0)
        return buffer


# ==============================================================================
# EMAIL SENDER
# ==============================================================================
def validate_email(email: str) -> bool:
    """Valida formato básico de email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def send_project_email(recipient_email: str, project_name: str, pdf_buffer: BytesIO, language: str = "es") -> bool:
    """
    Envía el PDF del proyecto por email.
    """

    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("Error: Credenciales SMTP no configuradas")
        return False

    # Contenido del email según idioma
    if language == "es":
        subject = f"🚀 ProjectTeam 100 - Plan de Proyecto: {project_name}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px;">
                    <h1 style="color: white; margin: 0;">🚀 ProjectTeam 100</h1>
                    <p style="color: rgba(255,255,255,0.9); margin-top: 10px;">Plan de Proyecto Multidisciplinario</p>
                </div>

                <div style="padding: 30px 0;">
                    <h2 style="color: #1E3A5F;">¡Tu plan de proyecto está listo!</h2>

                    <p>Hemos generado el plan completo para tu proyecto:</p>

                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #00D4AA;">
                        <h3 style="color: #1E3A5F; margin-top: 0;">{project_name}</h3>
                        <p style="color: #666; margin-bottom: 0;">Generado el {datetime.now().strftime("%d de %B, %Y a las %H:%M")}</p>
                    </div>

                    <p style="margin-top: 20px;">El documento PDF adjunto incluye:</p>
                    <ul style="color: #555;">
                        <li>✅ Resumen ejecutivo</li>
                        <li>✅ Equipo multidisciplinario asignado</li>
                        <li>✅ Fases detalladas del proyecto</li>
                        <li>✅ Análisis de riesgos</li>
                        <li>✅ Métricas de éxito</li>
                        <li>✅ Y más...</li>
                    </ul>
                </div>

                <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <p style="color: #888; font-size: 12px; margin: 0;">
                        Este email fue generado automáticamente por ProjectTeam 100.<br>
                        © {datetime.now().year} ProjectTeam 100 - Todos los derechos reservados.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    else:
        subject = f"🚀 ProjectTeam 100 - Project Plan: {project_name}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px;">
                    <h1 style="color: white; margin: 0;">🚀 ProjectTeam 100</h1>
                    <p style="color: rgba(255,255,255,0.9); margin-top: 10px;">Multidisciplinary Project Plan</p>
                </div>

                <div style="padding: 30px 0;">
                    <h2 style="color: #1E3A5F;">Your project plan is ready!</h2>

                    <p>We have generated the complete plan for your project:</p>

                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #00D4AA;">
                        <h3 style="color: #1E3A5F; margin-top: 0;">{project_name}</h3>
                        <p style="color: #666; margin-bottom: 0;">Generated on {datetime.now().strftime("%B %d, %Y at %H:%M")}</p>
                    </div>

                    <p style="margin-top: 20px;">The attached PDF document includes:</p>
                    <ul style="color: #555;">
                        <li>✅ Executive summary</li>
                        <li>✅ Assigned multidisciplinary team</li>
                        <li>✅ Detailed project phases</li>
                        <li>✅ Risk analysis</li>
                        <li>✅ Success metrics</li>
                        <li>✅ And more...</li>
                    </ul>
                </div>

                <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <p style="color: #888; font-size: 12px; margin: 0;">
                        This email was automatically generated by ProjectTeam 100.<br>
                        © {datetime.now().year} ProjectTeam 100 - All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    try:
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Agregar cuerpo HTML
        msg.attach(MIMEText(body, 'html'))

        # Agregar PDF adjunto
        pdf_attachment = MIMEBase('application', 'octet-stream')
        pdf_buffer.seek(0)
        pdf_attachment.set_payload(pdf_buffer.read())
        encoders.encode_base64(pdf_attachment)

        # Nombre del archivo
        safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"ProjectTeam100_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_attachment.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(pdf_attachment)

        # Conectar y enviar
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"Email enviado exitosamente a {recipient_email}")
        return True

    except Exception as e:
        print(f"Error enviando email: {e}")
        return False


# ==============================================================================
# FLASK APP
# ==============================================================================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Almacenamiento temporal en memoria para sesiones
sessions = {}

# Auth Routes
@app.route('/auth/login-page')
def auth_login_page():
    if firebase_auth.is_user_logged_in():
        return redirect(url_for('index'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/auth/login', methods=['POST'])
def auth_login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not email or not password:
        flash('Por favor completa todos los campos.', 'danger')
        return redirect(url_for('auth_login_page'))

    result = firebase_auth.login_user(email, password)

    if result['success']:
        firebase_auth.set_user_session(result['user_data'])
        flash(result['message'], 'success')
        return redirect(url_for('index'))
    else:
        flash(result['message'], 'danger')
        return redirect(url_for('auth_login_page'))

@app.route('/auth/logout')
def auth_logout():
    firebase_auth.clear_user_session()
    flash('Has cerrado la sesion correctamente.', 'success')
    return redirect(url_for('auth_login_page'))


@app.route('/')
@login_required
def index():
    """Página principal"""
    return render_template_string(HTML_TEMPLATE,
                         industries=INDUSTRIES,
                         regions=REGIONS,
                         detail_levels=DETAIL_LEVELS)


@app.route('/api/generate-questions', methods=['POST'])
@login_required
def api_generate_questions():
    """Genera preguntas de clarificación basadas en datos iniciales"""
    try:
        data = request.json

        project_data = {
            'name': data.get('name', ''),
            'description': data.get('description', ''),
            'industry': data.get('industry', ''),
            'location': data.get('location', ''),
            'region': data.get('region', 'global')
        }

        language = data.get('language', 'es')

        # Generar preguntas
        questions = generate_clarification_questions(project_data, language)

        # Guardar en sesión temporal
        session_id = data.get('session_id', str(datetime.now().timestamp()))
        sessions[session_id] = {
            'project_data': project_data,
            'questions': questions,
            'answers': [],
            'language': language
        }

        print(f"[OK] Sesion creada: {session_id}")

        return jsonify({
            'success': True,
            'session_id': session_id,
            'questions': questions,
            'total_questions': len(questions)
        })

    except Exception as e:
        print(f"[ERROR] generate-questions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/submit-answer', methods=['POST'])
@login_required
def api_submit_answer():
    """Recibe respuesta a una pregunta"""
    try:
        data = request.json
        session_id = data.get('session_id')
        answer = data.get('answer', '')
        question_index = data.get('question_index', 0)

        if session_id not in sessions:
            return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404

        session = sessions[session_id]

        # Agregar respuesta
        if len(session['answers']) <= question_index:
            session['answers'].append(answer)
        else:
            session['answers'][question_index] = answer

        print(f"[OK] Respuesta {question_index + 1} guardada")

        # Verificar si hay más preguntas
        total_questions = len(session['questions'])
        next_index = question_index + 1

        if next_index < total_questions:
            return jsonify({
                'success': True,
                'has_more': True,
                'next_question': session['questions'][next_index],
                'next_index': next_index,
                'progress': f"{next_index + 1}/{total_questions}"
            })
        else:
            return jsonify({
                'success': True,
                'has_more': False,
                'message': 'Todas las preguntas respondidas'
            })

    except Exception as e:
        print(f"[ERROR] submit-answer: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generate-project', methods=['POST'])
@login_required
def api_generate_project():
    """Genera el proyecto completo con equipo y plan"""
    try:
        data = request.json
        session_id = data.get('session_id')

        print(f"[...] Generando proyecto para sesion: {session_id}")

        if session_id not in sessions:
            return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404

        session = sessions[session_id]
        project_data = session['project_data'].copy()
        project_data['questions'] = session['questions']
        project_data['answers'] = session['answers']
        language = session['language']

        options = {
            'detail_level': data.get('detail_level', 'detailed'),
            'include_costs': data.get('include_costs', False),
            'include_timeline': data.get('include_timeline', False)
        }

        # Generar equipo
        print("[...] Generando equipo...")
        team_data = generate_project_team(project_data, session['answers'], language)
        print(f"[OK] Equipo: {team_data.get('team_size', 0)} profesionales")

        # Generar proyecto completo
        print("[...] Generando plan...")
        project_plan = generate_full_project(project_data, team_data, options, language)
        print(f"[OK] Plan: {len(project_plan.get('phases', []))} fases")

        # Guardar en sesión
        session['team_data'] = team_data
        session['project_plan'] = project_plan
        session['options'] = options
        session['project_data'] = project_data

        # GENERAR PDF INMEDIATAMENTE
        print("[...] Generando PDF...")
        try:
            pdf_gen = PDFGenerator(language)
            pdf_buffer = pdf_gen.generate_pdf(project_data, team_data, project_plan, options)
            session['pdf_buffer'] = pdf_buffer
            print("[OK] PDF generado!")
        except Exception as pdf_error:
            print(f"[WARN] Error PDF: {pdf_error}")
            session['pdf_buffer'] = None

        return jsonify({
            'success': True,
            'team_size': team_data.get('team_size', 0),
            'team_summary': team_data.get('team_summary', ''),
            'phases_count': len(project_plan.get('phases', [])),
            'message': 'Proyecto generado exitosamente'
        })

    except Exception as e:
        print(f"[ERROR] generate-project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generate-pdf', methods=['POST'])
@login_required
def api_generate_pdf():
    """Genera el PDF y lo envía por email"""
    try:
        data = request.json
        session_id = data.get('session_id')
        email = data.get('email', '')

        print(f"[...] Preparando PDF para: {session_id}")

        if session_id not in sessions:
            return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404

        session = sessions[session_id]

        # Verificar que el proyecto esté generado
        if 'project_plan' not in session:
            return jsonify({'success': False, 'error': 'El proyecto no ha sido generado'}), 400

        project_data = session['project_data']
        team_data = session['team_data']
        project_plan = session['project_plan']
        options = session['options']
        language = session['language']

        # Generar PDF si no existe
        if 'pdf_buffer' not in session or session['pdf_buffer'] is None:
            print("[...] Generando PDF...")
            pdf_gen = PDFGenerator(language)
            pdf_buffer = pdf_gen.generate_pdf(project_data, team_data, project_plan, options)
            session['pdf_buffer'] = pdf_buffer
            print("[OK] PDF generado!")

        # Enviar por email si es válido
        email_sent = False
        if email and validate_email(email):
            session['pdf_buffer'].seek(0)
            email_sent = send_project_email(email, project_data['name'], session['pdf_buffer'], language)
            print(f"[OK] Email enviado: {email_sent}")

        return jsonify({
            'success': True,
            'email_sent': email_sent,
            'message': 'PDF generado' + (' y enviado por email' if email_sent else '')
        })

    except Exception as e:
        print(f"[ERROR] generate-pdf: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download-pdf/<session_id>')
@login_required
def api_download_pdf(session_id):
    """Descarga el PDF generado"""
    try:
        print(f"[...] Descargando PDF: {session_id}")

        if session_id not in sessions:
            print("[ERROR] Sesion no encontrada")
            return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404

        session = sessions[session_id]

        # Si no hay PDF, generarlo ahora
        if 'pdf_buffer' not in session or session['pdf_buffer'] is None:
            print("[...] PDF no existe, generando...")

            if 'project_plan' not in session:
                print("[ERROR] Proyecto no generado")
                return jsonify({'success': False, 'error': 'Proyecto no generado. Completa el proceso primero.'}), 400

            try:
                pdf_gen = PDFGenerator(session.get('language', 'es'))
                pdf_buffer = pdf_gen.generate_pdf(
                    session['project_data'],
                    session['team_data'],
                    session['project_plan'],
                    session['options']
                )
                session['pdf_buffer'] = pdf_buffer
                print("[OK] PDF generado!")
            except Exception as e:
                print(f"[ERROR] Generando PDF: {e}")
                return jsonify({'success': False, 'error': f'Error generando PDF: {str(e)}'}), 500

        pdf_buffer = session['pdf_buffer']
        pdf_buffer.seek(0)

        project_name = session['project_data'].get('name', 'Proyecto')
        safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name[:50]
        filename = f"ProjectTeam100_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf"

        print(f"[OK] Enviando: {filename}")

        # Crear copia del buffer
        pdf_copy = BytesIO(pdf_buffer.getvalue())

        return send_file(
            pdf_copy,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"[ERROR] download-pdf: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/preview-team', methods=['POST'])
@login_required
def api_preview_team():
    """Preview del equipo generado"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if session_id not in sessions:
            return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404

        session = sessions[session_id]

        if 'team_data' not in session:
            return jsonify({'success': False, 'error': 'Equipo no generado'}), 400

        return jsonify({
            'success': True,
            'team': session['team_data']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("  ProjectTeam 100 - Servidor Unificado (main6.py)")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
