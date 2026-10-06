const userModel = require('../models/userModel');

function createUserController({ db }) {
    return {
        deleteUser(id) {
            return db.transaction(() => userModel.deleteWithDependents(db, id));
        },
    };
}

module.exports = { createUserController };
