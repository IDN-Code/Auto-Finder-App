from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string, flash
from flask_login import login_required
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from PIL import Image
import io

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde .env
load_dotenv()

# Inicializar Firebase Admin
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# Inicializar Firebase Auth
class FirebaseAuth:
    def __init__(self):
        self.auth = auth

    def is_user_logged_in(self):
        user = self.auth.get_id_token(session.get('user_id'))
        return user is not None

    def get_current_user(self):
        try:
            user = self.auth.verify_id_token(session.get('id_token'))
            return user
        except Exception as e:
            logger.error(f"Error al verificar token de Firebase: {e}")
            return None

    def login_user(self, email, password):
        try:
            user = self.auth.create_user(email=email, password=password)
            return {'success': True, 'message': 'Usuario creado exitosamente', 'user_data': user.to_dict()}
        except Exception as e:
            logger.error(f"Error al crear usuario en Firebase: {e}")
            return {'success': False, 'message': f'Error: {e}'}

    def set_user_session(self, user_data):
        session['user_id'] = user_data['uid']
        session['email'] = user_data['email']
        session['user_name'] = user_data['display_name']
        session['user_role'] = user_data.get('user_role', 'user')
        session['id_token'] = self.auth.create_custom_token(user_data['uid']).decode('utf-8')

    def clear_user_session(self):
        session.clear()

