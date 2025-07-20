-- Healthcare Medicine Monitoring Platform Database Schema
-- SQLite Database for Flask Backend

-- Create database and enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Users table (for pharmacies, patients, admin users)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('pharmacy', 'patient', 'admin', 'ngo', 'government')),
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Locations table (districts, states, cities)
CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    location_type VARCHAR(20) NOT NULL CHECK (location_type IN ('state', 'district', 'city', 'area')),
    parent_id INTEGER,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES locations(id)
);

-- Pharmacies table
CREATE TABLE pharmacies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    pharmacy_name VARCHAR(200) NOT NULL,
    license_number VARCHAR(50) UNIQUE NOT NULL,
    address TEXT NOT NULL,
    location_id INTEGER NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    phone VARCHAR(15),
    is_verified BOOLEAN DEFAULT FALSE,
    operating_hours TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

-- Medicines table (master list of medicines)
CREATE TABLE medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    generic_name VARCHAR(200),
    brand_name VARCHAR(200),
    dosage_form VARCHAR(50), -- tablet, capsule, injection, etc.
    strength VARCHAR(50),
    category VARCHAR(100), -- essential, controlled, etc.
    manufacturer VARCHAR(200),
    is_essential BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pharmacy inventory table
CREATE TABLE pharmacy_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pharmacy_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    current_stock INTEGER NOT NULL DEFAULT 0,
    unit_price DECIMAL(10, 2) NOT NULL,
    mrp DECIMAL(10, 2),
    batch_number VARCHAR(50),
    expiry_date DATE,
    last_restocked_date DATE,
    minimum_stock_level INTEGER DEFAULT 10,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pharmacy_id) REFERENCES pharmacies(id),
    FOREIGN KEY (medicine_id) REFERENCES medicines(id),
    UNIQUE(pharmacy_id, medicine_id, batch_number)
);

-- Patient reports table (crowdsourced data)
CREATE TABLE patient_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    medicine_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    report_type VARCHAR(20) NOT NULL CHECK (report_type IN ('shortage', 'overpriced', 'unavailable', 'fake')),
    pharmacy_id INTEGER, -- optional, if specific pharmacy mentioned
    reported_price DECIMAL(10, 2),
    expected_price DECIMAL(10, 2),
    description TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (medicine_id) REFERENCES medicines(id),
    FOREIGN KEY (location_id) REFERENCES locations(id),
    FOREIGN KEY (pharmacy_id) REFERENCES pharmacies(id)
);

-- Price history table (for tracking price trends)
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pharmacy_id INTEGER NOT NULL,
    medicine_id INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    mrp DECIMAL(10, 2),
    stock_level INTEGER,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pharmacy_id) REFERENCES pharmacies(id),
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);

-- Shortage alerts table
CREATE TABLE shortage_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    alert_type VARCHAR(20) NOT NULL CHECK (alert_type IN ('shortage', 'price_spike', 'unavailable')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT,
    affected_pharmacies_count INTEGER DEFAULT 0,
    average_price DECIMAL(10, 2),
    price_increase_percentage DECIMAL(5, 2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

-- Notifications table
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    alert_id INTEGER,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(20) NOT NULL CHECK (notification_type IN ('shortage', 'price_alert', 'system', 'verification')),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (alert_id) REFERENCES shortage_alerts(id)
);

-- API logs table (for tracking API usage)
CREATE TABLE api_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    endpoint VARCHAR(100),
    method VARCHAR(10),
    request_data TEXT,
    response_status INTEGER,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- System settings table
CREATE TABLE system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_user_type ON users(user_type);
CREATE INDEX idx_pharmacy_inventory_medicine ON pharmacy_inventory(medicine_id);
CREATE INDEX idx_pharmacy_inventory_pharmacy ON pharmacy_inventory(pharmacy_id);
CREATE INDEX idx_patient_reports_medicine ON patient_reports(medicine_id);
CREATE INDEX idx_patient_reports_location ON patient_reports(location_id);
CREATE INDEX idx_patient_reports_created_at ON patient_reports(created_at);
CREATE INDEX idx_price_history_medicine ON price_history(medicine_id);
CREATE INDEX idx_price_history_pharmacy ON price_history(pharmacy_id);
CREATE INDEX idx_shortage_alerts_medicine ON shortage_alerts(medicine_id);
CREATE INDEX idx_shortage_alerts_location ON shortage_alerts(location_id);
CREATE INDEX idx_shortage_alerts_active ON shortage_alerts(is_active);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read);

-- Insert sample data for testing

