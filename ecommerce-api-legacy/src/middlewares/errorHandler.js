class AppError extends Error {
    constructor(message, statusCode = 500) {
        super(message);
        this.statusCode = statusCode;
    }
}

class ValidationError extends AppError {
    constructor(message = 'Bad Request') { super(message, 400); }
}

class NotFoundError extends AppError {
    constructor(message) { super(message, 404); }
}

class ForbiddenError extends AppError {
    constructor(message = 'Forbidden') { super(message, 403); }
}

// Último middleware: mantém o formato original das respostas de erro (texto puro).
function errorHandler(err, req, res, _next) {
    if (err instanceof AppError) return res.status(err.statusCode).send(err.message);
    if (err.status >= 400 && err.status < 500) return res.status(err.status).send('Bad Request'); // ex.: JSON malformado
    console.error(err);
    res.status(500).send('Erro interno');
}

module.exports = { AppError, ValidationError, NotFoundError, ForbiddenError, errorHandler };
