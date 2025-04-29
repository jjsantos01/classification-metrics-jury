# Juicio Interactivo

Aplicación interactiva desarrollada con Streamlit que simula un juicio donde los estudiantes actúan como jurado, votando sobre la culpabilidad de acusados en casos ficticios. La herramienta transforma esta experiencia en una oportunidad de aprendizaje sobre matrices de confusión y métricas de clasificación (accuracy, precision, recall, F1 score).

## Características principales

- Sistema de registro y persistencia de usuarios
- Interfaz intuitiva para navegar y votar en casos
- Panel de administración con análisis de métricas y visualizaciones
- Funcionalidad para modificar votos y comparar decisiones con la "verdad"
- Matriz de confusión interactiva que muestra aciertos y errores del "jurado"
- Opción para revelar resultados a los estudiantes al finalizar la actividad

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Conexión a internet (para cargar los casos)

## Instalación

1. Clona el repositorio:

```bash
git clone https://github.com/jjsantos01/classification-metrics-jury.git
cd classification-metrics-jury
```

2. Crea un entorno virtual (recomendado):

```bash
python -m venv venv

# En Windows
venv\Scripts\activate

# En macOS/Linux
source venv/bin/activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Configuración

### Variables de entorno

La aplicación requiere una contraseña de administrador, que puede configurarse de las siguientes maneras:

1. Mediante una variable de entorno:

```bash
# En Windows
set ADMIN_PWD=tu_contraseña_secreta

# En macOS/Linux
export ADMIN_PWD=tu_contraseña_secreta
```

2. O creando un archivo `.streamlit/secrets.toml` con el siguiente contenido:

```toml
ADMIN_PWD = "tu_contraseña_secreta"
CASES_URL = "https://url-a-tus-casos.json"
```

### Casos de prueba

Por defecto, la aplicación busca los casos en una URL remota. Para configurar tu propia fuente de casos:

1. Crea un archivo JSON con el siguiente formato:

```json
[
  {
    "id": 1,
    "description": "Descripción del caso 1",
    "image": "URL a una imagen (opcional)",
    "ground_truth": "guilty"
  },
  {
    "id": 2,
    "description": "Descripción del caso 2",
    "image": "URL a una imagen (opcional)",
    "ground_truth": "innocent"
  }
]
```

2. Aloja este archivo en un servidor web o configura la ruta local en `secrets.toml`.

## Ejecución

Para iniciar la aplicación:

```bash
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501` por defecto.

## Estructura del proyecto

- `app.py`: Punto de entrada principal
- `utils.py`: Funciones utilitarias y acceso a datos
- `views.py`: Componentes de la interfaz de usuario
- `votes.db`: Base de datos SQLite (creada automáticamente)
- `requirements.txt`: Dependencias del proyecto

## Uso básico

### Para estudiantes

1. Ingresa un nombre de usuario (3-20 caracteres alfanuméricos, guión o underscore).
2. Navega por los casos usando los botones "Anterior" y "Siguiente".
3. Para cada caso, vota si el acusado es "Culpable" o "Inocente".
4. Puedes cambiar tu voto en cualquier momento antes de que el instructor revele los resultados.
5. Una vez que el instructor activa la opción "Mostrar resultados", podrás ver el análisis completo.

### Para administradores

1. Inicia sesión con el usuario `admin` y la contraseña configurada.
2. El panel de administración te permitirá:
   - Ver las estadísticas de todos los casos
   - Configurar el umbral para clasificación
   - Activar/desactivar la visualización de resultados para los estudiantes
   - Descargar la base de datos
   - Reiniciar todos los votos

## Despliegue en la nube

La aplicación puede desplegarse fácilmente en Streamlit Cloud:

1. Sube el código a un repositorio GitHub.
2. Regístrate en [Streamlit Cloud](https://streamlit.io/cloud).
3. Conecta tu repositorio y configura los secretos en la configuración.

## Solución de problemas

- **Error de conexión a la base de datos**: Verifica los permisos en el directorio de la aplicación.
- **Los casos no se cargan**: Comprueba la URL de casos en `secrets.toml` o asegúrate de tener conexión a internet.
- **Error de contraseña**: Verifica que la variable `ADMIN_PWD` esté correctamente configurada.

## Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo LICENSE para más detalles.

---
