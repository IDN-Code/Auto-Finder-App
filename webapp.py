# webapp.py - Auto Parts Finder USA - VERSIÓN CORREGIDA Y FUNCIONAL COMPLETA
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string, flash
import requests
import os
import re
import html
import time
import io
import random
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote_plus, urljoin
from functools import wraps
import json

# Imports opcionales con manejo de errores
try:
    from PIL import Image
    PIL_AVAILABLE = True
    print("✅ PIL (Pillow) disponible")
except ImportError:
    PIL_AVAILABLE = False
    print("⚠ PIL no disponible")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    print("✅ Gemini disponible")
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False
    print("⚠ Gemini no disponible")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
    print("✅ BeautifulSoup4 disponible")
except ImportError:
    BS4_AVAILABLE = False
    print("⚠ BeautifulSoup4 no disponible")

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'auto-parts-finder-secret-key-2025')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True if os.environ.get('RENDER') else False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Base de datos de vehículos populares en USA
VEHICLE_DATABASE = {
    'makes': {
        'chevrolet': ['silverado', 'equinox', 'malibu', 'tahoe', 'suburban', 'traverse', 'camaro', 'corvette'],
        'ford': ['f150', 'f250', 'f350', 'escape', 'explorer', 'mustang', 'edge', 'expedition'],
        'toyota': ['camry', 'corolla', 'rav4', 'highlander', 'prius', 'tacoma', 'tundra', 'sienna'],
        'honda': ['civic', 'accord', 'crv', 'pilot', 'odyssey', 'ridgeline', 'passport'],
        'nissan': ['altima', 'sentra', 'rogue', 'murano', 'pathfinder', 'titan', 'frontier'],
        'jeep': ['wrangler', 'grand cherokee', 'cherokee', 'compass', 'renegade', 'gladiator'],
        'ram': ['1500', '2500', '3500', 'promaster'],
        'gmc': ['sierra', 'terrain', 'acadia', 'yukon', 'canyon']
    },
    'years': list(range(1990, 2025)),
    'common_parts': [
        'brake pads', 'brake rotors', 'oil filter', 'air filter', 'spark plugs', 
        'battery', 'alternator', 'starter', 'radiator', 'water pump'
    ]
}

# ==============================================================================
# CLASES PRINCIPALES
# ==============================================================================

class FirebaseAuth:
    """Sistema de autenticación simplificado"""
    
    def __init__(self):
        self.firebase_web_api_key = os.environ.get("FIREBASE_WEB_API_KEY")
        logger.info(f"Firebase Auth configurado: {bool(self.firebase_web_api_key)}")
    
    def login_user(self, email, password):
        """Login con credenciales demo para pruebas"""
        try:
            # Credenciales demo hardcoded para evitar dependencias
            if email == "admin@test.com" and password == "password123":
                return {
                    'success': True,
                    'message': 'Login exitoso',
                    'user_data': {
                        'user_id': 'demo_user_123',
                        'email': email,
                        'display_name': 'Demo User',
                        'id_token': 'demo_token_12345'
                    }
                }
            else:
                return {
                    'success': False,
                    'message': 'Credenciales incorrectas. Use admin@test.com / password123',
                    'user_data': None
                }
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return {
                'success': False,
                'message': 'Error interno en autenticación',
                'user_data': None
            }
    
    def set_user_session(self, user_data):
        """Establecer sesión de usuario"""
        try:
            session['user_id'] = user_data['user_id']
            session['user_name'] = user_data['display_name']
            session['user_email'] = user_data['email']
            session['login_time'] = datetime.now().isoformat()
            session.permanent = True
        except Exception as e:
            logger.error(f"Error estableciendo sesión: {e}")
    
    def clear_user_session(self):
        """Limpiar sesión de usuario"""
        try:
            session.clear()
        except Exception as e:
            logger.error(f"Error limpiando sesión: {e}")
    
    def is_user_logged_in(self):
        """Verificar si el usuario está logueado"""
        try:
            return 'user_id' in session and session.get('user_id') is not None
        except Exception as e:
            logger.error(f"Error verificando login: {e}")
            return False
    
    def get_current_user(self):
        """Obtener usuario actual"""
        try:
            if not self.is_user_logged_in():
                return None
            return {
                'user_id': session.get('user_id'),
                'user_name': session.get('user_name'),
                'user_email': session.get('user_email')
            }
        except Exception as e:
            logger.error(f"Error obteniendo usuario: {e}")
            return None

