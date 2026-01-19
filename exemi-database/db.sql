DROP TABLE IF EXISTS message;
DROP TABLE IF EXISTS conversation;
DROP TABLE IF EXISTS participant;

CREATE TABLE participant (
    id INT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    disabled BOOL DEFAULT FALSE,
    token VARCHAR(255),
    bio TEXT
) ENGINE = InnoDB;

CREATE TABLE conversation (
    id INT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    participant_id INT UNSIGNED NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_conversation_participant`
        FOREIGN KEY (participant_id) REFERENCES participant (id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE message (
    id INT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    conversation_id INT UNSIGNED NOT NULL,
    role ENUM('user','assistant','system') NOT NULL,
    context TEXT NOT NULL,
    CONSTRAINT `fk_message_conversation`
        FOREIGN KEY (conversation_id) REFERENCES conversation (id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT
) ENGINE = InnoDB;
