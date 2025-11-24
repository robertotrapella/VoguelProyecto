import random
from flask import Flask, render_template, request, jsonify

# --- Tu lógica de Vogel envuelta en una clase ---
class VogelSolver:
    def __init__(self, costos, oferta, demanda):
        self.matriz = costos
        self.oferta_inicial = oferta
        self.demanda_inicial = demanda
        
        self.steps = []
        self.text_log = []
        
        self.ficticia_fila_idx = -1
        self.ficticia_col_idx = -1

    def log_output(self, message):
        """ Guarda en el log de texto. """
        self.text_log.append(message)

    # Esta función está bien. Devuelve las listas de penalizaciones.
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

        # Obtenemos los índices de los máximos
        idx_p_fila = penalizaciones_fila.index(max_p_fila) if max_p_fila != -1 else -1
        idx_p_col = penalizaciones_columna.index(max_p_col) if max_p_col != -1 else -1
        
        # Devolvemos toda la información
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

    # --- CAMBIO PRINCIPAL AQUÍ ---
    # La lógica de 'solve' ahora maneja el desempate completo.
    def solve(self):
        try:
            self.log_output("--- Iniciando Proceso de Vogel ---")
            
            total_oferta = self.agregar_oferta()
            total_demanda = self.agregar_demanda()
            desbalance = self.calcular_desbalanceo(total_oferta, total_demanda)
            
            if desbalance != 0:
                tipo_faltante, restante = desbalance
                self.log_output(f"\nDesbalance: Falta {restante} de {tipo_faltante}. Agregando ficticia...")
                self.agregar_ficticia(tipo_faltante, restante)
            else:
                self.log_output("\nEl problema ya estaba balanceado.")

            lista_costos = []
            step_counter = 1
            
            filas_activas = len(self.matriz) - 1
            cols_activos = len(self.matriz[0]) - 1

            while True:
                demanda_restante = sum(self.matriz[-1][j] for j in range(cols_activos) if self.matriz[-1][j] > 0)
                oferta_restante = sum(self.matriz[i][-1] for i in range(filas_activas) if self.matriz[i][-1] > 0)
                
                if demanda_restante < 0.001 and oferta_restante < 0.001:
                    break

                # 1. Obtener toda la info de penalización
                status, max_p_fila_val, max_p_col_val, p_filas, p_cols = self.determinar_penalizacion()

                if status == "stop":
                    self.log_output("No hay más penalizaciones válidas.")
                    break
                
                # 2. Encontrar la penalización MÁXIMA en toda la tabla
                max_pen_overall = max(max_p_fila_val, max_p_col_val)
                
                if max_pen_overall == -1:
                    break
                    
                self.log_output(f"\nPenalización máxima encontrada: {max_pen_overall}")

                # 3. Encontrar TODOS los candidatos (filas/cols) con esta penalización
                candidates = [] # Almacenará tuplas: (tipo, index, min_costo_en_linea)
                
                # Buscar en filas
                for i in range(filas_activas):
                    if p_filas[i] == max_pen_overall:
                        min_costo = float('inf')
                        for j in range(cols_activos):
                            if self.matriz[-1][j] > 0 and self.matriz[i][j] < min_costo:
                                min_costo = self.matriz[i][j]
                        if min_costo != float('inf'):
                            candidates.append(('fila', i, min_costo))
                
                # Buscar en columnas
                for j in range(cols_activos):
                    if p_cols[j] == max_pen_overall:
                        min_costo = float('inf')
                        for i in range(filas_activas):
                            if self.matriz[i][-1] > 0 and self.matriz[i][j] < min_costo:
                                min_costo = self.matriz[i][j]
                        if min_costo != float('inf'):
                            candidates.append(('columna', j, min_costo))

                # 4. Manejar si no hay candidatos válidos (raro, pero posible)
                if not candidates:
                    self.log_output("Caso de parada: No se encontraron candidatos válidos.")
                    break
                    
                # 5. Decidir el ganador: el que tenga el costo mínimo (x[2])
                candidates.sort(key=lambda x: x[2])
                winner = candidates[0]
                
                tipo_elegido = winner[0]
                indice_elegido = winner[1]
                costo_minimo_elegido = winner[2]
                
                if len(candidates) > 1:
                     self.log_output(f"Empate de penalización resuelto por costo mínimo.")
                     self.log_output(f"Candidato ganador (costo: {costo_minimo_elegido}): {tipo_elegido} {indice_elegido + 1}.")
                
                # 6. Lógica de Asignación (encontrar la celda exacta)
                fila_idx, col_idx, min_costo = -1, -1, float('inf')

                if tipo_elegido == "fila":
                    fila_idx = indice_elegido
                    # Encontrar la columna con el costo mínimo en esta fila
                    for j in range(cols_activos):
                        if self.matriz[-1][j] > 0 and self.matriz[fila_idx][j] == costo_minimo_elegido:
                            col_idx = j
                            min_costo = costo_minimo_elegido
                            break # Tomar la primera que coincida
                else: # tipo == "columna"
                    col_idx = indice_elegido
                    # Encontrar la fila con el costo mínimo en esta columna
                    for i in range(filas_activas):
                        if self.matriz[i][-1] > 0 and self.matriz[i][col_idx] == costo_minimo_elegido:
                            fila_idx = i
                            min_costo = costo_minimo_elegido
                            break # Tomar la primera que coincida
                                
                if fila_idx == -1 or col_idx == -1:
                     self.log_output(f"Caso de parada: No se pudo asignar celda para {tipo_elegido} {indice_elegido+1}.")
                     break
                
                cantidad = min(self.matriz[fila_idx][-1], self.matriz[-1][col_idx])

                # 7. Capturar el paso ANTES de modificar la matriz
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
                
                # 8. Modificar la matriz
                self.matriz[fila_idx][-1] -= cantidad
                self.matriz[-1][col_idx] -= cantidad
                
                costo_parcial = cantidad * min_costo
                lista_costos.append(costo_parcial)
                
                self.log_output(f"Paso {step_counter}: Asignado {cantidad} de F{fila_idx+1} a C{col_idx+1}")
                step_counter += 1

            self.log_output("\n--- Asignación completada ---")
            self.log_output(f"Costo Total Mínimo: {sum(lista_costos)}")

        except Exception as e:
            self.log_output(f"\n--- ERROR EN LA EJECUCIÓN ---")
            self.log_output(f"Detalle: {str(e)}")
        
        return {
            'steps': self.steps,
            'log': self.text_log,
            'ficticia_fila': self.ficticia_fila_idx,
            'ficticia_col': self.ficticia_col_idx
        }


# --- Configuración de Flask (sin cambios) ---
app = Flask(__name__)

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