-- Insert locations (Indian states and districts)
INSERT INTO locations (name, location_type, parent_id) VALUES
('Maharashtra', 'state', NULL),
('Karnataka', 'state', NULL),
('Delhi', 'state', NULL),
('Mumbai', 'district', 1),
('Pune', 'district', 1),
('Bengaluru', 'district', 2),
('New Delhi', 'district', 3);

-- Insert essential medicines
INSERT INTO medicines (name, generic_name, brand_name, dosage_form, strength, category, manufacturer, is_essential) VALUES
('Insulin Human', 'Human Insulin', 'Humulin', 'injection', '100IU/ml', 'essential', 'Eli Lilly', TRUE),
('Levothyroxine', 'Levothyroxine Sodium', 'Eltroxin', 'tablet', '50mcg', 'essential', 'Aspen Pharma', TRUE),
('Metformin', 'Metformin HCl', 'Glucophage', 'tablet', '500mg', 'essential', 'Bristol Myers', TRUE),
('Paracetamol', 'Paracetamol', 'Crocin', 'tablet', '500mg', 'essential', 'GSK', TRUE),
('Amlodipine', 'Amlodipine Besylate', 'Norvasc', 'tablet', '5mg', 'essential', 'Pfizer', TRUE);

-- Insert sample users
INSERT INTO users (username, email, password_hash, user_type, full_name, phone, is_verified) VALUES
('admin', 'admin@healthmonitor.com', 'pbkdf2:sha256:hash', 'admin', 'System Administrator', '9999999999', TRUE),
('apollo_pharmacy', 'apollo@pharmacy.com', 'pbkdf2:sha256:hash', 'pharmacy', 'Apollo Pharmacy', '9888888888', TRUE),
('patient1', 'patient1@email.com', 'pbkdf2:sha256:hash', 'patient', 'John Doe', '9777777777', TRUE),
('health_dept', 'health@gov.in', 'pbkdf2:sha256:hash', 'government', 'Health Department', '9666666666', TRUE);

-- Insert sample pharmacy
INSERT INTO pharmacies (user_id, pharmacy_name, license_number, address, location_id, phone, is_verified) VALUES
(2, 'Apollo Pharmacy - Andheri', 'MH-MUM-2024-001', '123 Main Street, Andheri West, Mumbai', 4, '9888888888', TRUE);

-- Insert sample inventory
INSERT INTO pharmacy_inventory (pharmacy_id, medicine_id, current_stock, unit_price, mrp, minimum_stock_level) VALUES
(1, 1, 5, 450.00, 500.00, 10),  -- Low stock insulin
(1, 2, 50, 25.00, 30.00, 20),
(1, 3, 100, 8.00, 10.00, 30),
(1, 4, 200, 2.50, 3.00, 50),
(1, 5, 75, 15.00, 18.00, 25);

-- Insert sample patient reports
INSERT INTO patient_reports (user_id, medicine_id, location_id, report_type, pharmacy_id, reported_price, expected_price, description) VALUES
(3, 1, 4, 'shortage', 1, 600.00, 500.00, 'Insulin not available at regular pharmacy, found at higher price elsewhere'),
(3, 2, 4, 'overpriced', NULL, 50.00, 30.00, 'Thyroid medication price increased suddenly');

-- Insert system settings
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('max_price_increase_threshold', '20', 'Maximum percentage price increase before alert'),
('min_stock_alert_threshold', '10', 'Minimum stock level before shortage alert'),
('alert_cooldown_hours', '24', 'Hours to wait before sending duplicate alerts'),
('verification_required', 'true', 'Whether patient reports require verification');

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_users_timestamp 
    AFTER UPDATE ON users
    FOR EACH ROW
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_pharmacies_timestamp 
    AFTER UPDATE ON pharmacies
    FOR EACH ROW
    BEGIN
        UPDATE pharmacies SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_inventory_timestamp 
    AFTER UPDATE ON pharmacy_inventory
    FOR EACH ROW
    BEGIN
        UPDATE pharmacy_inventory SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Create trigger to automatically create price history entries
CREATE TRIGGER inventory_price_history 
    AFTER UPDATE ON pharmacy_inventory
    FOR EACH ROW
    WHEN NEW.unit_price != OLD.unit_price OR NEW.current_stock != OLD.current_stock
    BEGIN
        INSERT INTO price_history (pharmacy_id, medicine_id, price, mrp, stock_level)
        VALUES (NEW.pharmacy_id, NEW.medicine_id, NEW.unit_price, NEW.mrp, NEW.current_stock);
    END;