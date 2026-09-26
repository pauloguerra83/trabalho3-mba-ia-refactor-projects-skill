const crypto = require('crypto');

function hashPassword(raw) {
    const salt = crypto.randomBytes(16).toString('hex');
    const hash = crypto.scryptSync(raw, salt, 64).toString('hex');
    return `${salt}:${hash}`;
}

function findByEmail(db, email) {
    return db.get('SELECT id FROM users WHERE email = ?', [email]);
}

async function create(db, { name, email, password }) {
    const { lastID } = await db.run(
        'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
        [name, email, hashPassword(password)],
    );
    return lastID;
}

// Remove o usuário junto com matrículas e pagamentos dele (chamar dentro de transaction()).
async function deleteWithDependents(db, id) {
    await db.run(
        'DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)',
        [id],
    );
    await db.run('DELETE FROM enrollments WHERE user_id = ?', [id]);
    await db.run('DELETE FROM users WHERE id = ?', [id]);
}

module.exports = { hashPassword, findByEmail, create, deleteWithDependents };
