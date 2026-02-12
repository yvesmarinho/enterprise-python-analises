-- Criar tabela de teste para health checks
CREATE TABLE IF NOT EXISTS health_check (
    id SERIAL PRIMARY KEY,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir registro de teste
INSERT INTO health_check (check_time) VALUES (CURRENT_TIMESTAMP);

-- Criar usuário read-only para probes
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'probe_user') THEN
        CREATE USER probe_user WITH PASSWORD 'probe_pass_123';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE n8n TO probe_user;
GRANT SELECT ON health_check TO probe_user;
