const express = require('express');

function userRoutes(userController, requireAdmin) {
    const router = express.Router();

    router.delete('/api/users/:id', requireAdmin, async (req, res, next) => {
        try {
            await userController.deleteUser(req.params.id);
            res.send('Usuário deletado');
        } catch (err) { next(err); }
    });

    return router;
}

module.exports = { userRoutes };
