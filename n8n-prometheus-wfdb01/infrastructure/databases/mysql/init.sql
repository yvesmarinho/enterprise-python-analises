-- Criar tabela de teste para health checks
CREATE TABLE IF NOT EXISTS health_check (
    id INT AUTO_INCREMENT PRIMARY KEY,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir registro de teste
INSERT INTO health_check (check_time) VALUES (CURRENT_TIMESTAMP());

-- Criar usuário read-only para probes
CREATE USER IF NOT EXISTS 'probe_user'@'%' IDENTIFIED BY 'probe_pass_123';
GRANT SELECT ON n8n.health_check TO 'probe_user'@'%';
FLUSH PRIVILEGES;
