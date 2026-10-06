async function createEnrollment(db, userId, courseId) {
    const { lastID } = await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseId]);
    return lastID;
}

function createPayment(db, enrollmentId, amount, status) {
    return db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)', [enrollmentId, amount, status]);
}

function logAudit(db, action) {
    return db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [action]);
}

// Uma linha por curso x matrícula (curso sem matrícula vem com colunas nulas), em uma única query.
function financialReportRows(db) {
    return db.all(`
        SELECT c.id AS course_id, c.title AS course,
               e.id AS enrollment_id, u.name AS student,
               p.amount, p.status
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.id
        LEFT JOIN users u ON u.id = e.user_id
        LEFT JOIN payments p ON p.enrollment_id = e.id
        ORDER BY c.id, e.id`);
}

module.exports = { createEnrollment, createPayment, logAudit, financialReportRows };
