import streamlit as st
import sqlite3
import requests
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from datetime import datetime
import os
import io

# Database connection
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('votes.db', check_same_thread=False)
    c = conn.cursor()
    
    # Tabla de votos
    c.execute('''
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        case_id INTEGER,
        verdict TEXT,
        ts TIMESTAMP,
        UNIQUE(username, case_id)
    )
    ''')
    
    # Tabla de configuración
    c.execute('''
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT,
        ts TIMESTAMP
    )
    ''')
    
    conn.commit()
    return conn

# Load cases data
@st.cache_data(ttl=3600)
def load_cases():
    try:
        cases_url = os.environ["CASES_URL"]
        response = requests.get(cases_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error loading cases: {str(e)}")
        return []

# Database operations for votes
def get_user_votes(username: str) -> set:
    """Obtiene el conjunto de IDs de casos en los que ha votado un usuario"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT case_id FROM votes WHERE username = ?", (username,))
    return set(row[0] for row in c.fetchall())

def get_user_verdict(username: str, case_id: int) -> str:
    """Obtiene el veredicto actual de un usuario para un caso específico"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT verdict FROM votes WHERE username = ? AND case_id = ?", (username, case_id))
    result = c.fetchone()
    return result[0] if result else None

def save_vote(username: str, case_id: int, verdict: str) -> bool:
    """Guarda un nuevo voto en la base de datos"""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO votes (username, case_id, verdict, ts) VALUES (?, ?, ?, ?)",
            (username, case_id, verdict, datetime.now())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Ya votó en este caso
        return False
    except Exception as e:
        st.error(f"Error saving vote: {str(e)}")
        return False

def update_vote(username: str, case_id: int, verdict: str) -> bool:
    """Actualiza un voto existente en la base de datos"""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute(
            "UPDATE votes SET verdict = ?, ts = ? WHERE username = ? AND case_id = ?",
            (verdict, datetime.now(), username, case_id)
        )
        conn.commit()
        return c.rowcount > 0  # True si se actualizó al menos un registro
    except Exception as e:
        st.error(f"Error al actualizar voto: {str(e)}")
        return False

def get_all_votes() -> pd.DataFrame:
    """Obtiene todos los votos como un DataFrame"""
    conn = get_db_connection()
    query = "SELECT username, case_id, verdict, ts FROM votes"
    return pd.read_sql_query(query, conn)

def reset_all_votes():
    """Elimina todos los votos de la base de datos"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM votes")
    conn.commit()

# Database operations for config
def get_config(key: str, default_value: str = None) -> str:
    """Obtiene un valor de configuración por su clave"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key = ?", (key,))
    result = c.fetchone()
    return result[0] if result else default_value

def set_config(key: str, value: str) -> bool:
    """Establece un valor de configuración"""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO config (key, value, ts) VALUES (?, ?, ?)",
            (key, value, datetime.now())
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al guardar configuración: {str(e)}")
        return False

def get_show_results_to_students() -> bool:
    """Obtiene si se deben mostrar los resultados a los estudiantes"""
    result = get_config("show_results_to_students", "false")
    return result.lower() == "true"

def set_show_results_to_students(value: bool) -> bool:
    """Establece si se deben mostrar los resultados a los estudiantes"""
    return set_config("show_results_to_students", str(value).lower())