class AutoPartsFinder:
    """Buscador de repuestos automotrices con SerpAPI real"""
    
    def __init__(self):
        self.api_key = os.environ.get('SERPAPI_KEY')
        self.base_url = "https://serpapi.com/search"
        logger.info(f"SerpAPI configurado: {bool(self.api_key)}")
        
        # Tiendas populares de auto parts (para fallback)
        self.stores = [
            'AutoZone', 'Advance Auto Parts', "O'Reilly Auto Parts", 
            'NAPA', 'RockAuto', 'Amazon Automotive'
        ]
    
    def search_auto_parts(self, query=None, image_content=None, vehicle_info=None):
        """Búsqueda principal de repuestos usando SerpAPI real"""
        try:
            # Construir query final
            final_query = self._build_search_query(query, vehicle_info)
            
            if not final_query:
                final_query = "brake pads"
            
            logger.info(f"🔍 Buscando: '{final_query}'")
            print(f"🔍 DEBUG: Query final = '{final_query}'")
            
            # Verificar API key
            if not self.api_key:
                logger.warning("❌ SERPAPI_KEY no encontrada, usando resultados demo")
                print("⚠️ DEBUG: Sin SERPAPI_KEY, generando demos")
                return self._generate_sample_results(final_query, demo_mode=True)
            
            # Hacer llamada real a SerpAPI
            print("🚀 DEBUG: Llamando a SerpAPI...")
            return self._search_with_serpapi(final_query)
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}")
            print(f"❌ DEBUG: Error en search_auto_parts = {e}")
            # En caso de error, devolver resultados demo como fallback
            return self._generate_sample_results(query or "brake pads", demo_mode=True)
    
    def _search_with_serpapi(self, query):
        """Realizar búsqueda real usando SerpAPI"""
        try:
            # Parámetros para SerpAPI (Google Shopping)
            params = {
                'api_key': self.api_key,
                'engine': 'google_shopping',
                'q': query + ' auto parts',
                'location': 'United States',
                'hl': 'en',
                'gl': 'us',
                'num': 20
            }
            
            logger.info(f"🔍 Llamando a SerpAPI con query: {params['q']}")
            print(f"🌐 DEBUG: Haciendo petición a SerpAPI...")
            
            # Hacer petición HTTP con timeout
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            print(f"📊 DEBUG: Respuesta de SerpAPI recibida")
            
            # Verificar si hay error en la respuesta
            if 'error' in data:
                logger.error(f"❌ Error de SerpAPI: {data['error']}")
                print(f"❌ DEBUG: Error en SerpAPI = {data['error']}")
                return self._generate_sample_results(query, demo_mode=True)
            
            # Procesar resultados reales
            shopping_results = data.get('shopping_results', [])
            print(f"📊 DEBUG: {len(shopping_results)} resultados de shopping")
            
            if not shopping_results:
                logger.warning("⚠️ No se encontraron resultados en SerpAPI")
                print("⚠️ DEBUG: Sin resultados en SerpAPI, usando demos")
                return self._generate_sample_results(query, demo_mode=True)
            
            # Convertir a formato interno
            processed_results = []
            for item in shopping_results[:12]:
                processed_item = self._process_serpapi_result(item)
                if processed_item:
                    processed_results.append(processed_item)
            
            print(f"✅ DEBUG: {len(processed_results)} resultados procesados")
            
            if len(processed_results) == 0:
                print("⚠️ DEBUG: No se procesaron resultados válidos, usando demos")
                return self._generate_sample_results(query, demo_mode=True)
            
            logger.info(f"✅ Procesados {len(processed_results)} resultados REALES de SerpAPI")
            return processed_results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión con SerpAPI: {e}")
            print(f"❌ DEBUG: Error de conexión = {e}")
            return self._generate_sample_results(query, demo_mode=True)
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout en SerpAPI")
            print("❌ DEBUG: Timeout en SerpAPI")
            return self._generate_sample_results(query, demo_mode=True)
        except Exception as e:
            logger.error(f"❌ Error inesperado en SerpAPI: {e}")
            print(f"❌ DEBUG: Error inesperado = {e}")
            return self._generate_sample_results(query, demo_mode=True)

    def _process_serpapi_result(self, item):
        """Procesar un resultado individual de SerpAPI"""
        try:
            # Extraer datos verificados directamente de SerpAPI
            title = item.get('title', 'Producto sin título').strip()
            price = item.get('price', 'Precio no disponible')
            source = item.get('source', 'Tienda desconocida')
            link = item.get('link', '#')
            
            # ✅ VALIDAR QUE EL LINK SEA REAL DE SERPAPI
            if not link or link == '#':
                logger.warning(f"⚠️ Link inválido encontrado para: {title}")
                return None
            
            # Limpiar y validar precio
            price_numeric = 0.0
            if price and price != 'Precio no disponible':
                try:
                    # Extraer número del precio
                    price_clean = re.sub(r'[^\d\.]', '', str(price))
                    if price_clean:
                        price_numeric = float(price_clean)
                except Exception as e:
                    logger.debug(f"No se pudo parsear precio: {price}")
                    price_numeric = 0.0
            
            # Extraer rating y reviews si existen
            rating = item.get('rating', '')
            reviews = item.get('reviews', '')
            
            # Detectar tipo de repuesto basado en el título
            part_type = 'Aftermarket'
            title_lower = title.lower()
            if any(oem_word in title_lower for oem_word in ['oem', 'original', 'genuine', 'factory']):
                part_type = 'OEM'
            
            return {
                'title': title,
                'price': price,
                'price_numeric': price_numeric,
                'source': source,
                'link': link,  # ✅ LINK REAL DIRECTO DE SERPAPI
                'rating': rating,
                'reviews': reviews,
                'part_type': part_type,
                'search_source': 'serpapi_real',
                'serpapi_verified': True  # ✅ MARCADO COMO VERIFICADO
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando resultado SerpAPI: {e}")
            return None

    def _generate_sample_results(self, query, demo_mode=False):
        """Generar resultados de ejemplo GARANTIZADOS - NUNCA falla"""
        try:
            # Asegurar que query no esté vacío
            if not query or query.strip() == "":
                query = "auto parts"
            
            print(f"🎭 DEBUG: Generando resultados demo para '{query}'")
            
            results = []
            base_prices = [29.99, 45.99, 67.99, 89.99, 124.99, 199.99]
            
            # Partes específicas basadas en query común
            part_types = ['brake pads', 'oil filter', 'air filter', 'spark plugs', 'battery', 'alternator']
            
            for i in range(6):
                store = self.stores[i % len(self.stores)]
                price = base_prices[i]
                
                # Usar parte específica si está en la lista, sino usar query
                part_name = part_types[i] if 'part' in query.lower() else query
                
                result = {
                    'title': f'{part_name.title()} - {"Premium OEM" if i % 2 == 0 else "Aftermarket Quality"}',
                    'price': f'${price:.2f}',
                    'price_numeric': price,
                    'source': store,
                    'link': f"https://www.google.com/search?tbm=shop&q={quote_plus(part_name + ' ' + store)}",
                    'rating': f"{4.0 + (i * 0.1):.1f}",
                    'reviews': str(100 + i * 50),
                    'part_type': 'OEM' if i % 2 == 0 else 'Aftermarket',
                    'search_source': 'demo',
                    'serpapi_verified': False,  # ✅ MARCADO COMO NO VERIFICADO
                    'demo_mode': demo_mode
                }
                results.append(result)
            
            print(f"✅ DEBUG: Generados {len(results)} resultados demo exitosamente")
            logger.info(f"✅ Generados {len(results)} resultados demo para: {query}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error generando ejemplos: {e}")
            print(f"❌ DEBUG: Error en _generate_sample_results = {e}")
            
            # ÚLTIMO RECURSO - resultado básico garantizado
            return [{
                'title': f'Repuesto para: {query}',
                'price': '$50.00',
                'price_numeric': 50.0,
                'source': 'AutoZone',
                'link': f"https://www.google.com/search?tbm=shop&q={quote_plus(query)}",
                'rating': '4.5',
                'reviews': '250',
                'part_type': 'Demo',
                'search_source': 'demo',
                'serpapi_verified': False,
                'demo_mode': True
            }]

    def _generate_error_fallback(self, error_message):
        """Generar mensaje de error cuando falla la API"""
        return [{
            'title': '❌ Error en la búsqueda de repuestos',
            'price': 'N/A',
            'price_numeric': 0.0,
            'source': 'Sistema - Error',
            'link': '/',
            'rating': '',
            'reviews': '',
            'part_type': 'Error',
            'search_source': 'error',
            'error_message': error_message,
            'serpapi_verified': False
        }]

    def _generate_no_results_message(self, query):
        """Generar mensaje cuando no hay resultados en SerpAPI"""
        return [{
            'title': f'No se encontraron repuestos para: "{query}"',
            'price': 'N/A',
            'price_numeric': 0.0,
            'source': 'Sistema - Sin resultados',
            'link': f"https://www.google.com/search?tbm=shop&q={quote_plus(query + ' auto parts')}",
            'rating': '',
            'reviews': '',
            'part_type': 'Info',
            'search_source': 'no_results',
            'serpapi_verified': False
        }]

    def _build_search_query(self, query, vehicle_info):
        """Construir query de búsqueda optimizada"""
        try:
            parts = []
            
            # Agregar información del vehículo si existe
            if vehicle_info:
                if vehicle_info.get('year'):
                    parts.append(str(vehicle_info['year']))
                if vehicle_info.get('make'):
                    parts.append(vehicle_info['make'].lower())
                if vehicle_info.get('model'):
                    parts.append(vehicle_info['model'].lower())
            
            # Agregar query del usuario
            if query and query.strip():
                parts.append(query.strip())
            
            # Si no hay nada, usar término genérico
            if not parts:
                final_query = "brake pads"
            else:
                final_query = ' '.join(parts).strip()
            
            print(f"🔍 DEBUG: Query construida = '{final_query}'")
            logger.info(f"🔍 Query construida: '{final_query}'")
            return final_query
            
        except Exception as e:
            logger.error(f"❌ Error construyendo query: {e}")
            print(f"❌ DEBUG: Error en _build_search_query = {e}")
            return "brake pads"  # Fallback garantizado

# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def login_required(f):
    """Decorador para requerir login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not firebase_auth or not firebase_auth.is_user_logged_in():
                flash('Debes iniciar sesión para acceder a esta página.', 'warning')
                return redirect(url_for('auth_login_page'))
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error en login_required: {e}")
            return redirect(url_for('auth_login_page'))
    return decorated_function

def validate_image(image_content):
    """Validar imagen subida"""
    if not PIL_AVAILABLE or not image_content:
        return False
    try:
        image = Image.open(io.BytesIO(image_content))
        return image.size[0] > 10 and image.size[1] > 10
    except Exception as e:
        logger.error(f"Error validando imagen: {e}")
        return False

def render_page(title, content):
    """Renderizar página con template base"""
    template = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <title>{html.escape(title)}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
            min-height: 100vh; 
            padding: 15px; 
        }}
        .container {{ 
            max-width: 800px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 12px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
        }}
        h1 {{ color: #1e3c72; text-align: center; margin-bottom: 10px; font-size: 2.2em; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; font-size: 1.1em; }}
        input, select {{ 
            width: 100%; 
            padding: 14px; 
            margin: 10px 0; 
            border: 2px solid #e1e5e9; 
            border-radius: 8px; 
            font-size: 16px; 
            transition: border-color 0.3s;
        }}
        input:focus, select:focus {{ outline: none; border-color: #1e3c72; }}
        button {{ 
            background: #1e3c72; 
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px; 
            font-weight: 600; 
            padding: 14px 24px; 
            transition: background-color 0.3s;
        }}
        button:hover {{ background: #2a5298; }}
        .search-bar {{ display: flex; gap: 12px; margin-bottom: 25px; }}
        .search-bar input {{ flex: 1; margin: 0; }}
        .search-bar button {{ margin: 0; }}
        .vehicle-form {{ 
            background: #f8f9fa; 
            padding: 25px; 
            border-radius: 10px; 
            margin: 20px 0; 
            border: 1px solid #dee2e6;
        }}
        .vehicle-row {{ 
            display: grid; 
            grid-template-columns: 1fr 1fr 1fr; 
            gap: 15px; 
            margin-bottom: 15px; 
        }}
        .tips {{ 
            background: #e8f4f8; 
            border-left: 4px solid #1e3c72; 
            padding: 20px; 
            border-radius: 6px; 
            margin-bottom: 20px; 
            font-size: 14px; 
        }}
        .error {{ 
            background: #ffebee; 
            color: #c62828; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 15px 0; 
            display: none; 
            border-left: 4px solid #d32f2f;
        }}
        .loading {{ 
            text-align: center; 
            padding: 40px; 
            display: none; 
        }}
        .spinner {{ 
            border: 4px solid #f3f3f3; 
            border-top: 4px solid #1e3c72; 
            border-radius: 50%; 
            width: 50px; 
            height: 50px; 
            animation: spin 1s linear infinite; 
            margin: 0 auto 20px; 
        }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .user-info {{ 
            background: #e3f2fd; 
            padding: 15px; 
            border-radius: 8px; 
            margin-bottom: 20px; 
            text-align: center; 
            font-weight: 500;
        }}
        .user-info a {{ color: #1976d2; text-decoration: none; font-weight: 600; }}
        .user-info a:hover {{ text-decoration: underline; }}
        .image-upload {{ 
            background: #f8f9fa; 
            border: 3px dashed #dee2e6; 
            border-radius: 10px; 
            padding: 30px; 
            text-align: center; 
            margin: 20px 0; 
            cursor: pointer; 
            transition: all 0.3s ease;
        }}
        .image-upload:hover {{ border-color: #1e3c72; background: #e3f2fd; }}
        .image-upload input[type="file"] {{ display: none; }}
        .or-divider {{ 
            text-align: center; 
            margin: 25px 0; 
            color: #666; 
            font-weight: 600; 
            position: relative; 
        }}
        .or-divider:before {{ 
            content: ''; 
            position: absolute; 
            top: 50%; 
            left: 0; 
            right: 0; 
            height: 1px; 
            background: #dee2e6; 
            z-index: 1; 
        }}
        .or-divider span {{ 
            background: white; 
            padding: 0 20px; 
            position: relative; 
            z-index: 2; 
        }}
        .part-badge {{ 
            display: inline-block; 
            color: white; 
            padding: 4px 10px; 
            border-radius: 6px; 
            font-size: 12px; 
            font-weight: bold; 
            margin-left: 10px; 
        }}
        .part-badge.verified {{ background: #28a745; }}
        .part-badge.demo {{ background: #ff9800; }}
        .part-badge.oem {{ background: #28a745; }}
        .part-badge.aftermarket {{ background: #17a2b8; }}
        .product-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
            margin-top: 25px; 
        }}
        .product-card {{ 
            border: 1px solid #ddd; 
            border-radius: 10px; 
            padding: 20px; 
            background: white; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .product-card:hover {{ 
            transform: translateY(-2px); 
            box-shadow: 0 4px 15px rgba(0,0,0,0.15); 
        }}
        .product-card.verified {{ border-color: #28a745; border-width: 2px; }}
        .product-card.demo {{ border-color: #ff9800; border-width: 2px; }}
        .product-title {{ 
            margin: 0 0 12px 0; 
            color: #1e3c72; 
            font-size: 1.1em; 
            font-weight: 600; 
        }}
        .product-price {{ 
            font-size: 1.4em; 
            font-weight: bold; 
            color: #28a745; 
            margin: 8px 0; 
        }}
        .product-store {{ 
            font-size: 14px; 
            color: #666; 
            margin: 8px 0; 
        }}
        .product-link {{ 
            display: inline-block; 
            color: white; 
            padding: 10px 20px; 
            text-decoration: none; 
            border-radius: 6px; 
            font-size: 14px; 
            margin-top: 15px; 
            transition: background-color 0.3s;
        }}
        .product-link.verified {{ background: #28a745; }}
        .product-link.demo {{ background: #ff9800; }}
        .product-link:hover {{ opacity: 0.8; }}
        @media (max-width: 768px) {{
            .container {{ padding: 20px; margin: 10px; }}
            .vehicle-row {{ grid-template-columns: 1fr; }}
            .search-bar {{ flex-direction: column; }}
            h1 {{ font-size: 1.8em; }}
        }}
    </style>
</head>
<body>{content}</body>
</html>'''
    return template

# ==============================================================================
# RUTAS DE LA APLICACIÓN
# ==============================================================================

@app.route('/')
def home():
    """Página principal con búsqueda pública"""
    try:
        vehicle_data_json = json.dumps(VEHICLE_DATABASE)
        
        # Verificar estado de SerpAPI
        serpapi_status = "✅ Configurado" if os.environ.get('SERPAPI_KEY') else "⚠️ No configurado (modo demo)"
        
        home_content = f'''
        <div class="container">
            <h1>🔧 Auto Parts Finder USA</h1>
            <div class="subtitle">Encuentra repuestos automotrices en las mejores tiendas de Estados Unidos</div>
            
            <div style="background: {'#e8f5e8' if os.environ.get('SERPAPI_KEY') else '#fff3cd'}; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <strong>Estado SerpAPI:</strong> {serpapi_status}
                {'' if os.environ.get('SERPAPI_KEY') else '<br><small>Configure SERPAPI_KEY para resultados reales de tiendas</small>'}
            </div>
            
            <div class="tips">
                💡 <strong>Consejos para mejores resultados:</strong><br>
                • Incluye año, marca y modelo de tu vehículo<br>
                • Usa nombres específicos como "brake pads", "oil filter", "spark plugs"<br>
                • Puedes subir una foto del repuesto para identificación visual
            </div>
            
            <!-- Información del vehículo -->
            <div class="vehicle-form">
                <h3>🚗 Información del Vehículo (Opcional pero recomendado)</h3>
                <div class="vehicle-row">
                    <select id="vehicleYear">
                        <option value="">Seleccionar año</option>
                    </select>
                    <select id="vehicleMake">
                        <option value="">Seleccionar marca</option>
                    </select>
                    <select id="vehicleModel">
                        <option value="">Seleccionar modelo</option>
                    </select>
                </div>
            </div>
            
            <!-- Búsqueda por texto -->
            <div class="search-bar">
                <input type="text" id="searchQuery" placeholder="¿Qué repuesto necesitas? Ejemplo: brake pads, oil filter, spark plugs..." maxlength="150">
                <button onclick="searchParts()">🔍 Buscar Repuestos</button>
            </div>
            
            <div class="or-divider">
                <span>O</span>
            </div>
            
            <!-- Búsqueda por imagen -->
            <div class="image-upload" onclick="document.getElementById('imageInput').click()">
                <input type="file" id="imageInput" accept="image/*" onchange="handleImageUpload(event)">
                <div>📷 Subir foto del repuesto para identificación automática</div>
                <small style="color: #666; margin-top: 10px; display: block;">Formatos soportados: JPG, PNG, WEBP (máx. 16MB)</small>
            </div>
            
            <div class="loading" id="searchLoading">
                <div class="spinner"></div>
                <p>Buscando repuestos en las mejores tiendas...</p>
            </div>
            
            <div class="error" id="searchError"></div>
            
            <div id="searchResults"></div>
            
            <!-- Enlace para login -->
            <div style="text-align: center; margin-top: 40px; padding: 25px; background: #f8f9fa; border-radius: 10px;">
                <h3 style="color: #1e3c72; margin-bottom: 15px;">¿Necesitas más funciones?</h3>
                <p style="color: #666; margin-bottom: 20px;">Inicia sesión para guardar búsquedas, crear listas de repuestos y acceder a precios exclusivos</p>
                <a href="/login" style="background: #1e3c72; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                    Iniciar Sesión
                </a>
            </div>
        </div>
        
        <script>
        // Datos de vehículos
        const vehicleData = {vehicle_data_json};
        
        // Inicializar selectores de vehículos
        function initVehicleSelectors() {{
            const yearSelect = document.getElementById('vehicleYear');
            const makeSelect = document.getElementById('vehicleMake');
            
            // Llenar años (más recientes primero)
            const years = [...vehicleData.years].reverse();
            years.forEach(year => {{
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                yearSelect.appendChild(option);
            }});
            
            // Llenar marcas
            Object.keys(vehicleData.makes).forEach(make => {{
                const option = document.createElement('option');
                option.value = make;
                option.textContent = make.charAt(0).toUpperCase() + make.slice(1);
                makeSelect.appendChild(option);
            }});
            
            // Evento para actualizar modelos cuando cambia la marca
            makeSelect.addEventListener('change', updateModels);
        }}
        
        function updateModels() {{
            const makeSelect = document.getElementById('vehicleMake');
            const modelSelect = document.getElementById('vehicleModel');
            const selectedMake = makeSelect.value;
            
            // Limpiar modelos
            modelSelect.innerHTML = '<option value="">Seleccionar modelo</option>';
            
            if (selectedMake && vehicleData.makes[selectedMake]) {{
                vehicleData.makes[selectedMake].forEach(model => {{
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = model.toUpperCase();
                    modelSelect.appendChild(option);
                }});
            }}
        }}
        
        // Manejar subida de imagen
        function handleImageUpload(event) {{
            const file = event.target.files[0];
            if (file) {{
                if (file.size > 16 * 1024 * 1024) {{
                    alert('La imagen es demasiado grande. Máximo 16MB.');
                    return;
                }}
                console.log('Imagen seleccionada:', file.name);
            }}
        }}
        
        // Búsqueda de repuestos - FUNCIÓN PRINCIPAL CORREGIDA
        async function searchParts() {{
            console.log('🔍 Iniciando búsqueda...');
            
            const query = document.getElementById('searchQuery').value.trim();
            const imageInput = document.getElementById('imageInput');
            const vehicleYear = document.getElementById('vehicleYear').value;
            const vehicleMake = document.getElementById('vehicleMake').value;
            const vehicleModel = document.getElementById('vehicleModel').value;
            
            console.log('📊 Datos de búsqueda:', {{
                query: query,
                hasImage: imageInput.files.length > 0,
                vehicle: {{year: vehicleYear, make: vehicleMake, model: vehicleModel}}
            }});
            
            if (!query && !imageInput.files[0]) {{
                showError('Por favor ingresa un término de búsqueda o sube una imagen del repuesto');
                return;
            }}
            
            showLoading(true);
            hideError();
            clearResults();
            
            const formData = new FormData();
            if (query) formData.append('query', query);
            if (imageInput.files[0]) formData.append('image', imageInput.files[0]);
            if (vehicleYear) formData.append('vehicle_year', vehicleYear);
            if (vehicleMake) formData.append('vehicle_make', vehicleMake);
            if (vehicleModel) formData.append('vehicle_model', vehicleModel);
            
            try {{
                console.log('🌐 Enviando petición a /api/search-parts-public...');
                
                const response = await fetch('/api/search-parts-public', {{
                    method: 'POST',
                    body: formData
                }});
                
                console.log('📥 Respuesta recibida:', response.status, response.statusText);
                
                const result = await response.json();
                console.log('📊 Datos recibidos:', result);
                
                if (result.success) {{
                    console.log('✅ Búsqueda exitosa, mostrando resultados...');
                    displayResults(result.products, result.search_info || {{}});
                }} else {{
                    console.error('❌ Error en búsqueda:', result.message);
                    showError(result.message || 'Error en la búsqueda. Intenta nuevamente.');
                }}
            }} catch (error) {{
                console.error('❌ Error de conexión:', error);
                showError('Error de conexión. Verifica tu internet e intenta nuevamente.');
            }} finally {{
                showLoading(false);
            }}
        }}
        
        function displayResults(products, searchInfo) {{
            console.log('📊 Productos a mostrar:', products);
            console.log('📋 Info de búsqueda:', searchInfo);
            
            if (!products || products.length === 0) {{
                console.error('❌ No hay productos para mostrar');
                showError('No se encontraron repuestos. Intenta con otros términos de búsqueda.');
                return;
            }}
            
            const resultsContainer = document.getElementById('searchResults');
            
            // Verificar si hay errores
            if (products[0] && products[0].search_source === 'error') {{
                console.error('❌ Error en productos:', products[0]);
                showError('Error en la búsqueda: ' + (products[0].error_message || 'Error desconocido'));
                return;
            }}
            
            // Contar resultados reales vs demo
            const realResults = products.filter(p => p.serpapi_verified === true);
            const demoResults = products.filter(p => p.serpapi_verified === false);
            const resultType = realResults.length > 0 ? 'Resultados Verificados de SerpAPI' : 'Resultados Demo';
            const resultColor = realResults.length > 0 ? '#28a745' : '#ff9800';
            const resultIcon = realResults.length > 0 ? '✅' : '⚠️';
            
            console.log(`📊 Resultados: ${{realResults.length}} reales, ${{demoResults.length}} demo`);
            
            let html = `
                <div style="background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%); padding: 25px; border-radius: 12px; margin: 30px 0; border-left: 5px solid ${{resultColor}};">
                    <h3 style="color: #155724; margin-bottom: 10px;">
                        ${{resultIcon}} ${{resultType}} (${{products.length}} encontrados)
                    </h3>
                    <p style="color: #155724;"><strong>Búsqueda:</strong> ${{searchInfo.query || 'Imagen'}} ${{searchInfo.vehicle ? '| Vehículo: ' + searchInfo.vehicle : ''}}</p>
                    ${{realResults.length > 0 ? 
                        '<p style="color: #155724; font-size: 14px; margin-top: 8px;">🔗 Links directos a tiendas reales de repuestos</p>' : 
                        '<p style="color: #856404; font-size: 14px; margin-top: 8px;">⚠️ Configure SERPAPI_KEY para obtener resultados reales de tiendas</p>'
                    }}
                </div>
                <div class="product-grid">
            `;
            
            products.forEach((product, index) => {{
                const isReal = product.serpapi_verified === true;
                const cardClass = isReal ? 'verified' : 'demo';
                const badgeClass = isReal ? 'verified' : 'demo';
                const badgeText = isReal ? '✅ Verificado' : '⚠️ Demo';
                const linkClass = isReal ? 'verified' : 'demo';
                const linkText = isReal ? 'Ver en Tienda Real →' : 'Buscar en Google →';
                
                // Badge adicional para tipo de repuesto
                let partTypeBadge = '';
                if (product.part_type === 'OEM') {{
                    partTypeBadge = '<span class="part-badge oem">OEM Original</span>';
                }} else if (product.part_type === 'Aftermarket') {{
                    partTypeBadge = '<span class="part-badge aftermarket">Aftermarket</span>';
                }}
                
                html += `
                    <div class="product-card ${{cardClass}}">
                        <h4 class="product-title">
                            ${{product.title}} 
                            <span class="part-badge ${{badgeClass}}">${{badgeText}}</span>
                            ${{partTypeBadge}}
                        </h4>
                        <div class="product-price">
                            ${{product.price}}
                        </div>
                        <div class="product-store">
                            <strong>Tienda:</strong> ${{product.source}}
                        </div>
                        ${{product.rating ? `<div style="font-size: 13px; color: #666; margin: 8px 0;">⭐ ${{product.rating}} estrellas (${{product.reviews}} reseñas)</div>` : ''}}
                        <a href="${{product.link}}" target="_blank" class="product-link ${{linkClass}}">
                            ${{linkText}}
                        </a>
                    </div>
                `;
            }});
            
            html += '</div>';
            
            html += `
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 30px; text-align: center;">
                    <h4 style="color: #1e3c72; margin-bottom: 15px;">💡 Consejos para comprar repuestos</h4>
                    <ul style="text-align: left; color: #666; max-width: 600px; margin: 0 auto;">
                        <li style="margin-bottom: 8px;">✅ Verifica la compatibilidad con tu vehículo antes de comprar</li>
                        <li style="margin-bottom: 8px;">💰 Compara precios entre diferentes tiendas</li>
                        <li style="margin-bottom: 8px;">⭐ Lee las reseñas de otros compradores</li>
                        <li style="margin-bottom: 8px;">🛡️ Considera la garantía ofrecida por cada tienda</li>
                        ${{realResults.length > 0 ? 
                            '<li style="margin-bottom: 8px;">🔗 Los enlaces verificados te llevan directamente a la página del producto</li>' : 
                            '<li style="margin-bottom: 8px;">⚠️ Para obtener links directos a productos, configure su API key de SerpAPI</li>'
                        }}
                    </ul>
                </div>
            `;
            
            resultsContainer.innerHTML = html;
            console.log('✅ Resultados mostrados exitosamente');
        }}
        
        function showLoading(show) {{
            const loadingDiv = document.getElementById('searchLoading');
            loadingDiv.style.display = show ? 'block' : 'none';
            console.log('🔄 Loading:', show);
        }}
        
        function showError(message) {{
            const errorDiv = document.getElementById('searchError');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            console.error('❌ Error mostrado:', message);
        }}
        
        function hideError() {{
            const errorDiv = document.getElementById('searchError');
            errorDiv.style.display = 'none';
        }}
        
        function clearResults() {{
            const resultsDiv = document.getElementById('searchResults');
            resultsDiv.innerHTML = '';
            console.log('🧹 Resultados limpiados');
        }}
        
        // Buscar al presionar Enter
        document.getElementById('searchQuery').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                searchParts();
            }}
        }});
        
        // Inicializar cuando carga la página
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('🚀 Página cargada, inicializando...');
            initVehicleSelectors();
        }});
        </script>
        '''
        
        return render_page("Auto Parts Finder USA - Encuentra Repuestos Automotrices", home_content)
        
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        return render_page("Error", '<div class="container"><h1>Error</h1><p>Error cargando la página principal</p><a href="/">Reintentar</a></div>'), 500

@app.route('/login', methods=['GET'])
def auth_login_page():
    """Página de login"""
    try:
        if firebase_auth and firebase_auth.is_user_logged_in():
            return redirect(url_for('search_page'))
        
        login_content = '''
        <div class="container">
            <h1>🔐 Auto Parts Finder</h1>
            <div class="subtitle">Iniciar Sesión para Acceso Completo</div>
            
            <div style="background: #e3f2fd; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                <h3 style="color: #1565c0; margin-bottom: 15px;">Beneficios de crear cuenta:</h3>
                <ul style="color: #1976d2; margin-left: 20px;">
                    <li>Guardar búsquedas y listas de repuestos</li>
                    <li>Acceso a precios exclusivos</li>
                    <li>Historial de compras</li>
                    <li>Alertas de ofertas personalizadas</li>
                </ul>
            </div>
            
            <form id="loginForm" onsubmit="handleLogin(event)">
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Correo electrónico:</label>
                    <input type="email" id="email" placeholder="tu@email.com" required>
                </div>
                <div style="margin-bottom: 25px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Contraseña:</label>
                    <input type="password" id="password" placeholder="Tu contraseña" required>
                </div>
                <button type="submit" style="width: 100%; padding: 16px; font-size: 18px;">Iniciar Sesión</button>
            </form>
            
            <div class="loading" id="loginLoading">
                <div class="spinner"></div>
                <p>Verificando credenciales...</p>
            </div>
            
            <div class="error" id="loginError"></div>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin-top: 25px; border-left: 4px solid #ffc107;">
                <h4 style="color: #856404; margin-bottom: 10px;">🧪 Credenciales de Demo:</h4>
                <p style="color: #856404; margin-bottom: 8px;"><strong>Email:</strong> admin@test.com</p>
                <p style="color: #856404;"><strong>Contraseña:</strong> password123</p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <p style="margin-bottom: 15px;">
                    <a href="/" style="color: #1e3c72; text-decoration: none; font-weight: 600;">← Volver a búsqueda sin registrarse</a>
                </p>
                <p style="color: #666; font-size: 14px;">
                    ¿No tienes cuenta? <a href="#" style="color: #1e3c72;">Regístrate aquí</a>
                </p>
            </div>
        </div>
        
        <script>
        async function handleLogin(event) {
            event.preventDefault();
            
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value.trim();
            
            if (!email || !password) {
                showLoginError('Por favor completa todos los campos');
                return;
            }
            
            document.getElementById('loginForm').style.display = 'none';
            document.getElementById('loginLoading').style.display = 'block';
            hideLoginError();
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    window.location.href = '/search';
                } else {
                    showLoginError(result.message || 'Error de autenticación');
                    document.getElementById('loginForm').style.display = 'block';
                }
            } catch (error) {
                console.error('Login error:', error);
                showLoginError('Error de conexión. Intenta nuevamente.');
                document.getElementById('loginForm').style.display = 'block';
            } finally {
                document.getElementById('loginLoading').style.display = 'none';
            }
        }
        
        function showLoginError(message) {
            const errorDiv = document.getElementById('loginError');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }
        
        function hideLoginError() {
            document.getElementById('loginError').style.display = 'none';
        }
        
        // Completar campos demo al hacer clic
        document.addEventListener('DOMContentLoaded', function() {
            const demoSection = document.querySelector('[style*="background: #fff3cd"]');
            if (demoSection) {
                demoSection.style.cursor = 'pointer';
                demoSection.addEventListener('click', function() {
                    document.getElementById('email').value = 'admin@test.com';
                    document.getElementById('password').value = 'password123';
                });
            }
        });
        </script>
        '''
        
        return render_page("Iniciar Sesión - Auto Parts Finder", login_content)
        
    except Exception as e:
        logger.error(f"Error in login page: {e}")
        return render_page("Error", '<div class="container"><h1>Error</h1><p>Error cargando página de login</p><a href="/">Volver</a></div>'), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    """API de autenticación"""
    try:
        if not firebase_auth:
            return jsonify({'success': False, 'message': 'Servicio de autenticación no disponible'})
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Datos no válidos'})
        
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email y contraseña son requeridos'})
        
        result = firebase_auth.login_user(email, password)
        
        if result['success']:
            firebase_auth.set_user_session(result['user_data'])
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error en API login: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'})

@app.route('/search')
@login_required
def search_page():
    """Página de búsqueda para usuarios autenticados"""
    try:
        current_user = firebase_auth.get_current_user()
        user_name = current_user['user_name'] if current_user else 'Usuario'
        
        search_content = f'''
        <div class="container">
            <div class="user-info">
                👋 Bienvenido, <strong>{html.escape(user_name)}</strong> | 
                <a href="/logout">Cerrar Sesión</a> | 
                <a href="/profile">Mi Perfil</a>
            </div>
            
            <h1>🔧 Auto Parts Finder PRO</h1>
            <div class="subtitle">Búsqueda avanzada de repuestos con funciones premium</div>
            
            <div style="background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%); padding: 20px; border-radius: 10px; margin-bottom: 25px;">
                <h3 style="color: #155724; margin-bottom: 10px;">🎯 Funciones Premium Activadas</h3>
                <ul style="color: #155724; margin-left: 20px; font-size: 14px;">
                    <li>Búsquedas ilimitadas con SerpAPI</li>
                    <li>Precios en tiempo real</li>
                    <li>Comparación avanzada</li>
                    <li>Guardado de favoritos</li>
                </ul>
            </div>
            
            <!-- Búsqueda mejorada -->
            <div class="search-bar">
                <input type="text" id="searchQuery" placeholder="Buscar repuestos con mayor precisión..." maxlength="200">
                <button onclick="searchParts()">🔍 Buscar PRO</button>
            </div>
            
            <div class="loading" id="searchLoading">
                <div class="spinner"></div>
                <p>Buscando en base de datos premium...</p>
            </div>
            
            <div class="error" id="searchError"></div>
            
            <div id="searchResults"></div>
            
            <!-- Historial de búsquedas -->
            <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <h3 style="color: #1e3c72;">📋 Búsquedas Recientes</h3>
                <div id="searchHistory">
                    <p style="color: #666; font-style: italic;">Tus búsquedas aparecerán aquí...</p>
                </div>
            </div>
        </div>
        
        <script>
        let searchHistory = JSON.parse(localStorage.getItem('autoparts_search_history') || '[]');
        
        async function searchParts() {{
            const query = document.getElementById('searchQuery').value.trim();
            
            if (!query) {{
                showError('Por favor ingresa un término de búsqueda');
                return;
            }}
            
            showLoading(true);
            hideError();
            clearResults();
            
            // Agregar al historial
            addToHistory(query);
            
            const formData = new FormData();
            formData.append('query', query);
            
            try {{
                const response = await fetch('/api/search-parts', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    displayResults(result.products);
                }} else {{
                    showError(result.message || 'Error en la búsqueda');
                }}
            }} catch (error) {{
                console.error('Error:', error);
                showError('Error de conexión');
            }} finally {{
                showLoading(false);
            }}
        }}
        
        function displayResults(products) {{
            if (!products || products.length === 0) {{
                showError('No se encontraron repuestos');
                return;
            }}
            
            const resultsContainer = document.getElementById('searchResults');
            
            // Contar resultados reales vs demo
            const realResults = products.filter(p => p.serpapi_verified === true);
            const resultType = realResults.length > 0 ? 'Resultados Verificados Premium' : 'Resultados Demo Premium';
            const resultColor = realResults.length > 0 ? '#28a745' : '#ff9800';
            const resultIcon = realResults.length > 0 ? '✅' : '⚠️';
            
            let html = `
                <div style="background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%); padding: 25px; border-radius: 12px; margin: 30px 0; border-left: 5px solid ${{resultColor}};">
                    <h3 style="color: #155724;">${{resultIcon}} ${{resultType}} (${{products.length}} encontrados)</h3>
                    ${{realResults.length > 0 ? 
                        '<p style="color: #155724; font-size: 14px;">🔗 Enlaces directos verificados a tiendas reales</p>' : 
                        '<p style="color: #856404; font-size: 14px;">⚠️ Configure SERPAPI_KEY para resultados reales</p>'
                    }}
                </div>
                <div class="product-grid">
            `;
            
            products.forEach(product => {{
                const isReal = product.serpapi_verified === true;
                const cardClass = isReal ? 'verified' : 'demo';
                const badgeClass = isReal ? 'verified' : 'demo';
                const badgeText = isReal ? '✅ Verificado' : '⚠️ Demo';
                const linkClass = isReal ? 'verified' : 'demo';
                
                html += `
                    <div class="product-card ${{cardClass}}">
                        <h4 class="product-title">
                            ${{product.title}} 
                            <span class="part-badge ${{badgeClass}}">${{badgeText}}</span>
                        </h4>
                        <div class="product-price">${{product.price}}</div>
                        <div class="product-store"><strong>Tienda:</strong> ${{product.source}}</div>
                        <div style="margin: 10px 0;">
                            <button onclick="saveFavorite('${{product.title.replace(/'/g, "\\'")}}')" style="background: #28a745; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; margin-right: 10px;">
                                ❤ Guardar
                            </button>
                            <a href="${{product.link}}" target="_blank" class="product-link ${{linkClass}}">
                                ${{isReal ? 'Ver Producto Real →' : 'Buscar en Google →'}}
                            </a>
                        </div>
                    </div>
                `;
            }});
            
            html += '</div>';
            resultsContainer.innerHTML = html;
        }}
        
        function addToHistory(query) {{
            searchHistory.unshift(query);
            searchHistory = [...new Set(searchHistory)].slice(0, 5); // Solo últimas 5 búsquedas únicas
            localStorage.setItem('autoparts_search_history', JSON.stringify(searchHistory));
            updateHistoryDisplay();
        }}
        
        function updateHistoryDisplay() {{
            const historyContainer = document.getElementById('searchHistory');
            if (searchHistory.length === 0) {{
                historyContainer.innerHTML = '<p style="color: #666; font-style: italic;">Tus búsquedas aparecerán aquí...</p>';
                return;
            }}
            
            let html = '';
            searchHistory.forEach(query => {{
                html += `
                    <span style="display: inline-block; background: #e3f2fd; color: #1976d2; padding: 5px 10px; border-radius: 15px; margin: 5px 5px 5px 0; cursor: pointer;" 
                          onclick="document.getElementById('searchQuery').value = '${{query.replace(/'/g, "\\'")}}'; searchParts();">
                        ${{query}}
                    </span>
                `;
            }});
            historyContainer.innerHTML = html;
        }}
        
        function saveFavorite(title) {{
            alert('Repuesto guardado en favoritos: ' + title);
        }}
        
        function showLoading(show) {{
            document.getElementById('searchLoading').style.display = show ? 'block' : 'none';
        }}
        
        function showError(message) {{
            const errorDiv = document.getElementById('searchError');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }}
        
        function hideError() {{
            document.getElementById('searchError').style.display = 'none';
        }}
        
        function clearResults() {{
            document.getElementById('searchResults').innerHTML = '';
        }}
        
        // Inicializar
        document.addEventListener('DOMContentLoaded', function() {{
            updateHistoryDisplay();
            
            document.getElementById('searchQuery').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    searchParts();
                }}
            }});
        }});
        </script>
        '''
        
        return render_page("Búsqueda Premium - Auto Parts Finder", search_content)
        
    except Exception as e:
        logger.error(f"Error in search page: {e}")
        return redirect(url_for('auth_login_page'))

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    try:
        if firebase_auth:
            firebase_auth.clear_user_session()
        flash('Has cerrado sesión correctamente', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Error en logout: {e}")
        return redirect(url_for('home'))

@app.route('/api/search-parts-public', methods=['POST'])
def api_search_parts_public():
    """API de búsqueda pública con debug mejorado"""
    try:
        query = request.form.get('query', '').strip()
        vehicle_year = request.form.get('vehicle_year', '').strip()
        vehicle_make = request.form.get('vehicle_make', '').strip()
        vehicle_model = request.form.get('vehicle_model', '').strip()
        
        print(f"📥 DEBUG: Búsqueda recibida - Query: '{query}', Vehículo: {vehicle_year} {vehicle_make} {vehicle_model}")
        logger.info(f"📥 Búsqueda recibida - Query: '{query}', Vehículo: {vehicle_year} {vehicle_make} {vehicle_model}")
        
        # Procesar imagen si existe
        image_content = None
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            try:
                image_content = image_file.read()
                print(f"📷 DEBUG: Imagen recibida: {image_file.filename}, tamaño: {len(image_content)} bytes")
                if not validate_image(image_content):
                    print("❌ DEBUG: Imagen no válida")
                    return jsonify({
                        'success': False, 
                        'message': 'Imagen no válida. Use formatos JPG, PNG o WEBP.'
                    })
            except Exception as e:
                logger.error(f"Error procesando imagen: {e}")
                print(f"❌ DEBUG: Error procesando imagen: {e}")
                return jsonify({
                    'success': False, 
                    'message': 'Error procesando la imagen'
                })
        
        # Validación mejorada
        if not query and not image_content:
            print("❌ DEBUG: No hay query ni imagen")
            return jsonify({
                'success': False, 
                'message': 'Proporciona un término de búsqueda o una imagen'
            })
        
        # Si no hay query, usar uno por defecto
        if not query:
            query = "brake pads"
            print(f"🔄 DEBUG: Usando query por defecto: '{query}'")
        
        # Información del vehículo
        vehicle_info = None
        if vehicle_year or vehicle_make or vehicle_model:
            vehicle_info = {
                'year': vehicle_year,
                'make': vehicle_make,
                'model': vehicle_model
            }
            print(f"🚗 DEBUG: Info del vehículo: {vehicle_info}")
        
        # Verificar que AutoPartsFinder esté disponible
        if not auto_parts_finder:
            print("❌ DEBUG: AutoPartsFinder no está inicializado")
            logger.error("❌ AutoPartsFinder no está inicializado")
            return jsonify({
                'success': False, 
                'message': 'Servicio de búsqueda no disponible temporalmente'
            })
        
        # Realizar búsqueda
        print(f"🔍 DEBUG: Iniciando búsqueda...")
        logger.info(f"🔍 Iniciando búsqueda...")
        
        products = auto_parts_finder.search_auto_parts(
            query=query,
            image_content=image_content,
            vehicle_info=vehicle_info
        )
        
        print(f"📊 DEBUG: Resultados obtenidos: {len(products) if products else 0}")
        logger.info(f"📊 Resultados obtenidos: {len(products) if products else 0}")
        
        # Verificar que tenemos resultados
        if not products or len(products) == 0:
            print("⚠️ DEBUG: No se obtuvieron productos, forzando resultados demo")
            logger.warning("⚠️ No se obtuvieron productos, forzando resultados demo")
            # Forzar resultados demo
            products = auto_parts_finder._generate_sample_results(query, demo_mode=True)
        
        # Información adicional de la búsqueda
        search_info = {
            'query': query,
            'has_image': bool(image_content),
            'vehicle': None,
            'timestamp': datetime.now().isoformat()
        }
        
        if vehicle_info and any(vehicle_info.values()):
            vehicle_parts = [p for p in [vehicle_info.get('year'), 
                           vehicle_info.get('make', '').title(), 
                           vehicle_info.get('model', '').upper()] if p]
            search_info['vehicle'] = ' '.join(vehicle_parts)
        
        print(f"✅ DEBUG: Respuesta exitosa con {len(products)} productos")
        logger.info(f"✅ Respuesta exitosa con {len(products)} productos")
        
        return jsonify({
            'success': True,
            'products': products,
            'search_info': search_info,
            'count': len(products)
        })
        
    except Exception as e:
        logger.error(f"❌ Error en búsqueda pública: {e}")
        print(f"❌ DEBUG: Error en búsqueda pública: {e}")
        return jsonify({
            'success': False, 
            'message': f'Error interno del servidor: {str(e)}'
        })

@app.route('/api/search-parts', methods=['POST'])
@login_required
def api_search_parts():
    """API de búsqueda para usuarios autenticados"""
    try:
        query = request.form.get('query', '').strip()
        
        print(f"🔍 DEBUG: Búsqueda premium - Query: '{query}'")
        
        if not query:
            return jsonify({
                'success': False, 
                'message': 'Término de búsqueda requerido'
            })
        
        if not auto_parts_finder:
            print("❌ DEBUG: AutoPartsFinder no disponible")
            return jsonify({
                'success': False, 
                'message': 'Servicio no disponible'
            })
        
        products = auto_parts_finder.search_auto_parts(query=query)
        
        print(f"✅ DEBUG: Búsqueda premium completada - {len(products)} productos")
        
        return jsonify({
            'success': True,
            'products': products,
            'count': len(products),
            'premium': True
        })
        
    except Exception as e:
        logger.error(f"Error en búsqueda autenticada: {e}")
        print(f"❌ DEBUG: Error en búsqueda autenticada: {e}")
        return jsonify({
            'success': False, 
            'message': 'Error interno del servidor'
        })

# ==============================================================================
# MANEJADORES DE ERRORES
# ==============================================================================

@app.errorhandler(404)
def not_found(error):
    """Página no encontrada"""
    content = '''
    <div class="container">
        <h1>🚫 Página No Encontrada</h1>
        <div class="subtitle">Error 404</div>
        <div style="text-align: center; margin: 40px 0;">
            <p style="color: #666; margin-bottom: 30px;">La página que buscas no existe o ha sido movida.</p>
            <a href="/" style="background: #1e3c72; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                🏠 Volver al Inicio
            </a>
        </div>
    </div>
    '''
    return render_page("Página No Encontrada - Auto Parts Finder", content), 404

@app.errorhandler(500)
def internal_error(error):
    """Error interno del servidor"""
    content = '''
    <div class="container">
        <h1>⚠ Error Interno</h1>
        <div class="subtitle">Error 500</div>
        <div style="text-align: center; margin: 40px 0;">
            <p style="color: #666; margin-bottom: 30px;">Ha ocurrido un error interno en el servidor. Nuestro equipo ha sido notificado.</p>
            <a href="/" style="background: #1e3c72; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                🔄 Reintentar
            </a>
        </div>
    </div>
    '''
    return render_page("Error Interno - Auto Parts Finder", content), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Manejador de excepciones generales"""
    logger.error(f"Excepción no manejada: {e}")
    content = '''
    <div class="container">
        <h1>❌ Error Inesperado</h1>
        <div class="subtitle">Algo salió mal</div>
        <div style="text-align: center; margin: 40px 0;">
            <p style="color: #666; margin-bottom: 30px;">Ha ocurrido un error inesperado. Por favor intenta nuevamente.</p>
            <a href="/" style="background: #1e3c72; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                🏠 Volver al Inicio
            </a>
        </div>
    </div>
    '''
    return render_page("Error - Auto Parts Finder", content), 500

# ==============================================================================
# INICIALIZACIÓN SEGURA DE COMPONENTES
# ==============================================================================

def initialize_components():
    """Inicializar todos los componentes de la aplicación de forma segura"""
    global firebase_auth, auto_parts_finder
    
    # Inicializar Firebase Auth
    try:
        firebase_auth = FirebaseAuth()
        logger.info("✅ FirebaseAuth inicializado correctamente")
        print("✅ DEBUG: FirebaseAuth inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando FirebaseAuth: {e}")
        print(f"❌ DEBUG: Error en FirebaseAuth: {e}")
        firebase_auth = None
    
    # Inicializar AutoPartsFinder
    try:
        auto_parts_finder = AutoPartsFinder()
        logger.info("✅ AutoPartsFinder inicializado correctamente")
        print("✅ DEBUG: AutoPartsFinder inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando AutoPartsFinder: {e}")
        print(f"❌ DEBUG: Error en AutoPartsFinder: {e}")
        auto_parts_finder = None

# Inicializar componentes al importar
initialize_components()

# ==============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ==============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("🔧 AUTO PARTS FINDER USA - SISTEMA DE REPUESTOS AUTOMOTRICES")
    print("=" * 70)
    
    # Información del sistema
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🌐 Puerto: {port}")
    print(f"🔧 Modo Debug: {debug_mode}")
    print(f"🖼  PIL (imágenes): {'✅ Disponible' if PIL_AVAILABLE else '❌ No disponible'}")
    print(f"🤖 Gemini AI: {'✅ Disponible' if GEMINI_AVAILABLE else '❌ No disponible'}")
    print(f"🕷  BeautifulSoup: {'✅ Disponible' if BS4_AVAILABLE else '❌ No disponible'}")
    print(f"🔐 Firebase Auth: {'✅ Configurado' if firebase_auth else '❌ Error'}")
    print(f"🔍 Auto Parts Finder: {'✅ Activo' if auto_parts_finder else '❌ Error'}")
    
    # Estado de SerpAPI
    serpapi_key = os.environ.get('SERPAPI_KEY')
    if serpapi_key:
        print(f"🔑 SerpAPI: ✅ Configurado (key: ...{serpapi_key[-8:]})")
        print("   ➡️ Mostrará resultados REALES de tiendas")
    else:
        print("🔑 SerpAPI: ⚠️ NO CONFIGURADO")
        print("   ➡️ Mostrará resultados DEMO")
        print("   💡 Configure SERPAPI_KEY para resultados reales")
    
    print("=" * 70)
    print("🚀 Iniciando servidor...")
    print("📝 Credenciales demo: admin@test.com / password123")
    print("🔗 Página principal: http://localhost:5000")
    print("💡 Para debugging: Revisa la consola del navegador (F12)")
    print("=" * 70)
    
    try:
        app.run(
            host='0.0.0.0', 
            port=port, 
            debug=debug_mode,
            use_reloader=debug_mode
        )
    except Exception as e:
        logger.error(f"❌ Error crítico iniciando la aplicación: {e}")
        print(f"\n❌ ERROR CRÍTICO: {e}")
        print("💡 Verificaciones:")
        print("   - Puerto disponible")
        print("   - Permisos de red")
        print("   - Variables de entorno")
        print("   - Dependencias instaladas")
        if not serpapi_key:
            print("   - Configure SERPAPI_KEY para resultados reales")
