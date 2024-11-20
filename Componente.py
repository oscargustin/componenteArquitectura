from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import psycopg2
from datetime import datetime

app = Flask(__name__)
api = Api(app)

# Configuración de la base de datos
DB_CONFIG = {
    'dbname': 'componenteArquitectura',
    'user': 'postgres',
    'password': 'A1234',
    'host': 'localhost',
    'port': '5432'
}

# Conexión a PostgreSQL
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# Inserción de datos en la base de datos (solo una vez)
def insertar_datos_iniciales():
    try:
        with psycopg2.connect(**DB_CONFIG) as connection:
            with connection.cursor() as cursor:
                # Inserción en la tabla departamento
                cursor.execute("""INSERT INTO departamento (numero) VALUES ('106'), ('108');""")
                
                # Inserción en la tabla gasto_comun
                cursor.execute("""
                    INSERT INTO gasto_comun (departamento_id, periodo, monto)
                    VALUES (1, '2024-01-01', 50000),
                           (2, '2024-02-01', 60000);
                """)
            connection.commit()  # Confirmar los cambios
        print("Datos insertados exitosamente.")
    except Exception as e:
        print("Error al insertar datos:", e)

# Ruta para obtener departamentos
@app.route('/departamentos', methods=['GET'])
def get_departamentos():
    try:
        with psycopg2.connect(**DB_CONFIG) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM departamento;")
                data = cursor.fetchall()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})

# Rutas de la API
class GenerarGastos(Resource):
    def post(self):
        data = request.json
        mes = data.get('mes')
        anio = data.get('anio')
        monto_base = data.get('monto_base', 100000)

        if not mes or not anio:
            return {"error": "Debe especificar mes y año"}, 400

        periodo = datetime(int(anio), int(mes), 1)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Obtener todos los departamentos
                cur.execute("SELECT id FROM departamento")
                departamentos = cur.fetchall()

                # Crear gastos para cada departamento
                for depto in departamentos:
                    cur.execute("""
                        INSERT INTO gasto_comun (departamento_id, periodo, monto)
                        VALUES (%s, %s, %s)
                    """, (depto[0], periodo, monto_base))

                conn.commit()

        return {"message": "Gastos comunes generados con exito"}, 201


class MarcarPago(Resource):
    def post(self):
        data = request.json
        departamento_id = data.get('departamento_id')
        mes = data.get('mes')
        anio = data.get('anio')
        fecha_pago = data.get('fecha_pago')

        if not departamento_id or not mes or not anio or not fecha_pago:
            return {"error": "Faltan datos obligatorios"}, 400

        periodo = datetime(int(anio), int(mes), 1)
        fecha_pago_dt = datetime.strptime(fecha_pago, '%Y-%m-%d')

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verificar si el gasto existe
                cur.execute("""
                    SELECT pagado FROM gasto_comun
                    WHERE departamento_id = %s AND periodo = %s
                """, (departamento_id, periodo))
                gasto = cur.fetchone()

                if not gasto:
                    return {"error": "Gasto no encontrado"}, 404

                if gasto[0]:
                    return {"message": "Pago duplicado"}, 409

                # Marcar como pagado
                cur.execute("""
                    UPDATE gasto_comun
                    SET pagado = TRUE, fecha_pago = %s
                    WHERE departamento_id = %s AND periodo = %s
                """, (fecha_pago_dt, departamento_id, periodo))

                conn.commit()

        return {"message": "Pago exitoso"}, 200


class GastosPendientes(Resource):
    def get(self):
        mes = request.args.get('mes')
        anio = request.args.get('anio')

        if not mes or not anio:
            return {"error": "Debe especificar mes y año"}, 400

        periodo_limite = datetime(int(anio), int(mes), 1)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Obtener gastos pendientes hasta el período límite
                cur.execute("""
                    SELECT departamento_id, periodo, monto
                    FROM gasto_comun
                    WHERE periodo <= %s AND pagado = FALSE
                    ORDER BY periodo ASC
                """, (periodo_limite,))
                pendientes = cur.fetchall()

        if not pendientes:
            return {"message": "Sin montos pendientes"}, 200

        result = [
            {"departamento_id": row[0], "periodo": row[1].strftime('%Y-%m-%d'), "monto": float(row[2])}
            for row in pendientes
        ]
        return jsonify(result)



api.add_resource(GenerarGastos, '/gastos/generar')
api.add_resource(MarcarPago, '/gastos/pagar')
api.add_resource(GastosPendientes, '/gastos/pendientes')

if __name__ == '__main__':
    insertar_datos_iniciales()

    app.run(debug=True)
