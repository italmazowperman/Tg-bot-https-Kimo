-- Таблица Orders
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    client_name VARCHAR(200) NOT NULL,
    container_count INTEGER DEFAULT 0,
    goods_type VARCHAR(100),
    route VARCHAR(200),
    transit_port VARCHAR(100),
    document_number VARCHAR(100),
    chinese_transport_company VARCHAR(200),
    iranian_transport_company VARCHAR(200),
    status VARCHAR(50) DEFAULT 'New',
    status_color VARCHAR(20) DEFAULT '#FFFFFF',
    
    creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    loading_date TIMESTAMP,
    departure_date TIMESTAMP,
    arrival_iran_date TIMESTAMP,
    truck_loading_date TIMESTAMP,
    arrival_turkmenistan_date TIMESTAMP,
    client_receiving_date TIMESTAMP,
    arrival_notice_date TIMESTAMP,
    tkm_date TIMESTAMP,
    eta_date TIMESTAMP,
    
    has_loading_photo BOOLEAN DEFAULT FALSE,
    has_local_charges BOOLEAN DEFAULT FALSE,
    has_tex BOOLEAN DEFAULT FALSE,
    
    notes TEXT,
    additional_info TEXT
);

-- Таблица Containers
CREATE TABLE IF NOT EXISTS containers (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    container_number VARCHAR(50),
    container_type VARCHAR(50) DEFAULT '20ft Standard',
    weight DECIMAL(10, 2),
    volume DECIMAL(10, 2),
    
    loading_date TIMESTAMP,
    departure_date TIMESTAMP,
    arrival_iran_date TIMESTAMP,
    truck_loading_date TIMESTAMP,
    arrival_turkmenistan_date TIMESTAMP,
    client_receiving_date TIMESTAMP,
    
    driver_first_name VARCHAR(100),
    driver_last_name VARCHAR(100),
    driver_company VARCHAR(200),
    truck_number VARCHAR(50),
    driver_iran_phone VARCHAR(50),
    driver_turkmenistan_phone VARCHAR(50),
    
    UNIQUE(order_id, container_number)
);

-- Таблица Tasks
CREATE TABLE IF NOT EXISTS tasks (
    task_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    description VARCHAR(500) NOT NULL,
    assigned_to VARCHAR(100),
    status VARCHAR(20) DEFAULT 'ToDo',
    priority VARCHAR(20) DEFAULT 'Medium',
    due_date TIMESTAMP,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для быстрого поиска
CREATE INDEX idx_orders_order_number ON orders(order_number);
CREATE INDEX idx_orders_client_name ON orders(client_name);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_tkm_date ON orders(tkm_date);
CREATE INDEX idx_containers_order_id ON containers(order_id);
CREATE INDEX idx_tasks_order_id ON tasks(order_id);
CREATE INDEX idx_tasks_status ON tasks(status);
