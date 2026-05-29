CREATE TABLE IF NOT EXISTS registros_tiempo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_tecnico VARCHAR(100) NOT NULL,
    tipo_registro ENUM('Entrada', 'Salida') NOT NULL,
    latitud DECIMAL(10, 8) NOT NULL,
    longitud DECIMAL(11, 8) NOT NULL,
    precision_gps DECIMAL(10, 2) NOT NULL,
    marca_de_tiempo TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuarios_admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);
