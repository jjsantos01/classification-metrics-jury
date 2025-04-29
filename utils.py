matrix_html = """
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
    