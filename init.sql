USE emails;

CREATE TABLE emails (
    id INT AUTO_INCREMENT PRIMARY KEY,
    received_time DATETIME,
    subject VARCHAR(255),
    from_email VARCHAR(255),
    from_name VARCHAR(255),
    reply_to_email VARCHAR(255),
    reply_to_name VARCHAR(255),
    to_email VARCHAR(255),
    to_name VARCHAR(255),
    cc_email VARCHAR(255),
    cc_name VARCHAR(255),
    raw_headers TEXT,
    encoding VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_to_email (to_email)
);

CREATE TABLE email_attachments
 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email_id INT,
    filename VARCHAR(255),
    content_type VARCHAR(255),
    content LONGBLOB,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE TABLE email_parts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email_id INT,
    headers TEXT,
    content_type VARCHAR(255),
    content LONGTEXT,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX idx_to_email ON emails(to_email);