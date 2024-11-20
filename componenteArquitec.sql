CREATE TABLE departamento (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE gasto_comun (
    id SERIAL PRIMARY KEY,
    departamento_id INTEGER REFERENCES departamento(id),
    periodo DATE NOT NULL,
    monto NUMERIC(10, 2) NOT NULL,
    pagado BOOLEAN DEFAULT FALSE,
    fecha_pago DATE
);