# Analytics and Metrics
def confusion_components(df: pd.DataFrame, threshold: float = 0.5):
    """Calcula las métricas de confusión y componentes para análisis"""
    if df.empty:
        return {
            'case_metrics': pd.DataFrame(),
            'accuracy': 0,
            'precision': 0,
            'recall': 0,
            'f1': 0
        }
        
    case_metrics = df.groupby('case_id').agg(
        total_votes=('verdict', 'count'),
        guilty_votes=('verdict', lambda x: (x == 'guilty').sum())
    )
    
    case_metrics['p_guilty'] = case_metrics['guilty_votes'] / case_metrics['total_votes']
    case_metrics['prediction'] = (case_metrics['p_guilty'] > threshold).map({True: 'guilty', False: 'innocent'})
    
    cases = load_cases()
    case_ground_truth = {case['id']: case['ground_truth'] for case in cases}
    
    case_metrics['ground_truth'] = case_metrics.index.map(lambda x: case_ground_truth.get(x))
    case_metrics['correct'] = case_metrics['prediction'] == case_metrics['ground_truth']
    
    y_true = case_metrics['ground_truth'].map({'guilty': 1, 'innocent': 0}).values
    y_pred = case_metrics['prediction'].map({'guilty': 1, 'innocent': 0}).values
    
    try:
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
    except:
        accuracy = precision = recall = f1 = 0
    
    return {
        'case_metrics': case_metrics,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }

# HTML Generators
def get_confusion_matrix_html(TN, FP, FN, TP):
    """
    Genera el HTML para una matriz de confusión con estilos
    
    Args:
        TN: Número de verdaderos negativos
        FP: Número de falsos positivos
        FN: Número de falsos negativos
        TP: Número de verdaderos positivos
        
    Returns:
        str: HTML formateado para la matriz de confusión
    """
    matrix_html = f"""
    <style>
    .matrix-table {{
      margin: 40px auto;
      border-collapse: separate;
      border-spacing: 8px;
    }}
    
    .matrix-table th, .matrix-table td {{
      text-align: center;
      padding: 0;
    }}
    
    .matrix-table th {{
      font-weight: bold;
      font-size: 16px;
      padding: 8px;
    }}
    
    .matrix-cell {{
      width: 200px;
      height: 200px;
      padding: 15px !important;
      vertical-align: middle;
      border: 2px solid #ddd;
    }}
    
    .tp-cell {{
      background-color: #d4edda;
    }}
    
    .tn-cell {{
      background-color: #d4edda;
    }}
    
    .fp-cell {{
      background-color: #f8d7da;
    }}
    
    .fn-cell {{
      background-color: #f8d7da;
    }}
    
    .matrix-label {{
      font-weight: bold;
      margin-bottom: 10px;
      font-size: 15px;
      display: block;
    }}
    
    .matrix-value {{
      font-size: 32px;
      font-weight: bold;
      margin: 10px 0;
      display: block;
    }}
    
    .matrix-description {{
      font-size: 13px;
      line-height: 1.3;
      display: block;
    }}
    
    .prediction-header {{
      font-style: italic;
      color: #444;
    }}
    
    .rotate-text {{
      writing-mode: vertical-lr;
      transform: rotate(180deg);
      height: 200px;
    }}
    </style>
    
    <table class="matrix-table">
      <thead>
        <tr>
          <th></th>
          <th colspan="2" class="prediction-header">Predicción</th>
        </tr>
        <tr>
          <th></th>
          <th>Inocente</th>
          <th>Culpable</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th rowspan="2" class="rotate-text">Verdad</th>
          <td class="matrix-cell tn-cell">
            <span class="matrix-label">Verdadero Negativo (TN)</span>
            <span class="matrix-value">{TN}</span>
            <span class="matrix-description">Correctamente clasificado como Inocente</span>
          </td>
          <td class="matrix-cell fp-cell">
            <span class="matrix-label">Falso Positivo (FP)</span>
            <span class="matrix-value">{FP}</span>
            <span class="matrix-description">Incorrectamente clasificado como Culpable</span>
          </td>
        </tr>
        <tr>
          <td class="matrix-cell fn-cell">
            <span class="matrix-label">Falso Negativo (FN)</span>
            <span class="matrix-value">{FN}</span>
            <span class="matrix-description">Incorrectamente clasificado como Inocente</span>
          </td>
          <td class="matrix-cell tp-cell">
            <span class="matrix-label">Verdadero Positivo (TP)</span>
            <span class="matrix-value">{TP}</span>
            <span class="matrix-description">Correctamente clasificado como Culpable</span>
          </td>
        </tr>
      </tbody>
    </table>
    """
    return matrix_html