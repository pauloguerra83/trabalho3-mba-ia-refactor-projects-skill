const sqlite3 = require('sqlite3');
const { hashPassword } = require('./models/userModel');

function openDatabase(path) {
    const conn = new sqlite3.Database(path);

    const run = (sql, params = []) => new Promise((resolve, reject) => {
        conn.run(sql, params, function (err) {
            if (err) return reject(err);
            resolve({ lastID: this.lastID, changes: this.changes });
        });
    });
    const get = (sql, params = []) => new Promise((resolve, reject) => {
        conn.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
    });
    const all = (sql, params = []) => new Promise((resolve, reject) => {
        conn.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
    });

    // Uma única conexão é compartilhada pelas requisições: as transações são enfileiradas
    // para que um BEGIN nunca comece dentro de outra transação em andamento.
    let queue = Promise.resolve();
    function transaction(work) {
        const result = queue.then(async () => {
            await run('BEGIN');
            try {
                const value = await work();
                await run('COMMIT');
                return value;
            } catch (err) {
                await run('ROLLBACK');
                throw err;
            }
        });
        queue = result.catch(() => {});
        return result;
    }

    return { run, get, all, transaction };
}

async function initSchema(db) {
    await db.run('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)');
    await db.run('CREATE TABLE courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)');
    await db.run('CREATE TABLE enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)');
    await db.run('CREATE TABLE payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)');
    await db.run('CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)');

    // Seed de desenvolvimento (senha com hash, como no cadastro).
    await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', ['Leonan', 'leonan@fullcycle.com.br', hashPassword('123')]);
    await db.run("INSERT INTO courses (title, price, active) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497.00, 1)");
    await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
    await db.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, 'PAID')");
}

module.exports = { openDatabase, initSchema };
