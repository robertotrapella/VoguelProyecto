import os
import random
from flask import Flask, render_template, request, jsonify, send_from_directory

class VogelSolver:
    def __init__(self, costos, oferta, demanda):
        self.matriz = costos
        self.oferta_inicial = oferta
        self.demanda_inicial = demanda
        
        self.steps = []
        self.assignments = [] # <--- NUEVA LISTA PARA GUARDAR (CANTIDAD, COSTO)
        self.text_log = [] # Lo mantenemos por si acaso, pero ya no es vital
        
        self.ficticia_fila_idx = -1
        self.ficticia_col_idx = -1

    def log_output(self, message):
        self.text_log.append(message)

    def determinar_penalizacion(self):
        filas_totales = len(self.matriz) - 1
        cols_totales = len(self.matriz[0]) - 1
        penalizaciones_fila = [-1] * filas_totales
        penalizaciones_columna = [-1] * cols_totales

        for i in range(filas_totales):
            if self.matriz[i][-1] > 0:
                costos_validos = [self.matriz[i][j] for j in range(cols_totales) if self.matriz[-1][j] > 0]
                costos_ord = sorted(costos_validos)
                if len(costos_ord) >= 2:
                    penalizaciones_fila[i] = costos_ord[1] - costos_ord[0]
                elif len(costos_ord) == 1:
                    penalizaciones_fila[i] = costos_ord[0]

        for j in range(cols_totales):
            if self.matriz[-1][j] > 0:
                costos_validos = [self.matriz[i][j] for i in range(filas_totales) if self.matriz[i][-1] > 0]
                costos_ord = sorted(costos_validos)
                if len(costos_ord) >= 2:
                    penalizaciones_columna[j] = costos_ord[1] - costos_ord[0]
                elif len(costos_ord) == 1:
                    penalizaciones_columna[j] = costos_ord[0]

        max_p_fila = max(penalizaciones_fila)
        max_p_col = max(penalizaciones_columna)

        if max_p_fila == -1 and max_p_col == -1:
            return "stop", 0, 0, [], []

        return "continue", max_p_fila, max_p_col, penalizaciones_fila, penalizaciones_columna


    def agregar_demanda(self):
        lista_demanda = self.demanda_inicial.copy()
        total_demanda = sum(lista_demanda)
        lista_demanda.append(0)
        self.matriz.append(lista_demanda)
        return total_demanda

    def agregar_oferta(self):
        lista_oferta = self.oferta_inicial.copy()
        total_oferta = sum(lista_oferta)
        for i in range(len(self.matriz)):
            self.matriz[i].append(lista_oferta[i])
        return total_oferta

    def calcular_desbalanceo(self, total_oferta, total_demanda):
        if total_oferta == total_demanda:
            return 0
        elif total_oferta > total_demanda:
            return "demanda", total_oferta - total_demanda
        elif total_oferta < total_demanda:
            return "oferta", total_demanda - total_oferta

    def agregar_ficticia(self, tipo, restante):
        if tipo == "demanda":
            for i in range(len(self.matriz)-1):
                self.matriz[i].insert(-1, 0)
            self.matriz[-1].insert(-1, restante)
            self.ficticia_col_idx = len(self.matriz[0]) - 2 
        elif tipo == "oferta":
            nueva_fila = [0] * (len(self.matriz[0])-1)
            nueva_fila.append(restante)
            self.matriz.insert(-1, nueva_fila)
            self.ficticia_fila_idx = len(self.matriz) - 2

    def solve(self):
        try:
            total_oferta = self.agregar_oferta()
            total_demanda = self.agregar_demanda()
            desbalance = self.calcular_desbalanceo(total_oferta, total_demanda)
            
            if desbalance != 0:
                tipo_faltante, restante = desbalance
                self.agregar_ficticia(tipo_faltante, restante)

            step_counter = 1
            filas_activas = len(self.matriz) - 1
            cols_activos = len(self.matriz[0]) - 1

            while True:
                demanda_restante = sum(self.matriz[-1][j] for j in range(cols_activos) if self.matriz[-1][j] > 0)
                oferta_restante = sum(self.matriz[i][-1] for i in range(filas_activas) if self.matriz[i][-1] > 0)
                
                if demanda_restante < 0.001 and oferta_restante < 0.001:
                    break

                status, max_p_fila_val, max_p_col_val, p_filas, p_cols = self.determinar_penalizacion()

                if status == "stop":
                    break
                
                max_pen_overall = max(max_p_fila_val, max_p_col_val)
                if max_pen_overall == -1: break
                    
                candidates = [] 
                
                for i in range(filas_activas):
                    if p_filas[i] == max_pen_overall:
                        min_costo = float('inf')
                        for j in range(cols_activos):
                            if self.matriz[-1][j] > 0 and self.matriz[i][j] < min_costo:
                                min_costo = self.matriz[i][j]
                        if min_costo != float('inf'):
                            candidates.append(('fila', i, min_costo))
                
                for j in range(cols_activos):
                    if p_cols[j] == max_pen_overall:
                        min_costo = float('inf')
                        for i in range(filas_activas):
                            if self.matriz[i][-1] > 0 and self.matriz[i][j] < min_costo:
                                min_costo = self.matriz[i][j]
                        if min_costo != float('inf'):
                            candidates.append(('columna', j, min_costo))

                if not candidates: break
                    
                candidates.sort(key=lambda x: x[2])
                winner = candidates[0]
                
                tipo_elegido = winner[0]
                indice_elegido = winner[1]
                costo_minimo_elegido = winner[2]
                
                fila_idx, col_idx, min_costo = -1, -1, float('inf')

                if tipo_elegido == "fila":
                    fila_idx = indice_elegido
                    for j in range(cols_activos):
                        if self.matriz[-1][j] > 0 and self.matriz[fila_idx][j] == costo_minimo_elegido:
                            col_idx = j
                            min_costo = costo_minimo_elegido
                            break 
                else: 
                    col_idx = indice_elegido
                    for i in range(filas_activas):
                        if self.matriz[i][-1] > 0 and self.matriz[i][col_idx] == costo_minimo_elegido:
                            fila_idx = i
                            min_costo = costo_minimo_elegido
                            break 
                                
                if fila_idx == -1 or col_idx == -1: break
                
                cantidad = min(self.matriz[fila_idx][-1], self.matriz[-1][col_idx])

                current_step_data = {
                    'step': step_counter,
                    'matrix': [row.copy() for row in self.matriz], 
                    'row_penalties': p_filas,
                    'col_penalties': p_cols,
                    'chosen_penalty': (tipo_elegido, indice_elegido, max_pen_overall), 
                    'chosen_cell': (fila_idx, col_idx),
                    'assigned_amount': cantidad
                }
                self.steps.append(current_step_data)
                
                # GUARDAR EL CÁLCULO PARA EL FINAL
                self.assignments.append({
                    'cantidad': cantidad,
                    'costo': min_costo,
                    'total': cantidad * min_costo
                })

                self.matriz[fila_idx][-1] -= cantidad
                self.matriz[-1][col_idx] -= cantidad
                
                step_counter += 1

            total_cost = sum(x['total'] for x in self.assignments)

        except Exception as e:
            self.log_output(f"Error: {str(e)}")
            total_cost = 0
        
        return {
            'steps': self.steps,
            'ficticia_fila': self.ficticia_fila_idx,
            'ficticia_col': self.ficticia_col_idx,
            'calculos': self.assignments,   # <--- LISTA DE MULTIPLICACIONES
            'total_general': total_cost     # <--- SUMA FINAL
        }


app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.png', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solve', methods=['POST'])
def solve_vogel():
    try:
        data = request.get_json()
        costos = data['costos']
        oferta = data['oferta']
        demanda = data['demanda']

        if not costos or not oferta or not demanda:
            return jsonify({'error': 'Datos incompletos.'}), 400

        solver = VogelSolver(costos, oferta, demanda)
        result_data = solver.solve()
        
        return jsonify(result_data)

    except Exception as e:
        return jsonify({'error': f'Error en el servidor: {str(e)}'}), 500

if __name__ == "__main__":
    app.run(debug=True)