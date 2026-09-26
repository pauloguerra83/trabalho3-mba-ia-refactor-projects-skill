from werkzeug.security import check_password_hash, generate_password_hash

CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")  # nunca inclui a senha
CAMPOS_LOGIN = ("id", "nome", "email", "tipo")


def _to_dict(row, campos=CAMPOS_PUBLICOS):
    return {campo: row[campo] for campo in campos}


def listar(db):
    return [_to_dict(row) for row in db.execute("SELECT * FROM usuarios").fetchall()]


def buscar_por_id(db, usuario_id):
    row = db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return _to_dict(row) if row else None


def autenticar(db, email, senha):
    """Retorna os dados públicos do usuário se e-mail e senha conferem; senão None."""
    row = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    if row and check_password_hash(row["senha"], senha):
        return _to_dict(row, CAMPOS_LOGIN)
    return None


def criar(db, nome, email, senha, tipo="cliente"):
    cursor = db.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        (nome, email, generate_password_hash(senha), tipo),
    )
    return cursor.lastrowid
