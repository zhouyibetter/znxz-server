USE `dialog_znxz`;

DROP TABLE IF EXISTS `dialog`;

DROP TABLE IF EXISTS `session`;

CREATE TABLE IF NOT EXISTS `session` (
    `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `session_name` varchar(255) NOT NULL,
    `user_id` INT NOT NULL,
    `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `dialog` (
    `id` int(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `session_id` int(11) NOT NULL,
    `question` text NOT NULL,
    `message` text NOT NULL,
    `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
);

SELECT MAX(id) FROM session;