const crypto = require('crypto');
const { ForbiddenError } = require('./errorHandler');

// Exige X-Admin-Token igual ao ADMIN_TOKEN do ambiente; sem token configurado, a rota fica bloqueada.
function adminAuth(adminToken) {
    const expected = adminToken ? Buffer.from(adminToken) : null;
    return (req, res, next) => {
        const given = Buffer.from(req.get('X-Admin-Token') || '');
        if (!expected || given.length !== expected.length || !crypto.timingSafeEqual(given, expected)) {
            return next(new ForbiddenError('Acesso administrativo não autorizado'));
        }
        next();
    };
}

module.exports = { adminAuth };
