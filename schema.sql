-- Схема базы данных "Автоматизированное рабочее место библиотекаря"

PRAGMA foreign_keys = ON;

-- 1. Издательство
CREATE TABLE IF NOT EXISTS publisher (
    id_publisher INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    address TEXT,
    phone TEXT
);

-- 2. Книга
CREATE TABLE IF NOT EXISTS book (
    id_book INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    pages INTEGER,
    id_publisher INTEGER NOT NULL,
    FOREIGN KEY (id_publisher) REFERENCES publisher(id_publisher)
);

-- 3. Автор
CREATE TABLE IF NOT EXISTS author (
    id_author INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    country TEXT,
    birth_date TEXT,
    death_date TEXT
);

-- 4. Авторы книги (M:N)
CREATE TABLE IF NOT EXISTS book_author (
    id_book INTEGER NOT NULL,
    id_author INTEGER NOT NULL,
    PRIMARY KEY (id_book, id_author),
    FOREIGN KEY (id_book) REFERENCES book(id_book),
    FOREIGN KEY (id_author) REFERENCES author(id_author)
);

-- 5. Экземпляр книги
CREATE TABLE IF NOT EXISTS book_instance (
    id_instance INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT NOT NULL,
    price REAL NOT NULL DEFAULT 0,
    id_book INTEGER NOT NULL,
    FOREIGN KEY (id_book) REFERENCES book(id_book)
);

-- 6. Читательский билет
CREATE TABLE IF NOT EXISTS reader_card (
    id_reader_card INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    photo BLOB
);

-- 7. Выдача
CREATE TABLE IF NOT EXISTS issue (
    id_instance INTEGER NOT NULL,
    issue_date TEXT NOT NULL,
    return_date TEXT,
    id_reader_card INTEGER NOT NULL,
    PRIMARY KEY (id_instance, issue_date),
    FOREIGN KEY (id_instance) REFERENCES book_instance(id_instance),
    FOREIGN KEY (id_reader_card) REFERENCES reader_card(id_reader_card)
);

-- Представление: Отчёт по книжному фонду (по годам)
CREATE VIEW IF NOT EXISTS report_inventory AS
SELECT
    strftime('%Y', i.issue_date) AS year,
    b.id_book,
    b.title AS book_name,
    ROUND((SELECT SUM(price) FROM book_instance WHERE id_book = b.id_book), 2) AS total_value,
    (SELECT COUNT(*) FROM book_instance WHERE id_book = b.id_book) AS total_instances,
    COUNT(DISTINCT i.id_instance) AS issued_instances
FROM book b
JOIN book_instance bi ON b.id_book = bi.id_book
LEFT JOIN issue i ON bi.id_instance = i.id_instance
GROUP BY year, b.id_book, b.title
HAVING year IS NOT NULL
ORDER BY year DESC, b.title;