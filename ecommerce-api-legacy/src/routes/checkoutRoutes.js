const express = require('express');

function checkoutRoutes(checkoutController) {
    const router = express.Router();

    router.post('/api/checkout', async (req, res, next) => {
        try {
            const { usr, eml, pwd, c_id, card } = req.body || {}; // contrato preservado
            const result = await checkoutController.checkout({ name: usr, email: eml, password: pwd, courseId: c_id, card });
            res.status(200).json(result);
        } catch (err) { next(err); }
    });

    return router;
}

module.exports = { checkoutRoutes };
