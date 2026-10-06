const express = require('express');
const config = require('./config');
const { openDatabase, initSchema } = require('./database');
const { createPaymentService } = require('./services/paymentService');
const { createCheckoutController } = require('./controllers/checkoutController');
const { createReportController } = require('./controllers/reportController');
const { createUserController } = require('./controllers/userController');
const { checkoutRoutes } = require('./routes/checkoutRoutes');
const { adminRoutes } = require('./routes/adminRoutes');
const { userRoutes } = require('./routes/userRoutes');
const { adminAuth } = require('./middlewares/adminAuth');
const { errorHandler } = require('./middlewares/errorHandler');

async function main() {
    const db = openDatabase(config.dbPath);
    await initSchema(db);

    const paymentService = createPaymentService({ gatewayKey: config.paymentGatewayKey });
    const requireAdmin = adminAuth(config.adminToken);
    if (!config.adminToken) console.warn('ADMIN_TOKEN não definido; rotas administrativas responderão 403');

    const app = express();
    app.use(express.json());
    app.use(checkoutRoutes(createCheckoutController({ db, paymentService })));
    app.use(adminRoutes(createReportController({ db }), requireAdmin));
    app.use(userRoutes(createUserController({ db }), requireAdmin));
    app.use(errorHandler);

    app.listen(config.port, () => {
        console.log(`Frankenstein LMS rodando na porta ${config.port}...`);
    });
}

main().catch((err) => {
    console.error('Falha ao iniciar a aplicação', err);
    process.exit(1);
});