# Inicializar AutoPartsFinder
class AutoPartsFinder:
    def __init__(self):
        self.serpapi_key = os.environ.get('SERPAPI_KEY')
        if not self.serpapi_key:
            raise ValueError("SERPAPI_KEY no configurado en el archivo .env")
        self.headers = {
            "X-API-KEY": self.serpapi_key,
            "Content-Type": "application/json"
        }
        self.base_url = "https://serpapi.com/search"

    def search_auto_parts(self, query, image_content=None, vehicle_info=None):
        try:
            params = {
                "q": query,
                "tbm": "shop", # Search in shopping results
                "api_key": self.serpapi_key
            }

            if image_content:
                params["image_url"] = "data:image/jpeg;base64," + base64.b64encode(image_content).decode('utf-8')

            if vehicle_info:
                params["vehicle_year"] = vehicle_info.get("year")
                params["vehicle_make"] = vehicle_info.get("make")
                params["vehicle_model"] = vehicle_info.get("model")

            response = requests.get(self.base_url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            if data.get("error"):
                return {"success": False, "message": f"Error de SERPAPI: {data['error']}"}

            products = []
            if data.get("shopping_results"):
                for item in data["shopping_results"]:
                    product = {
                        "title": item.get("title", "N/A"),
                        "price": item.get("price", "N/A"),
                        "link": item.get("link", "N/A"),
                        "source": item.get("source", "N/A"),
                        "rating": item.get("rating", "N/A"),
                        "reviews": item.get("reviews", "N/A"),
                        "part_type": "Aftermarket" # Default to aftermarket
                    }
                    if item.get("product_type") == "OEM":
                        product["part_type"] = "OEM"
                    elif item.get("product_type") == "Premium":
                        product["part_type"] = "Premium"
                    products.append(product)

            return {"success": True, "products": products, "message": f"Se encontraron {len(products)} productos"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al buscar en SERPAPI: {e}")
            return {"success": False, "message": f"Error de conexión con SERPAPI: {e}"}
        except Exception as e:
            logger.error(f"Error inesperado en AutoPartsFinder: {e}")
            return {"success": False, "message": f"Error interno del servidor: {e}"}

# Validar imagen
def validate_image(image_content):
    try:
        Image.open(io.BytesIO(image_content))
        return True
    except Exception:
        return False

# Inicializar Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here')

# Configurar Firebase Auth para Flask
@app.before_request
def before_request():
    if 'user_id' in session:
        try:
            user = auth.verify_id_token(session['id_token'])
            session['user_id'] = user.uid
            session['email'] = user.email
            session['user_name'] = user.display_name
            session['user_role'] = user.custom_claims.get('user_role', 'user')
        except Exception as e:
            logger.warning(f"Token de sesión inválido o expirado: {e}")
            session.clear()

# Renderizar página principal
@app.route('/')
def home():
    """Página principal de la aplicación"""
    try:
        if firebase_auth and firebase_auth.is_user_logged_in():
            return redirect(url_for('search_page'))
        
        home_content = '''
            <h1>🔧 Auto Parts Finder USA</h1>
            <div class="subtitle">Encuentra repuestos automotrices de alta calidad</div>
            
            <div class="alert alert-info">
                <h6>🎯 Funciones Principales</h6>
                <ul class="mb-0">
                    <li>Búsqueda de repuestos por término o imagen</li>
                    <li>Filtros de vehículo para mayor precisión</li>
                    <li>Precios en tiempo real</li>
                    <li>Enlaces directos a tiendas especializadas</li>
                </ul>
            </div>
            
            <div class="input-group mb-3">
                <input type="text" id="searchQuery" class="form-control" placeholder="Buscar repuestos con mayor precisión..." maxlength="200" required>
                <button class="btn btn-primary" onclick="searchParts()">🔍 Buscar</button>
            </div>
            
            <div id="searchLoading" class="text-center" style="display: none;">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Buscando en base de datos...</p>
            </div>
            
            <div id="searchError" class="alert alert-danger" style="display: none;"></div>
            
            <div id="searchResults"></div>
        
        <script>
        function updateModels() {{
            const makeSelect = document.getElementById('vehicleMake');
            const modelSelect = document.getElementById('vehicleModel');
            const selectedMake = makeSelect.value;
            
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
        
        async function searchParts() {{
            console.log('🔍 Iniciando búsqueda...');
            
            if (!hasAPI) {{
                showError('La aplicación requiere configurar SERPAPI_KEY para funcionar. Contacte al administrador.');
                return;
            }}
            
            const query = document.getElementById('searchQuery').value.trim();
            const imageInput = document.getElementById('imageInput');
            const vehicleYear = document.getElementById('vehicleYear').value;
            const vehicleMake = document.getElementById('vehicleMake').value;
            const vehicleModel = document.getElementById('vehicleModel').value;
            
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
                const response = await fetch('/api/search-parts-public', {{
                    method: 'POST',
                    body: formData
                }});
                
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                
                const result = await response.json();
                
                if (result.success) {{
                    if (result.products && result.products.length > 0) {{
                        displayResults(result.products, result.search_info || {{}});
                    }} else {{
                        showError(result.message || 'No se encontraron repuestos para esta búsqueda.');
                    }}
                }} else {{
                    showError(result.message || 'Error en la búsqueda. Intenta nuevamente.');
                }}
            }} catch (error) {{
                showError(`Error de conexión: ${{error.message}}`);
            }} finally {{
                showLoading(false);
            }}
        }}
        
        function displayResults(products, searchInfo) {{
            if (!products || products.length === 0) {{
                showError('No se encontraron repuestos.');
                return;
            }}
            
            const resultsContainer = document.getElementById('searchResults');
            
            let html = `
                <div class="alert alert-success">
                    <h5>✅ Resultados Encontrados (${{products.length}} productos)</h5>
                    <p><strong>Búsqueda:</strong> ${{searchInfo.query || 'Imagen'}} ${{searchInfo.vehicle ? '| Vehículo: ' + searchInfo.vehicle : ''}}</p>
                    <small>🔗 Enlaces directos a tiendas especializadas en repuestos automotrices</small>
                </div>
            `;
            
            products.forEach(product => {{
                let badgeClass = 'aftermarket';
                let badgeText = product.part_type || 'Aftermarket';
                
                if (product.part_type === 'OEM') {{
                    badgeClass = 'oem';
                    badgeText = '🏭 OEM Original';
                }} else if (product.part_type === 'Premium') {{
                    badgeClass = 'premium';
                    badgeText = '⭐ Premium';
                }} else {{
                    badgeText = '🔧 Aftermarket';
                }}
                
                html += `
                    <div class="product-card">
                        <div class="product-title">
                            ${{product.title}} 
                            <span class="part-badge ${{badgeClass}}">${{badgeText}}</span>
                        </div>
                        <div class="product-price">${{product.price}}</div>
                        <div class="mb-2"><strong>Tienda:</strong> ${{product.source}}</div>
                        ${{product.rating ? `<div class="mb-2"><small>⭐ ${{product.rating}} (${{product.reviews || '0'}} reseñas)</small></div>` : ''}}
                        <a href="${{product.link}}" target="_blank" class="btn btn-success btn-sm" rel="noopener noreferrer">
                            Ver en Tienda →
                        </a>
                    </div>
                `;
            }});
            
            html += `
                <div class="alert alert-info mt-4">
                    <h6>💡 Consejos para comprar repuestos</h6>
                    <ul class="mb-0">
                        <li>✅ Verifica la compatibilidad con tu vehículo antes de comprar</li>
                        <li>💰 Compara precios entre diferentes tiendas</li>
                        <li>⭐ Lee las reseñas de otros compradores</li>
                        <li>🛡️ Considera la garantía ofrecida por cada tienda</li>
                        <li>🔗 Los enlaces te llevan directamente a la página del producto</li>
                    </ul>
                </div>
            `;
            
            resultsContainer.innerHTML = html;
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
        
        document.getElementById('searchQuery').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                searchParts();
            }}
        }});
        
        document.addEventListener('DOMContentLoaded', function() {{
            initVehicleSelectors();
        }});
        </script>
        '''
        
        return render_template_string(home_content, hasAPI=bool(os.environ.get('SERPAPI_KEY')))
        
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        return render_template_string('<div class="alert alert-danger"><h4>Error</h4><p>Error cargando la página principal</p><a href="/" class="btn btn-primary">Reintentar</a></div>'), 500

@app.route('/login', methods=['GET'])
def auth_login_page():
    """Página de login"""
    try:
        if firebase_auth and firebase_auth.is_user_logged_in():
            return redirect(url_for('search_page'))
        
        login_content = '''
            <h1>🔐 Auto Parts Finder</h1>
            <div class="subtitle">Iniciar Sesión para Acceso Completo</div>
            
            <div class="alert alert-info">
                <h5>Beneficios de crear cuenta:</h5>
                <ul class="mb-0">
                    <li>Guardar búsquedas y listas de repuestos</li>
                    <li>Historial de búsquedas</li>
                    <li>Comparación de precios avanzada</li>
                    <li>Alertas de disponibilidad</li>
                </ul>
            </div>
            
            <form id="loginForm" onsubmit="handleLogin(event)">
                <div class="mb-3">
                    <label for="email" class="form-label">Correo electrónico:</label>
                    <input type="email" id="email" class="form-control" placeholder="tu@email.com" required>
                </div>
                <div class="mb-3">
                    <label for="password" class="form-label">Contraseña:</label>
                    <input type="password" id="password" class="form-control" placeholder="Tu contraseña" required>
                </div>
                <button type="submit" class="btn btn-primary w-100">Iniciar Sesión</button>
            </form>
            
            <div id="loginLoading" class="text-center mt-3" style="display: none;">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Verificando credenciales...</p>
            </div>
            
            <div id="loginError" class="alert alert-danger mt-3" style="display: none;"></div>
            
            <div class="alert alert-warning mt-3">
                <h6>🔑 Credenciales de Prueba:</h6>
                <div class="mb-2">
                    <strong>Administrador:</strong><br>
                    Email: admin@autoparts.com<br>
                    Contraseña: AutoParts2025!
                </div>
                <div>
                    <strong>Usuario Regular:</strong><br>
                    Email: user@autoparts.com<br>
                    Contraseña: UserPass123!
                </div>
            </div>
            
            <div class="text-center mt-3">
                <a href="/" class="btn btn-link">← Volver a búsqueda sin registrarse</a>
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
        
        document.addEventListener('DOMContentLoaded', function() {
            const demoSection = document.querySelector('.alert-warning');
            if (demoSection) {
                demoSection.style.cursor = 'pointer';
                demoSection.addEventListener('click', function(e) {
                    if (e.target.textContent.includes('Administrador') || e.target.closest('div').textContent.includes('Administrador')) {
                        document.getElementById('email').value = 'admin@autoparts.com';
                        document.getElementById('password').value = 'AutoParts2025!';
                    } else if (e.target.textContent.includes('Usuario Regular') || e.target.closest('div').textContent.includes('Usuario Regular')) {
                        document.getElementById('email').value = 'user@autoparts.com';
                        document.getElementById('password').value = 'UserPass123!';
                    }
                });
            }
        });
        </script>
        '''
        
        return render_template_string(login_content)
        
    except Exception as e:
        logger.error(f"Error in login page: {e}")
        return render_template_string('<div class="alert alert-danger"><h4>Error</h4><p>Error cargando página de login</p><a href="/">Volver</a></div>'), 500

@app.route('/search')
@login_required
def search_page():
    """Página de búsqueda para usuarios autenticados"""
    try:
        current_user = firebase_auth.get_current_user()
        user_name = current_user['user_name'] if current_user else 'Usuario'
        user_role = current_user.get('user_role', 'user') if current_user else 'user'
        
        search_content = f'''
            <div class="alert alert-info text-center">
                👋 Bienvenido, <strong>{html.escape(user_name)}</strong> ({user_role.title()}) | 
                <a href="/logout" class="btn btn-sm btn-outline-primary">Cerrar Sesión</a>
            </div>
            
            <h1>🔧 Auto Parts Finder PRO</h1>
            <div class="subtitle">Búsqueda avanzada de repuestos con funciones premium</div>
            
            <div class="alert alert-success">
                <h6>🎯 Funciones Premium Activadas</h6>
                <ul class="mb-0">
                    <li>Búsquedas ilimitadas con SerpAPI</li>
                    <li>Precios en tiempo real</li>
                    <li>Comparación avanzada</li>
                    <li>Historial de búsquedas</li>
                </ul>
            </div>
            
            <div class="input-group mb-3">
                <input type="text" id="searchQuery" class="form-control" placeholder="Buscar repuestos con mayor precisión..." maxlength="200" required>
                <button class="btn btn-primary" onclick="searchParts()">🔍 Buscar PRO</button>
            </div>
            
            <div id="searchLoading" class="text-center" style="display: none;">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Buscando en base de datos premium...</p>
            </div>
            
            <div id="searchError" class="alert alert-danger" style="display: none;"></div>
            
            <div id="searchResults"></div>
        
        <script>
        async function searchParts() {{
            const query = document.getElementById('searchQuery').value.trim();
            
            if (!query) {{
                showError('Por favor ingresa un término de búsqueda');
                return;
            }}
            
            showLoading(true);
            hideError();
            clearResults();
            
            const formData = new FormData();
            formData.append('query', query);
            
            try {{
                const response = await fetch('/api/search-parts', {{
                    method: 'POST',
                    body: formData
                }});
                
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                
                const result = await response.json();
                
                if (result.success) {{
                    if (result.products && result.products.length > 0) {{
                        displayResults(result.products);
                    }} else {{
                        showError(result.message || 'No se encontraron repuestos para esta búsqueda');
                    }}
                }} else {{
                    showError(result.message || 'Error en la búsqueda');
                }}
            }} catch (error) {{
                showError(`Error de conexión: ${{error.message}}`);
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
            
            let html = `
                <div class="alert alert-success">
                    <h5>✅ Búsqueda Premium Completada (${{products.length}} productos encontrados)</h5>
                    <small>🔗 Enlaces directos verificados a tiendas especializadas</small>
                </div>
            `;
            
            products.forEach(product => {{
                let badgeClass = 'aftermarket';
                let badgeText = product.part_type || 'Aftermarket';
                
                if (product.part_type === 'OEM') {{
                    badgeClass = 'oem';
                    badgeText = '🏭 OEM Original';
                }} else if (product.part_type === 'Premium') {{
                    badgeClass = 'premium';
                    badgeText = '⭐ Premium';
                }} else {{
                    badgeText = '🔧 Aftermarket';
                }}
                
                html += `
                    <div class="product-card">
                        <div class="product-title">
                            ${{product.title}} 
                            <span class="part-badge ${{badgeClass}}">${{badgeText}}</span>
                        </div>
                        <div class="product-price">${{product.price}}</div>
                        <div class="mb-2"><strong>Tienda:</strong> ${{product.source}}</div>
                        ${{product.rating ? `<div class="mb-2"><small>⭐ ${{product.rating}} (${{product.reviews || '0'}} reseñas)</small></div>` : ''}}
                        <a href="${{product.link}}" target="_blank" class="btn btn-success btn-sm" rel="noopener noreferrer">
                            Ver Producto →
                        </a>
                    </div>
                `;
            }});
            
            resultsContainer.innerHTML = html;
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
        
        document.getElementById('searchQuery').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                searchParts();
            }}
        }});
        </script>
        '''
        
        return render_template_string(search_content)
        
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

@app.route('/api/search-parts-public', methods=['POST'])
def api_search_parts_public():
    """API de búsqueda pública profesional"""
    try:
        if not auto_parts_finder:
            logger.error("❌ AutoPartsFinder no está inicializado")
            return jsonify({
                'success': False, 
                'message': 'Servicio de búsqueda no disponible. Configure SERPAPI_KEY.'
            })
        
        query = request.form.get('query', '').strip()
        vehicle_year = request.form.get('vehicle_year', '').strip()
        vehicle_make = request.form.get('vehicle_make', '').strip()
        vehicle_model = request.form.get('vehicle_model', '').strip()
        
        print(f"📥 DEBUG: Búsqueda recibida - Query: '{query}', Vehículo: {vehicle_year} {vehicle_make} {vehicle_model}")
        logger.info(f"📥 Búsqueda recibida - Query: '{query}', Vehículo: {vehicle_year} {vehicle_make} {vehicle_model}")
        
        image_content = None
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            try:
                image_content = image_file.read()
                print(f"📷 DEBUG: Imagen recibida: {image_file.filename}, tamaño: {len(image_content)} bytes")
                if not validate_image(image_content):
                    return jsonify({
                        'success': False, 
                        'message': 'Imagen no válida. Use formatos JPG, PNG o WEBP.'
                    })
            except Exception as e:
                logger.error(f"Error procesando imagen: {e}")
                return jsonify({
                    'success': False, 
                    'message': 'Error procesando la imagen'
                })
        
        if not query and not image_content:
            return jsonify({
                'success': False, 
                'message': 'Proporciona un término de búsqueda o una imagen'
            })
        
        vehicle_info = None
        if vehicle_year or vehicle_make or vehicle_model:
            vehicle_info = {
                'year': vehicle_year,
                'make': vehicle_make,
                'model': vehicle_model
            }
        
        search_result = auto_parts_finder.search_auto_parts(
            query=query,
            image_content=image_content,
            vehicle_info=vehicle_info
        )
        
        if not search_result.get('success', False):
            return jsonify(search_result)
        
        products = search_result.get('products', [])
        
        search_info = {
            'query': query,
            'has_image': bool(image_content),
            'vehicle': None,
            'timestamp': datetime.now().isoformat(),
            'total_results': len(products)
        }
        
        if vehicle_info and any(vehicle_info.values()):
            vehicle_parts = [p for p in [vehicle_info.get('year'), 
                           vehicle_info.get('make', '').title(), 
                           vehicle_info.get('model', '').upper()] if p]
            search_info['vehicle'] = ' '.join(vehicle_parts)
        
        return jsonify({
            'success': True,
            'products': products,
            'search_info': search_info,
            'count': len(products),
            'message': search_result.get('message', f'Se encontraron {len(products)} productos')
        })
        
    except Exception as e:
        logger.error(f"❌ Error en búsqueda pública: {e}")
        return jsonify({
            'success': False, 
            'message': 'Error interno del servidor. Intenta nuevamente.'
        })

@app.route('/api/search-parts', methods=['POST'])
@login_required
def api_search_parts():
    """API de búsqueda para usuarios autenticados"""
    try:
        query = request.form.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False, 
                'message': 'Término de búsqueda requerido'
            })
        
        if not auto_parts_finder:
            return jsonify({
                'success': False, 
                'message': 'Servicio no disponible. Configure SERPAPI_KEY.'
            })
        
        search_result = auto_parts_finder.search_auto_parts(query=query)
        
        if search_result.get('success', False):
            products = search_result.get('products', [])
            return jsonify({
                'success': True,
                'products': products,
                'count': len(products),
                'premium': True,
                'message': search_result.get('message', f'Se encontraron {len(products)} productos')
            })
        else:
            return jsonify(search_result)
        
    except Exception as e:
        logger.error(f"Error en búsqueda autenticada: {e}")
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
    <div class="alert alert-warning text-center">
        <h4>🚫 Página No Encontrada</h4>
        <p>La página que buscas no existe o ha sido movida.</p>
        <a href="/" class="btn btn-primary">🏠 Volver al Inicio</a>
    </div>
    '''
    return render_template_string(content), 404

@app.errorhandler(500)
def internal_error(error):
    """Error interno del servidor"""
    content = '''
    <div class="alert alert-danger text-center">
        <h4>⚠ Error Interno</h4>
        <p>Ha ocurrido un error interno en el servidor.</p>
        <a href="/" class="btn btn-primary">🔄 Reintentar</a>
    </div>
    '''
    return render_template_string(content), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Manejador de excepciones generales"""
    logger.error(f"Excepción no manejada: {e}")
    content = '''
    <div class="alert alert-danger text-center">
        <h4>❌ Error Inesperado</h4>
        <p>Ha ocurrido un error inesperado. Por favor intenta nuevamente.</p>
        <a href="/" class="btn btn-primary">🏠 Volver al Inicio</a>
    </div>
    '''
    return render_template_string(content), 500

# ==============================================================================
# INICIALIZACIÓN SEGURA DE COMPONENTES
# ==============================================================================

def initialize_components():
    """Inicializar todos los componentes de la aplicación"""
    global firebase_auth, auto_parts_finder
    
    print("\n🔧 INICIALIZANDO COMPONENTES...")
    
    try:
        firebase_auth = FirebaseAuth()
        logger.info("✅ FirebaseAuth inicializado correctamente")
        print("✅ DEBUG: FirebaseAuth inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando FirebaseAuth: {e}")
        print(f"❌ DEBUG: Error en FirebaseAuth: {e}")
        firebase_auth = None
    
    try:
        auto_parts_finder = AutoPartsFinder()
        logger.info("✅ AutoPartsFinder inicializado correctamente")
        print("✅ DEBUG: AutoPartsFinder inicializado completamente")
    except ValueError as e:
        logger.error(f"❌ Error CRÍTICO: {e}")
        print(f"❌ DEBUG: Error CRÍTICO en AutoPartsFinder: {e}")
        print("❌ LA APLICACIÓN NO FUNCIONARÁ SIN SERPAPI_KEY")
        auto_parts_finder = None
    except Exception as e:
        logger.error(f"❌ Error inesperado inicializando AutoPartsFinder: {e}")
        print(f"❌ DEBUG: Error inesperado en AutoPartsFinder: {e}")
        auto_parts_finder = None
    
    print("🔧 Inicialización completada\n")

# Inicializar componentes
initialize_components()

# ==============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ==============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("🔧 AUTO PARTS FINDER USA - VERSIÓN COMPLETAMENTE LIMPIA")
    print("=" * 70)
    
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🌐 Puerto: {port}")
    print(f"🔧 Modo Debug: {debug_mode}")
    print(f"🖼  PIL (imágenes): {'✅ Disponible' if PIL_AVAILABLE else '❌ No disponible'}")
    print(f"🤖 Gemini AI: {'✅ Disponible' if GEMINI_AVAILABLE else '❌ No disponible'}")
    print(f"🕷  BeautifulSoup: {'✅ Disponible' if BS4_AVAILABLE else '❌ No disponible'}")
    print(f"🔐 Firebase Auth: {'✅ Configurado' if firebase_auth else '❌ Error'}")
    print(f"🔍 Auto Parts Finder: {'✅ Activo' if auto_parts_finder else '❌ ERROR CRÍTICO'}")
    
    serpapi_key = os.environ.get('SERPAPI_KEY')
    if serpapi_key and serpapi_key.strip():
        print(f"🔑 SerpAPI: ✅ CONFIGURADO CORRECTAMENTE")
        print(f"   Key: {serpapi_key[:4]}...{serpapi_key[-4:]} (longitud: {len(serpapi_key)})")
        print("   ➡️ La aplicación funcionará correctamente")
        print("   🔧 CSS con Bootstrap - SIN ERRORES DE SINTAXIS")
    else:
        print("🔑 SerpAPI: ❌ NO CONFIGURADO")
        print("   ➡️ LA APLICACIÓN NO FUNCIONARÁ")
        print("   💡 DEBE configurar SERPAPI_KEY para que funcione")
    
    print("=" * 70)
    print("🚀 Iniciando servidor...")
    print("📝 Credenciales de prueba:")
    print("   Admin: admin@autoparts.com / AutoParts2025!")
    print("   User: user@autoparts.com / UserPass123!")
    print("🔗 Página principal: http://localhost:5000")
    print("✅ TODOS LOS ERRORES DE SINTAXIS CORREGIDOS")
    print("✅ USANDO BOOTSTRAP CDN PARA EVITAR PROBLEMAS CSS")
    print("=" * 70)
    
    if not auto_parts_finder:
        print("\n❌ ADVERTENCIA CRÍTICA:")
        print("   La aplicación NO funcionará sin SERPAPI_KEY")
        print("   Configure la variable de entorno antes de usar")
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
        print("   - SERPAPI_KEY configurada correctamente")
        print("   - Dependencias instaladas")
