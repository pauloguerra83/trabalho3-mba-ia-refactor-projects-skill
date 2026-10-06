const { PAYMENT_STATUS, APPROVED_CARD_PREFIX } = require('../config');

// Gateway de pagamento simulado. A chave vem da config por parâmetro e nunca é logada.
function createPaymentService({ gatewayKey }) {
    return {
        authorize(card, amount) {
            console.info(`Processando pagamento de ${amount} no cartão final ${card.slice(-4)}${gatewayKey ? '' : ' (gateway simulado)'}`);
            return card.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
        },
    };
}

module.exports = { createPaymentService };
