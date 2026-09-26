const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

module.exports = Object.freeze({
    port: Number(process.env.PORT) || 3000,
    dbPath: process.env.DB_PATH || ':memory:',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '', // vazio em dev => gateway simulado
    adminToken: process.env.ADMIN_TOKEN || null,              // null => rotas admin respondem 403
    PAYMENT_STATUS,
    APPROVED_CARD_PREFIX: '4', // regra do gateway simulado: cartões iniciados em 4 são aprovados
});
