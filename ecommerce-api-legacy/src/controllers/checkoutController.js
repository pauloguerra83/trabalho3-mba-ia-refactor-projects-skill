const crypto = require('crypto');
const { PAYMENT_STATUS } = require('../config');
const { ValidationError, NotFoundError } = require('../middlewares/errorHandler');
const courseModel = require('../models/courseModel');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');

function validate({ name, email, password, courseId, card }) {
    if (!name || !email || !courseId || !card) throw new ValidationError();
    const isText = (v) => typeof v === 'string';
    if (!isText(name) || !isText(email) || !isText(card) || !/^\d+$/.test(card)) throw new ValidationError();
    if (password !== undefined && password !== null && !isText(password)) throw new ValidationError();
    if (!Number.isInteger(Number(courseId))) throw new ValidationError();
}

function createCheckoutController({ db, paymentService }) {
    return {
        async checkout(input) {
            validate(input);
            const { name, email, password, courseId, card } = input;

            const course = await courseModel.findActiveById(db, courseId);
            if (!course) throw new NotFoundError('Curso não encontrado');

            // O pagamento é decidido antes de qualquer escrita: recusa não deixa usuário nem matrícula no banco.
            const status = paymentService.authorize(card, course.price);
            if (status === PAYMENT_STATUS.DENIED) throw new ValidationError('Pagamento recusado');

            const enrollmentId = await db.transaction(async () => {
                const user = await userModel.findByEmail(db, email);
                const userId = user
                    ? user.id
                    : await userModel.create(db, {
                        name,
                        email,
                        password: password || crypto.randomBytes(16).toString('hex'), // sem senha fixa padrão
                    });
                const id = await enrollmentModel.createEnrollment(db, userId, courseId);
                await enrollmentModel.createPayment(db, id, course.price, status);
                await enrollmentModel.logAudit(db, `Checkout curso ${courseId} por ${userId}`);
                return id;
            });

            return { msg: 'Sucesso', enrollment_id: enrollmentId };
        },
    };
}

module.exports = { createCheckoutController };
