"""Автоматизированное рабочее место библиотекаря"""
import os
import sqlite3
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = 'lib-secret-key-2026'

DB_PATH = os.path.join(os.path.dirname(__file__), 'library.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


#  Каталог книг

@app.route('/')
def index():
    return redirect(url_for('catalog'))


@app.route('/catalog')
def catalog():
    conn = get_db()
    search = request.args.get('search', '').strip()
    if search:
        rows = conn.execute("""
            SELECT b.*, p.name AS publisher_name
            FROM book b
            JOIN publisher p ON b.id_publisher = p.id_publisher
            WHERE b.title LIKE ?
            ORDER BY b.title
        """, (f'%{search}%',)).fetchall()
    else:
        rows = conn.execute("""
            SELECT b.*, p.name AS publisher_name
            FROM book b
            JOIN publisher p ON b.id_publisher = p.id_publisher
            ORDER BY b.title
        """).fetchall()
    conn.close()
    return render_template('catalog.html', books=rows, search=search)


@app.route('/book/<int:book_id>')
def book_detail(book_id):
    conn = get_db()
    book = conn.execute("""
        SELECT b.*, p.name AS publisher_name
        FROM book b JOIN publisher p ON b.id_publisher = p.id_publisher
        WHERE b.id_book = ?
    """, (book_id,)).fetchone()

    authors = conn.execute("""
        SELECT a.* FROM author a
        JOIN book_author ba ON a.id_author = ba.id_author
        WHERE ba.id_book = ?
    """, (book_id,)).fetchall()

    instances = conn.execute("""
        SELECT bi.*,
               CASE WHEN active.id_instance IS NOT NULL
                    THEN 'Выдана' ELSE 'Доступна'
               END AS status,
               active.issue_date, active.return_date,
               rc.full_name AS reader_name
        FROM book_instance bi
        LEFT JOIN (
            SELECT id_instance, MAX(issue_date) as issue_date,
                   return_date, id_reader_card
            FROM issue
            WHERE return_date IS NULL
            GROUP BY id_instance
        ) active ON bi.id_instance = active.id_instance
        LEFT JOIN reader_card rc ON active.id_reader_card = rc.id_reader_card
        WHERE bi.id_book = ?
        ORDER BY bi.location
    """, (book_id,)).fetchall()

    conn.close()
    return render_template('book_detail.html', book=book, authors=authors, instances=instances)


#  Читатели

@app.route('/readers')
def readers():
    conn = get_db()
    search = request.args.get('search', '').strip()
    if search:
        rows = conn.execute("""
            SELECT rc.*,
                   (SELECT COUNT(*) FROM issue i WHERE i.id_reader_card = rc.id_reader_card AND i.return_date IS NULL) AS books_on_hands
            FROM reader_card rc
            WHERE rc.full_name LIKE ?
            ORDER BY rc.full_name
        """, (f'%{search}%',)).fetchall()
    else:
        rows = conn.execute("""
            SELECT rc.*,
                   (SELECT COUNT(*) FROM issue i WHERE i.id_reader_card = rc.id_reader_card AND i.return_date IS NULL) AS books_on_hands
            FROM reader_card rc
            ORDER BY rc.full_name
        """).fetchall()
    conn.close()
    return render_template('readers.html', readers=rows, search=search)


@app.route('/reader/<int:reader_id>')
def reader_detail(reader_id):
    conn = get_db()
    reader = conn.execute("SELECT * FROM reader_card WHERE id_reader_card = ?", (reader_id,)).fetchone()
    issues = conn.execute("""
        SELECT i.issue_date, i.return_date,
               bi.id_instance, bi.location, b.title AS book_name
        FROM issue i
        JOIN book_instance bi ON i.id_instance = bi.id_instance
        JOIN book b ON bi.id_book = b.id_book
        WHERE i.id_reader_card = ?
        ORDER BY i.issue_date DESC
    """, (reader_id,)).fetchall()
    conn.close()
    return render_template('reader_detail.html', reader=reader, issues=issues)


#Выдача книг

@app.route('/issues', methods=['GET', 'POST'])
def issues():
    conn = get_db()
    today = date.today().isoformat()

    if request.method == 'POST':
        id_instance = request.form.get('id_instance')
        id_reader_card = request.form.get('id_reader_card')
        issue_date = request.form.get('issue_date', today)

        # Проверка: экземпляр не должен быть уже выдан
        active = conn.execute("""
            SELECT id_instance FROM issue
            WHERE id_instance = ? AND return_date IS NULL
        """, (id_instance,)).fetchone()

        if active:
            flash(f'Ошибка: экземпляр №{id_instance} уже выдан и не возвращён', 'danger')
        else:
            try:
                conn.execute("""
                    INSERT INTO issue (id_instance, issue_date, return_date, id_reader_card)
                    VALUES (?, ?, NULL, ?)
                """, (id_instance, issue_date, id_reader_card))
                conn.commit()
                flash(f'Выдача экземпляра №{id_instance} зарегистрирована', 'success')
            except sqlite3.IntegrityError as e:
                flash(f'Ошибка БД: {e}', 'danger')

        conn.close()
        return redirect(url_for('issues'))

    # GET — список выдач
    search = request.args.get('search', '').strip()
    filter_status = request.args.get('status', 'all')

    query = """
        SELECT i.issue_date, i.return_date, i.id_instance, i.id_reader_card,
               b.title AS book_name, bi.location,
               rc.full_name AS reader_name
        FROM issue i
        JOIN book_instance bi ON i.id_instance = bi.id_instance
        JOIN book b ON bi.id_book = b.id_book
        JOIN reader_card rc ON i.id_reader_card = rc.id_reader_card
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (b.title LIKE ? OR rc.full_name LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    if filter_status == 'active':
        query += " AND i.return_date IS NULL"
    elif filter_status == 'returned':
        query += " AND i.return_date IS NOT NULL"

    query += " ORDER BY i.issue_date DESC"

    rows = conn.execute(query, params).fetchall()

    # Данные для выпадающих списков (форма выдачи)
    instances_available = conn.execute("""
        SELECT bi.id_instance, b.title, bi.location
        FROM book_instance bi
        JOIN book b ON bi.id_book = b.id_book
        WHERE bi.id_instance NOT IN (
            SELECT id_instance FROM issue WHERE return_date IS NULL
        )
        ORDER BY b.title
    """).fetchall()

    readers_list = conn.execute("SELECT * FROM reader_card ORDER BY full_name").fetchall()

    conn.close()
    return render_template('issues.html', issues=rows, search=search,
                           filter_status=filter_status, today=today,
                           instances_available=instances_available,
                           readers_list=readers_list)


@app.route('/return_book', methods=['POST'])
def return_book():
    id_instance = request.form['id_instance']
    issue_date = request.form['issue_date']
    return_date = request.form.get('return_date', date.today().isoformat())

    conn = get_db()
    conn.execute("""
        UPDATE issue SET return_date = ?
        WHERE id_instance = ? AND issue_date = ?
    """, (return_date, id_instance, issue_date))
    conn.commit()
    conn.close()
    flash(f'Экземпляр №{id_instance} возвращён', 'success')
    return redirect(url_for('issues'))


#Аналитический отчёт

@app.route('/report')
def report():
    conn = get_db()

    year_filter = request.args.get('year', '')
    book_filter = request.args.get('book', '').strip()

    query = """
        SELECT year, book_name, total_value,
               total_instances, issued_instances,
               (total_instances - issued_instances) AS available_instances
        FROM report_inventory
        WHERE 1=1
    """
    params = []

    if year_filter:
        query += " AND year = ?"
        params.append(year_filter)
    if book_filter:
        query += " AND book_name LIKE ?"
        params.append(f'%{book_filter}%')

    query += " ORDER BY year DESC, book_name"

    rows = conn.execute(query, params).fetchall()

    # Доступные года для фильтра
    years = [r['year'] for r in conn.execute(
        "SELECT DISTINCT year FROM report_inventory ORDER BY year DESC"
    ).fetchall()]

    # Сводка по фонду
    total_books = conn.execute("SELECT COUNT(*) AS cnt FROM book").fetchone()['cnt']
    total_instances_sum = conn.execute("SELECT COUNT(*) AS cnt FROM book_instance").fetchone()['cnt']
    issued_sum = conn.execute("SELECT COUNT(*) AS cnt FROM issue WHERE return_date IS NULL").fetchone()['cnt']

    conn.close()
    # Для круговой диаграммы — сумма из отфильтрованных rows
    pie_issued = sum(r['issued_instances'] for r in rows)
    pie_available = sum(r['total_instances'] - r['issued_instances'] for r in rows)

    return render_template('report.html', rows=rows,
                           year_filter=year_filter, book_filter=book_filter,
                           years=years,
                           total_books=total_books,
                           total_instances_sum=total_instances_sum,
                           issued_sum=issued_sum,
                           chart_labels=[r['book_name'] for r in rows],
                           chart_issued=[r['issued_instances'] for r in rows],
                           chart_available=[r['available_instances'] for r in rows],
                           pie_issued=pie_issued,
                           pie_available=pie_available)


#  Данные для AJAX-запросов

@app.route('/api/instances')
def api_instances():
    """Возвращает доступные экземпляры книг"""
    conn = get_db()
    rows = conn.execute("""
        SELECT bi.id_instance, b.title, bi.location
        FROM book_instance bi
        JOIN book b ON bi.id_book = b.id_book
        WHERE bi.id_instance NOT IN (
            SELECT id_instance FROM issue WHERE return_date IS NULL
        )
        ORDER BY b.title
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/readers')
def api_readers():
    conn = get_db()
    rows = conn.execute("SELECT id_reader_card, full_name FROM reader_card ORDER BY full_name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


if __name__ == '__main__':
    app.run(debug=True)