const express = require('express');

function adminRoutes(reportController, requireAdmin) {
    const router = express.Router();

    router.get('/api/admin/financial-report', requireAdmin, async (req, res, next) => {
        try {
            res.json(await reportController.financialReport());
        } catch (err) { next(err); }
    });

    return router;
}

module.exports = { adminRoutes };
